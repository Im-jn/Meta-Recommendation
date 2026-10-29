"""WP8 single-invocation helper: one ainvoke, untouched business config, real parents."""
import asyncio
import contextvars
import copy
from typing import TypedDict

import pytest
from langchain_core.callbacks import CallbackManager
from langchain_core.runnables.config import var_child_runnable_config
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from langgraph_metarec.graphs.routing_graph import build_routing_graph
from langgraph_metarec.wp8_trace import topology
from langgraph_metarec.wp8_trace.invocation import (
    TopologyMismatchError,
    TraceContext,
    invoke_with_wp8_trace,
    traced_config,
)
from wp8_probe_support import RecordingHandler, build_runs

ROUTING_INPUT = {
    "query": "Recommend a hotel for tonight", "intent": "query", "preferences": None,
    "domain_lock": None, "force_itinerary": False, "errors": [], "retry_count": 0, "max_retries": 1,
}
COUNTER_ID = "wp8-test-counter@v1"
OUTER_ID = "wp8-test-outer@v1"


class CounterState(TypedDict, total=False):
    n: int


class Behaviour:
    def __init__(self, mode="ok"):
        self.mode, self.calls, self.entered = mode, 0, asyncio.Event()
        self.checkpointer = None


def build_counter_graph(behaviour=None):
    behaviour = behaviour or Behaviour()

    async def side_effect(state):
        behaviour.calls += 1
        behaviour.entered.set()
        if behaviour.mode == "error":
            raise RuntimeError("injected")
        if behaviour.mode == "hang":
            await asyncio.Event().wait()
        return {"n": state.get("n", 0) + 1}

    graph = StateGraph(CounterState)
    graph.add_node("side_effect", side_effect)
    graph.add_edge(START, "side_effect")
    graph.add_edge("side_effect", END)
    return graph.compile(checkpointer=behaviour.checkpointer)


def build_outer_graph(inner):
    async def call_inner(state):
        await inner()
        return state

    graph = StateGraph(CounterState)
    graph.add_node("call_inner", call_inner)
    graph.add_edge(START, "call_inner")
    graph.add_edge("call_inner", END)
    return graph.compile()


async def _noop():
    return None


@pytest.fixture(autouse=True)
def registered_test_graphs(monkeypatch):
    monkeypatch.setitem(topology._GRAPHS, COUNTER_ID, ("Test counter graph", build_counter_graph))
    monkeypatch.setitem(topology._GRAPHS, OUTER_ID, ("Test outer graph", lambda: build_outer_graph(_noop)))
    topology.registered_graph.cache_clear()
    yield
    topology.registered_graph.cache_clear()


def _ctx(collector=None, **kwargs):
    return TraceContext(trace_id="tr-1", debug_run_id="dr-1", collector=collector or RecordingHandler(), **kwargs)


def _graph_runs(handler):
    runs = build_runs(handler.events)
    return [r for r in runs.values() if "@v" in str(r["name"]) or r["name"] == "LangGraph"], runs


