"""The single reviewed path every MetaRec graph invocation goes through.

``invoke_with_wp8_trace`` calls ``graph.ainvoke`` exactly once. With no trace
context, or a disabled one, the call is byte-for-byte what the runner did
before. With tracing on it changes only two config keys, and only for this
graph run:

- ``run_name`` = the ``graph_definition_id``, because every compiled graph
  otherwise reports the callback name ``"LangGraph"``. It does not reach
  nested runs or checkpoint metadata.
- ``callbacks`` gains the WP8 collector, unless the collector is already
  inherited from an enclosing traced run (then the key is left alone, which
  keeps that run as the callback parent).

LangChain replaces, not merges, any config key passed explicitly, so passing 
``metadata`` or ``configurable`` to a nested call would drop the inherited checkpoint 
namespace and callback parent. WP8 identity travels in the run name and the collector, 
and never in config metadata.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler, BaseCallbackManager, CallbackManager
from langchain_core.runnables.config import var_child_runnable_config

from .topology import matches_registered


class TopologyMismatchError(RuntimeError):
    """A graph was invoked under a graph_definition_id whose topology it no longer has."""


@dataclass(frozen=True)
class TraceContext:
    """Explicit WP8 trace context, passed down through every graph runner.

    ``config``, ``sink`` and ``projector`` are Member B's ``GraphTraceConfigV1``,
    ``TraceEventSink`` and ``SafeProjector``; the collector uses them.
    """

    trace_id: str
    debug_run_id: str
    collector: BaseCallbackHandler
    enabled: bool = True
    # The callback run that invoked this graph, carried explicitly across a
    # boundary that does not copy context (e.g. a background-task hand-off).
    # It must be the real run id observed at the call site, never a guess.
    parent_run_id: Optional[UUID] = None
    config: Any = None
    sink: Any = None
    projector: Any = None

    def handoff(self, parent_run_id: UUID) -> "TraceContext":
        return replace(self, parent_run_id=parent_run_id)


def _effective_callbacks(config: Optional[Mapping[str, Any]]) -> Any:
    """The callbacks LangChain will use for this call: explicit, else inherited."""
    if config is not None and config.get("callbacks") is not None:
        return config["callbacks"]
    inherited = var_child_runnable_config.get()
    return inherited.get("callbacks") if inherited else None


def _handlers(callbacks: Any) -> list:
    if callbacks is None:
        return []
    if isinstance(callbacks, BaseCallbackManager):
        return list(callbacks.handlers) + list(callbacks.inheritable_handlers)
    return list(callbacks)


def _with_collector(callbacks: Any, ctx: TraceContext) -> Any:
    if isinstance(callbacks, BaseCallbackManager):
        manager = callbacks.copy()
        manager.add_handler(ctx.collector, inherit=True)
        return manager
    handlers = [*(callbacks or []), ctx.collector]
    if ctx.parent_run_id is not None:
        return CallbackManager(handlers=handlers, inheritable_handlers=handlers, parent_run_id=ctx.parent_run_id)
    return handlers


def traced_config(
    config: Optional[Mapping[str, Any]],
    trace_ctx: TraceContext,
    graph_definition_id: str,
) -> dict:
    """A new config for one traced graph run; the caller's config is not mutated."""
    merged = dict(config or {})
    merged["run_name"] = graph_definition_id
    effective = _effective_callbacks(config)
    if trace_ctx.collector not in _handlers(effective):
        merged["callbacks"] = _with_collector(effective, trace_ctx)
    return merged


async def invoke_with_wp8_trace(
    graph: Any,
    input: Any,
    config: Optional[Mapping[str, Any]],
    trace_ctx: Optional[TraceContext],
    *,
    graph_definition_id: str,
    **kwargs: Any,
) -> Any:
    """Invoke a compiled MetaRec graph exactly once, traced when ``trace_ctx`` is enabled."""
    if trace_ctx is None or not trace_ctx.enabled:
        if config is None:
            return await graph.ainvoke(input, **kwargs)
        return await graph.ainvoke(input, config, **kwargs)
    if not matches_registered(graph, graph_definition_id):
        raise TopologyMismatchError(
            f"graph does not match the registered topology of {graph_definition_id}; "
            "bump its version in langgraph_metarec/wp8_trace/topology.py"
        )
    return await graph.ainvoke(input, traced_config(config, trace_ctx, graph_definition_id), **kwargs)
