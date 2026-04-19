import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { DebugPage } from '../ui/DebugPage'
import {
  debugLogin,
  fetchOpenApiSpec,
  generateDebugApiPlaygroundInput,
  generateDebugUnitInput,
  getBehaviorDebugRun,
  getDebugConfig,
  getDebugSession,
  listDebugRuns,
  listDebugUnits,
  runDebugUnit,
  startBehaviorDebugRun,
  trackBehaviorDebugTask,
  explainBehaviorDebugRun,
  debugLogout,
} from '../utils/debugApi'

vi.mock('../utils/debugApi', () => ({
  DEBUG_BASE_URL: 'http://localhost:8000',
  debugLogin: vi.fn(),
  debugLogout: vi.fn(),
  explainBehaviorDebugRun: vi.fn(),
  fetchOpenApiSpec: vi.fn(),
  generateDebugApiPlaygroundInput: vi.fn(),
  generateDebugUnitInput: vi.fn(),
  getBehaviorDebugRun: vi.fn(),
  getDebugConfig: vi.fn(),
  getDebugSession: vi.fn(),
  listDebugRuns: vi.fn(),
  listDebugUnits: vi.fn(),
  runDebugUnit: vi.fn(),
  startBehaviorDebugRun: vi.fn(),
  trackBehaviorDebugTask: vi.fn(),
}))

const defaultConfig = {
  enabled: true,
  llm_explain_enabled: true,
  auth_mode: 'token',
  cookie_name: 'debug_session',
}

const defaultSession = {
  ok: true,
  session: {
    id: 'sess-1',
    role: 'admin',
    created_at: '2026-01-01T00:00:00Z',
    expires_at: '2026-01-01T12:00:00Z',
  },
}

const defaultRunSummary = {
  runs: [
    {
      id: 'run-1',
      kind: 'behavior',
      status: 'completed',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:01Z',
      event_count: 2,
      error: null,
    },
  ],
}

const defaultRunDetail = {
  id: 'run-1',
  kind: 'behavior',
  status: 'completed',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:01Z',
  config: {},
  events: [],
  artifacts: {},
  explanation: null,
  error: null,
  job_running: false,
}

const defaultUnitSpec = {
  units: [
    {
      name: 'intent_parser',
      description: 'Parse intent',
      function_name: 'parse_intent',
      input_schema: { type: 'object', properties: { query: { type: 'string' } } },
      expected_io: { type: 'object' },
      sample_input: { query: 'hello' },
    },
  ],
}

const defaultOpenApi = {
  openapi: '3.0.0',
  paths: {
    '/health': {
      get: {
        summary: 'Health check',
        operationId: 'health_check',
        responses: {
          '200': { description: 'ok' },
        },
      },
    },
  },
}

function renderDebugPage() {
  return render(
    <MemoryRouter>
      <DebugPage />
    </MemoryRouter>
  )
}

describe('frontend page: DebugPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('fetch', vi.fn())

    vi.mocked(getDebugConfig).mockResolvedValue(defaultConfig)
    vi.mocked(getDebugSession).mockResolvedValue(defaultSession)
    vi.mocked(debugLogin).mockResolvedValue(defaultSession)
    vi.mocked(debugLogout).mockResolvedValue({ ok: true })
    vi.mocked(listDebugRuns).mockResolvedValue(defaultRunSummary)
    vi.mocked(listDebugUnits).mockResolvedValue(defaultUnitSpec)
    vi.mocked(getBehaviorDebugRun).mockResolvedValue(defaultRunDetail)
    vi.mocked(startBehaviorDebugRun).mockResolvedValue({ ok: true, run_id: 'run-2', status: 'queued' })
    vi.mocked(trackBehaviorDebugTask).mockResolvedValue({ ok: true, run_id: 'run-track', status: 'queued' })
    vi.mocked(explainBehaviorDebugRun).mockResolvedValue({ ok: true, mode: 'nl_explain', explanation: {} })
    vi.mocked(generateDebugUnitInput).mockResolvedValue({ input_data: { query: 'generated' }, validation_errors: [] })
    vi.mocked(runDebugUnit).mockResolvedValue({
      ok: true,
      unit: { name: 'intent_parser', function_name: 'parse_intent' },
      input_source: 'manual',
      input_data: { query: 'hello' },
      validation_errors: [],
      result: {
        ok: true,
        output: { intent: 'query', confidence: 0.9 },
        duration_ms: 5,
      },
    })
    vi.mocked(generateDebugApiPlaygroundInput).mockResolvedValue({
      ok: true,
      mode: 'schema',
      input_data: { path_params: {}, query_params: {}, body: {} },
      validation_errors: [],
    })
    vi.mocked(fetchOpenApiSpec).mockResolvedValue(defaultOpenApi)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('supports login flow and can create a behavior trace run', async () => {
    vi.mocked(getDebugSession).mockRejectedValueOnce(new Error('unauthorized'))

    renderDebugPage()

    expect(await screen.findByRole('heading', { name: 'Debug Login' })).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText('Debug admin token'), {
      target: { value: 'debug-token' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Login' }))

    await waitFor(() => expect(debugLogin).toHaveBeenCalledWith('debug-token'))
    expect(await screen.findByRole('tab', { name: 'Task Process Tracker' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Create Trace Run' }))
    await waitFor(() => expect(startBehaviorDebugRun).toHaveBeenCalledTimes(1))
    expect(vi.mocked(startBehaviorDebugRun).mock.calls[0][0]).toEqual(
      expect.objectContaining({
        use_online_agent: false,
        auto_confirm: true,
      })
    )
  })

  it('runs unit test bench and renders execution output', async () => {
    renderDebugPage()

    expect(await screen.findByRole('tab', { name: 'Unit Test Bench' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Unit Test Bench' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Run Unit' }))

    await waitFor(() => expect(runDebugUnit).toHaveBeenCalledTimes(1))
    expect(vi.mocked(runDebugUnit).mock.calls[0][0]).toEqual(
      expect.objectContaining({
        unit_name: 'intent_parser',
        input_mode: 'manual',
      })
    )
    expect(await screen.findByText('Function Output (raw JSON)')).toBeInTheDocument()
    expect(screen.getByText('Execution Time')).toBeInTheDocument()
  })

  it('runs API playground request and renders API output summary', async () => {
    const mockFetch = globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      statusText: 'OK',
      headers: {
        forEach: (cb: (value: string, key: string) => void) => cb('application/json', 'content-type'),
        get: (key: string) => (key.toLowerCase() === 'content-type' ? 'application/json' : null),
      },
      text: async () => '{"status":"ok"}',
    })

    renderDebugPage()

    fireEvent.click(await screen.findByRole('tab', { name: 'API Playground' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Run API' }))

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1))
    expect(mockFetch.mock.calls[0][0]).toBe('http://localhost:8000/health')
    expect(await screen.findByText('Request succeeded')).toBeInTheDocument()
    expect(screen.getByText('HTTP Status')).toBeInTheDocument()
  })
})
