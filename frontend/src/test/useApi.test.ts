import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useTask, useReport, useSystem } from '../hooks/useApi'
import { taskApi, reportApi, systemApi } from '../services/api'

vi.mock('../services/api', () => ({
  taskApi: {
    create: vi.fn(),
    run: vi.fn(),
    getStatus: vi.fn(),
    getResult: vi.fn(),
    list: vi.fn(),
  },
  reportApi: {
    get: vi.fn(),
    getSummary: vi.fn(),
  },
  systemApi: {
    getStatus: vi.fn(),
    getMetrics: vi.fn(),
    getAgentStatus: vi.fn(),
  },
  authApi: {},
  toolsApi: {},
  chatApi: {},
}))

describe('useTask', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('initializes with idle state', () => {
    const { result } = renderHook(() => useTask())

    expect(result.current.status).toBe('idle')
    expect(result.current.taskId).toBeNull()
    expect(result.current.progress).toBe(0)
    expect(result.current.error).toBeNull()
  })

  it('creates a task successfully', async () => {
    vi.mocked(taskApi.create).mockResolvedValueOnce({
      task_id: 'test-123',
      status: 'pending',
      message: 'Created',
    })

    const { result } = renderHook(() => useTask())

    let taskId: string | undefined
    await act(async () => {
      taskId = await result.current.createTask('Analyze AAPL stock')
    })

    expect(taskId).toBe('test-123')
    expect(result.current.taskId).toBe('test-123')
    expect(result.current.status).toBe('pending')
  })

  it('handles task creation error', async () => {
    vi.mocked(taskApi.create).mockRejectedValueOnce(new Error('Network error'))

    const { result } = renderHook(() => useTask())

    await act(async () => {
      try {
        await result.current.createTask('Test query')
      } catch (error) {
        // Expected
      }
    })

    expect(result.current.status).toBe('error')
    expect(result.current.error).toBe('Network error')
  })

  it('runs a task and polls for status', async () => {
    vi.mocked(taskApi.create).mockResolvedValueOnce({
      task_id: 'test-123',
      status: 'pending',
      message: 'Created',
    })
    vi.mocked(taskApi.run).mockResolvedValueOnce({ message: 'Started' })
    vi.mocked(taskApi.getStatus).mockResolvedValue({
      task_id: 'test-123',
      status: 'running',
      progress: 50,
      current_stage: 'executing',
      message: 'Running',
    })

    const { result } = renderHook(() => useTask())

    await act(async () => {
      await result.current.createTask('Test query')
    })

    await act(async () => {
      await result.current.runTask('test-123')
    })

    expect(result.current.status).toBe('running')
    expect(taskApi.run).toHaveBeenCalledWith('test-123')
  })

  it('resets task state', () => {
    const { result } = renderHook(() => useTask())

    act(() => {
      result.current.resetTask()
    })

    expect(result.current.status).toBe('idle')
    expect(result.current.taskId).toBeNull()
    expect(result.current.progress).toBe(0)
  })
})

describe('useReport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('initializes with null report', () => {
    const { result } = renderHook(() => useReport())

    expect(result.current.report).toBeNull()
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('fetches a report successfully', async () => {
    const mockReport = {
      task_id: 'test-123',
      title: 'Test Report',
      summary: 'Test summary',
      content: 'Report content',
    }
    vi.mocked(reportApi.get).mockResolvedValueOnce(mockReport as any)

    const { result } = renderHook(() => useReport())

    await act(async () => {
      await result.current.getReport('test-123')
    })

    expect(result.current.report).toEqual(mockReport)
    expect(result.current.loading).toBe(false)
  })

  it('handles report fetch error', async () => {
    vi.mocked(reportApi.get).mockRejectedValueOnce(new Error('Failed to fetch'))

    const { result } = renderHook(() => useReport())

    await act(async () => {
      try {
        await result.current.getReport('test-123')
      } catch (error) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Failed to fetch')
    expect(result.current.loading).toBe(false)
  })

  it('fetches report summary', async () => {
    const mockSummary = {
      task_id: 'test-123',
      summary: 'Summary content',
      key_findings: ['finding1'],
    }
    vi.mocked(reportApi.getSummary).mockResolvedValueOnce(mockSummary as any)

    const { result } = renderHook(() => useReport())

    let summary: any
    await act(async () => {
      summary = await result.current.getReportSummary('test-123')
    })

    expect(summary).toEqual(mockSummary)
  })
})

describe('useSystem', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('initializes with null values', () => {
    const { result } = renderHook(() => useSystem())

    expect(result.current.systemStatus).toBeNull()
    expect(result.current.metrics).toBeNull()
    expect(result.current.agentStatus).toBeNull()
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('fetches system status', async () => {
    const mockStatus = {
      status: 'healthy',
      version: '1.0.0',
      uptime: 12345,
    }
    vi.mocked(systemApi.getStatus).mockResolvedValueOnce(mockStatus as any)

    const { result } = renderHook(() => useSystem())

    await act(async () => {
      await result.current.fetchSystemStatus()
    })

    expect(result.current.systemStatus).toEqual(mockStatus)
    expect(result.current.loading).toBe(false)
  })

  it('fetches system metrics', async () => {
    const mockMetrics = {
      total_tasks: 10,
      completed_tasks: 8,
      pending_tasks: 2,
    }
    vi.mocked(systemApi.getMetrics).mockResolvedValueOnce(mockMetrics as any)

    const { result } = renderHook(() => useSystem())

    await act(async () => {
      await result.current.fetchMetrics()
    })

    expect(result.current.metrics).toEqual(mockMetrics)
  })

  it('fetches agent status', async () => {
    const mockAgentStatus = {
      planner: { status: 'ready' },
      executor: { status: 'ready' },
      reasoner: { status: 'ready' },
    }
    vi.mocked(systemApi.getAgentStatus).mockResolvedValueOnce(mockAgentStatus as any)

    const { result } = renderHook(() => useSystem())

    await act(async () => {
      await result.current.fetchAgentStatus()
    })

    expect(result.current.agentStatus).toEqual(mockAgentStatus)
  })

  it('handles fetch errors', async () => {
    vi.mocked(systemApi.getStatus).mockRejectedValueOnce(new Error('Connection failed'))

    const { result } = renderHook(() => useSystem())

    await act(async () => {
      try {
        await result.current.fetchSystemStatus()
      } catch (error) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Connection failed')
    expect(result.current.loading).toBe(false)
  })
})