import { useState, useCallback } from 'react'
import { taskApi, reportApi, systemApi } from '../services/api'
import type {
  TaskResultResponse,
  ReportResponse,
  SystemStatusResponse,
  SystemMetricsResponse,
  AgentStatusResponse,
} from '../types/api'

interface TaskState {
  taskId: string | null
  status: 'idle' | 'pending' | 'running' | 'completed' | 'error'
  progress: number
  currentStage: string
  result: TaskResultResponse | null
  error: string | null
}

export function useTask() {
  const [taskState, setTaskState] = useState<TaskState>({
    taskId: null,
    status: 'idle',
    progress: 0,
    currentStage: '',
    result: null,
    error: null,
  })

  const createTask = useCallback(async (query: string, priority: number = 1) => {
    try {
      setTaskState(prev => ({ ...prev, status: 'pending', error: null }))
      const response = await taskApi.create(query, priority)
      setTaskState(prev => ({
        ...prev,
        taskId: response.task_id,
        status: 'pending',
      }))
      return response.task_id
    } catch (error: any) {
      setTaskState(prev => ({
        ...prev,
        status: 'error',
        error: error.message || 'Failed to create task',
      }))
      throw error
    }
  }, [])

  const runTask = useCallback(async (taskId: string) => {
    try {
      setTaskState(prev => ({ ...prev, status: 'running', error: null }))
      await taskApi.run(taskId)
      
      let pollCount = 0
      const maxPolls = 180 // 3 minutes max
      let consecutiveErrors = 0
      const maxConsecutiveErrors = 5 // Stop after 5 consecutive network failures

      // Start polling for status
      const pollInterval = setInterval(async () => {
        pollCount++
        if (pollCount > maxPolls) {
          clearInterval(pollInterval)
          setTaskState(prev => ({
            ...prev,
            status: 'error',
            error: 'Task timed out after 3 minutes. The research pipeline is taking too long.',
          }))
          return
        }

        try {
          const status = await taskApi.getStatus(taskId)
          consecutiveErrors = 0 // Reset error counter on success

          setTaskState(prev => ({
            ...prev,
            progress: status.progress,
            currentStage: status.current_stage,
            status: status.status === 'completed' ? 'completed' : status.status === 'failed' ? 'error' : 'running',
          }))

          if (status.status === 'completed') {
            clearInterval(pollInterval)
            try {
              const result = await taskApi.getResult(taskId)
              setTaskState(prev => ({
                ...prev,
                status: 'completed',
                result,
              }))
            } catch (resultError: any) {
              // Task completed but result fetch failed - still mark as completed with partial info
              setTaskState(prev => ({
                ...prev,
                status: 'completed',
                result: null,
              }))
            }
          } else if (status.status === 'failed') {
            clearInterval(pollInterval)
            setTaskState(prev => ({
              ...prev,
              status: 'error',
              error: status.message || 'Task failed',
            }))
          }
        } catch (error: any) {
          consecutiveErrors++
          const isTimeout = error.code === 'ECONNABORTED' || error.message?.includes('timeout')
          const isNetworkError = !error.response

          console.warn(`Poll error (${consecutiveErrors}/${maxConsecutiveErrors}):`, {
            isTimeout,
            isNetworkError,
            message: error.message,
          })

          if (consecutiveErrors >= maxConsecutiveErrors) {
            clearInterval(pollInterval)
            setTaskState(prev => ({
              ...prev,
              status: 'error',
              error: isTimeout
                ? 'Connection to server timed out. Please check if the backend is running.'
                : `Network error: ${error.message || 'Lost connection to server'}`,
            }))
          }
          // Otherwise: network hiccup, keep polling (task may still be running server-side)
        }
      }, 1500) // Poll every 1.5s instead of 1s to reduce load

      return () => clearInterval(pollInterval)
    } catch (error: any) {
      setTaskState(prev => ({
        ...prev,
        status: 'error',
        error: error.userMessage || error.message || 'Failed to run task',
      }))
      throw error
    }
  }, [])

  const getTaskResult = useCallback(async (taskId: string) => {
    try {
      const result = await taskApi.getResult(taskId)
      setTaskState(prev => ({
        ...prev,
        result,
        status: 'completed',
      }))
      return result
    } catch (error: any) {
      setTaskState(prev => ({
        ...prev,
        error: error.message || 'Failed to get task result',
      }))
      throw error
    }
  }, [])

  const resetTask = useCallback(() => {
    setTaskState({
      taskId: null,
      status: 'idle',
      progress: 0,
      currentStage: '',
      result: null,
      error: null,
    })
  }, [])

  return {
    ...taskState,
    createTask,
    runTask,
    getTaskResult,
    resetTask,
  }
}

export function useReport() {
  const [report, setReport] = useState<ReportResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const getReport = useCallback(async (taskId: string) => {
    try {
      setLoading(true)
      setError(null)
      const data = await reportApi.get(taskId)
      setReport(data)
      return data
    } catch (err: any) {
      setError(err.message || 'Failed to get report')
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const getReportSummary = useCallback(async (taskId: string) => {
    try {
      setLoading(true)
      setError(null)
      const data = await reportApi.getSummary(taskId)
      return data
    } catch (err: any) {
      setError(err.message || 'Failed to get report summary')
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    report,
    loading,
    error,
    getReport,
    getReportSummary,
  }
}

export function useSystem() {
  const [systemStatus, setSystemStatus] = useState<SystemStatusResponse | null>(null)
  const [metrics, setMetrics] = useState<SystemMetricsResponse | null>(null)
  const [agentStatus, setAgentStatus] = useState<AgentStatusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSystemStatus = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await systemApi.getStatus()
      setSystemStatus(data)
      return data
    } catch (err: any) {
      setError(err.message || 'Failed to get system status')
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await systemApi.getMetrics()
      setMetrics(data)
      return data
    } catch (err: any) {
      setError(err.message || 'Failed to get metrics')
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchAgentStatus = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await systemApi.getAgentStatus()
      setAgentStatus(data)
      return data
    } catch (err: any) {
      setError(err.message || 'Failed to get agent status')
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    systemStatus,
    metrics,
    agentStatus,
    loading,
    error,
    fetchSystemStatus,
    fetchMetrics,
    fetchAgentStatus,
  }
}