class FakeGraph:
    def __init__(self):
        self.calls = []

    async def ainvoke(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return "out"


@pytest.mark.backend_unit
@pytest.mark.asyncio
@pytest.mark.parametrize("ctx", [None, "disabled"])
async def test_untraced_call_is_exactly_the_plain_call(ctx):
    trace_ctx = _ctx(enabled=False) if ctx == "disabled" else None
    graph, config = FakeGraph(), {"configurable": {"thread_id": "t-1"}}

    assert await invoke_with_wp8_trace(graph, {"a": 1}, None, trace_ctx, graph_definition_id="nonexistent@v1") == "out"
    await invoke_with_wp8_trace(graph, {"a": 1}, config, trace_ctx, graph_definition_id="nonexistent@v1")

    assert graph.calls[0] == (({"a": 1},), {})
    assert graph.calls[1][0][1] is config, "the caller's config object is passed through unchanged"


@pytest.mark.backend_unit
def test_traced_config_adds_only_run_name_and_collector():
    business = {
        "configurable": {"thread_id": "u:c:branch-main"},
        "tags": ["existing"],
        "metadata": {"source": "service"},
        "recursion_limit": 40,
    }
    before = copy.deepcopy(business)
    ctx = _ctx()

    merged = traced_config(business, ctx, "task-graph@v1")

    assert business == before, "the caller's config is not mutated"
    assert {k: merged[k] for k in business} == business
    assert merged["run_name"] == "task-graph@v1"
    assert merged["callbacks"] == [ctx.collector]
    assert set(merged) == set(business) | {"run_name", "callbacks"}


@pytest.mark.backend_unit
def test_existing_callbacks_are_kept_and_not_mutated():
    other = RecordingHandler()
    as_list = {"callbacks": [other]}
    manager = CallbackManager(handlers=[other], inheritable_handlers=[other], parent_run_id=None)
    ctx = _ctx()

    merged_list = traced_config(as_list, ctx, "task-graph@v1")["callbacks"]
    merged_manager = traced_config({"callbacks": manager}, ctx, "task-graph@v1")["callbacks"]

    assert merged_list == [other, ctx.collector] and as_list["callbacks"] == [other]
    assert ctx.collector in merged_manager.handlers and ctx.collector not in manager.handlers
    assert merged_manager.parent_run_id == manager.parent_run_id


@pytest.mark.backend_unit
def test_collector_already_present_is_not_added_twice():
    ctx = _ctx()
    callbacks = [ctx.collector]

    assert traced_config({"callbacks": callbacks}, ctx, "task-graph@v1")["callbacks"] is callbacks


@pytest.mark.backend_unit
@pytest.mark.asyncio
async def test_root_graph_run_is_named_by_its_definition_and_output_is_unchanged():
    ctx = _ctx()

    traced = await invoke_with_wp8_trace(build_routing_graph(), dict(ROUTING_INPUT), None, ctx,
                                         graph_definition_id="routing-graph@v1")
    plain = await build_routing_graph().ainvoke(dict(ROUTING_INPUT))

    graphs, runs = _graph_runs(ctx.collector)
    assert [(g["name"], g["parent_run_id"]) for g in graphs] == [("routing-graph@v1", None)]
    node_names = {r["name"] for r in runs.values() if r["parent_run_id"] == graphs[0]["run_id"]}
    assert "domain_classification" in node_names, "node names are unchanged"
    assert traced == plain


async def _run_outer(ctx, inner):
    """Run a traced outer graph whose single node runs `inner`; return the recorded runs."""
    await invoke_with_wp8_trace(build_outer_graph(inner), {"n": 0}, None, ctx, graph_definition_id=OUTER_ID)
    return build_runs(ctx.collector.events)


def _node_run(runs, name):
    (node,) = [r for r in runs.values() if r["name"] == name]
    return node


@pytest.mark.backend_unit
@pytest.mark.asyncio
async def test_nested_call_keeps_the_inherited_parent_and_checkpoint_namespace():
    traced_ctx, plain_ctx = _ctx(), _ctx()

    async def traced_inner():
        await invoke_with_wp8_trace(build_routing_graph(), dict(ROUTING_INPUT), None, traced_ctx,
                                    graph_definition_id="routing-graph@v1")

    async def plain_inner():
        await build_routing_graph().ainvoke(dict(ROUTING_INPUT))

    traced = await _run_outer(traced_ctx, traced_inner)
    plain = await _run_outer(plain_ctx, plain_inner)

    (inner,) = [r for r in traced.values() if r["name"] == "routing-graph@v1"]
    assert inner["parent_run_id"] == _node_run(traced, "call_inner")["run_id"]
    assert inner["metadata"].get("checkpoint_ns", "").startswith("call_inner:"), "namespace still inherited"

    # Same run tree with or without the helper; only the nested graph's name differs.
    def shape(runs):
        return sorted((r["name"].replace("routing-graph@v1", "LangGraph"), r["metadata"].get("checkpoint_ns", "").split(":")[0])
                      for r in runs.values())
    assert shape(traced) == shape(plain)
    assert [r["name"] for r in plain.values() if r["name"] in ("LangGraph", "routing-graph@v1")] == ["LangGraph"], \
        "run_name does not leak into graphs invoked without the helper"


@pytest.mark.backend_unit
@pytest.mark.asyncio
async def test_each_callback_is_received_once_when_the_collector_is_inherited():
    ctx = _ctx()

    async def inner():
        await invoke_with_wp8_trace(build_routing_graph(), dict(ROUTING_INPUT), None, ctx,
                                    graph_definition_id="routing-graph@v1")

    await _run_outer(ctx, inner)

    starts = [e["run_id"] for e in ctx.collector.events if e["event"] == "chain_start"]
    assert len(starts) == len(set(starts))


@pytest.mark.backend_unit
@pytest.mark.asyncio
async def test_explicit_parent_links_a_graph_across_a_fresh_context():
    """The D0 E6b failure mode, and the mechanism M6 uses to fix it."""
    def spawn(ctx, explicit):
        async def inner():
            node_run_id = var_child_runnable_config.get()["callbacks"].parent_run_id
            child_ctx = ctx.handoff(node_run_id) if explicit else ctx
            task = asyncio.create_task(
                invoke_with_wp8_trace(build_routing_graph(), dict(ROUTING_INPUT), None, child_ctx,
                                      graph_definition_id="routing-graph@v1"),
                context=contextvars.Context(),
            )
            await task
        return inner

    linked_ctx, orphan_ctx = _ctx(), _ctx()
    linked = await _run_outer(linked_ctx, spawn(linked_ctx, explicit=True))
    orphan = await _run_outer(orphan_ctx, spawn(orphan_ctx, explicit=False))

    (child,) = [r for r in linked.values() if r["name"] == "routing-graph@v1"]
    assert child["parent_run_id"] == _node_run(linked, "call_inner")["run_id"]
    (lost,) = [r for r in orphan.values() if r["name"] == "routing-graph@v1"]
    assert lost["parent_run_id"] is None

@pytest.mark.backend_unit
@pytest.mark.asyncio
@pytest.mark.parametrize("traced", [False, True])
@pytest.mark.parametrize("mode", ["ok", "error", "cancel"])
async def test_side_effect_runs_exactly_once(traced, mode):
    behaviour = Behaviour("hang" if mode == "cancel" else mode)
    ctx = _ctx() if traced else None
    call = asyncio.create_task(
        invoke_with_wp8_trace(build_counter_graph(behaviour), {"n": 0}, None, ctx, graph_definition_id=COUNTER_ID)
    )

    if mode == "ok":
        assert (await call)["n"] == 1
    elif mode == "error":
        with pytest.raises(RuntimeError, match="injected"):
            await call
    else:
        await behaviour.entered.wait()
        call.cancel()
        with pytest.raises(asyncio.CancelledError):
            await call

    assert behaviour.calls == 1
    if traced and mode != "ok":
        errors = [e.get("error_class") for e in ctx.collector.events if e["event"] == "chain_error"]
        assert errors and set(errors) == {"RuntimeError" if mode == "error" else "CancelledError"}


@pytest.mark.backend_unit
@pytest.mark.asyncio
async def test_unknown_or_mismatched_definition_is_refused_before_running():
    behaviour = Behaviour()

    with pytest.raises(KeyError):
        await invoke_with_wp8_trace(build_counter_graph(behaviour), {"n": 0}, None, _ctx(),
                                    graph_definition_id="not-registered@v1")
    with pytest.raises(TopologyMismatchError):
        await invoke_with_wp8_trace(build_counter_graph(behaviour), {"n": 0}, None, _ctx(),
                                    graph_definition_id="routing-graph@v1")

    assert behaviour.calls == 0


@pytest.mark.backend_unit
@pytest.mark.asyncio
async def test_tracing_does_not_change_checkpoints():
    behaviour = Behaviour()
    behaviour.checkpointer = MemorySaver()
    graph = build_counter_graph(behaviour)

    await invoke_with_wp8_trace(graph, {"n": 0}, {"configurable": {"thread_id": "off"}}, None,
                                graph_definition_id=COUNTER_ID)
    await invoke_with_wp8_trace(graph, {"n": 0}, {"configurable": {"thread_id": "on"}}, _ctx(),
                                graph_definition_id=COUNTER_ID)

    def checkpoints(thread):
        return [(c.metadata, c.checkpoint["channel_values"]) for c in
                behaviour.checkpointer.list({"configurable": {"thread_id": thread}})]
    assert checkpoints("on") == checkpoints("off")
