import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { PageHeader } from '../components/layout'
import { StockPool, ResearchReport, AgentExecution } from '../components/research'
import { Plus, Loader2 } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { TaskStatusResponse } from '../types/api'
import { taskApi } from '../services/api'
import { useToast } from '../components/ui/ToastContext'

interface TaskStep {
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  duration?: number
  icon: LucideIcon | null
  color: string
}

interface SavedResearchState {
  selectedSymbol: string | null
  taskId: string | null
  isResearching: boolean
  taskLifecycle?: TaskLifecycle
  taskError?: string | null
  steps: TaskStep[]
  totalDuration?: number
  startedAt?: number
}

type TaskLifecycle = TaskStatusResponse['status'] | 'unknown'

const STORAGE_KEY = 'research_center_state'
const POLL_INTERVAL = 2000
// Backend task execution is capped at 15 minutes. Leave one minute for the
// final status/result request so the UI never declares a live task failed.
const RESEARCH_TIMEOUT_MS = 16 * 60 * 1000

function createInitialSteps(): TaskStep[] {
  return [
    { name: 'planner', status: 'running', icon: null, color: 'text-primary-300' },
    { name: 'newsSearch', status: 'pending', icon: null, color: 'text-blue-400' },
    { name: 'ragRetrieve', status: 'pending', icon: null, color: 'text-cyan-400' },
    { name: 'financialReport', status: 'pending', icon: null, color: 'text-green-400' },
    { name: 'synthesizer', status: 'pending', icon: null, color: 'text-yellow-400' },
    { name: 'report', status: 'pending', icon: null, color: 'text-emerald-400' },
  ]
}

const LEGACY_STEP_NAMES: Record<string, string> = {
  planner: 'Planner',
  newsSearch: 'News Search',
  ragRetrieve: 'RAG Retrieve',
  financialReport: 'Financial Report',
  synthesizer: 'Synthesizer',
  report: 'Report',
}

function isStep(step: TaskStep, name: string): boolean {
  return step.name === name || step.name === LEGACY_STEP_NAMES[name]
}

function loadResearchState(): SavedResearchState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveResearchState(state: SavedResearchState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // Ignore storage errors, the running task still remains on the backend.
  }
}

function updateStepsForStage(prev: TaskStep[], status: TaskStatusResponse, _elapsed: number): TaskStep[] {
  if (status.status === 'completed') {
    return prev.map((step) => ({ ...step, status: 'completed', duration: undefined }))
  }

  if (status.status === 'failed') {
    return prev.map((step) => (step.status === 'running' ? { ...step, status: 'failed' } : step))
  }

  if (status.current_stage === 'planning') {
    return prev.map((step) => (isStep(step, 'planner') ? { ...step, status: 'running' } : step))
  }

  if (status.current_stage === 'executing') {
    return prev.map((step) =>
      isStep(step, 'planner') ? { ...step, status: 'completed', duration: undefined } :
      isStep(step, 'newsSearch') ? { ...step, status: 'running' } :
      isStep(step, 'ragRetrieve') ? { ...step, status: 'running' } :
      isStep(step, 'financialReport') ? { ...step, status: 'running' } :
      step
    )
  }

  if (status.current_stage === 'reasoning') {
    return prev.map((step) =>
      !isStep(step, 'synthesizer') && !isStep(step, 'report') && step.status !== 'completed'
        ? { ...step, status: 'completed', duration: undefined } :
      isStep(step, 'synthesizer') ? { ...step, status: 'running' } :
      step
    )
  }

  if (status.current_stage === 'reporting') {
    return prev.map((step) =>
      isStep(step, 'synthesizer') ? { ...step, status: 'completed', duration: undefined } :
      isStep(step, 'report') ? { ...step, status: 'running' } :
      step
    )
  }

  return prev
}

export default function ResearchCenter() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const toast = useToast()
  const [searchParams] = useSearchParams()
  const [initialState] = useState(() => loadResearchState())
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pollInFlightRef = useRef(false)

  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(initialState?.selectedSymbol || null)
  const [taskId, setTaskId] = useState<string | null>(initialState?.taskId || null)
  const [isResearching, setIsResearching] = useState(Boolean(initialState?.isResearching))
  const [taskLifecycle, setTaskLifecycle] = useState<TaskLifecycle>(
    initialState?.taskLifecycle || (initialState?.isResearching ? 'running' : 'unknown'),
  )
  const [taskError, setTaskError] = useState<string | null>(initialState?.taskError || null)
  const [isValidatingTask, setIsValidatingTask] = useState(Boolean(initialState?.taskId && !initialState?.isResearching))
  const [steps, setSteps] = useState<TaskStep[]>(initialState?.steps?.length ? initialState.steps : [])
  const [totalDuration, setTotalDuration] = useState<number | undefined>(initialState?.totalDuration)
  const [startedAt, setStartedAt] = useState<number | undefined>(initialState?.startedAt)

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])

  const pollTaskStatus = useCallback(async (id: string, startTime: number) => {
    if (pollInFlightRef.current) return
    pollInFlightRef.current = true
    try {
      const status = await taskApi.getStatus(id)
      const elapsed = Date.now() - startTime

      setTaskLifecycle(status.status)
      setTotalDuration(elapsed)
      setSteps((prev) => updateStepsForStage(prev.length ? prev : createInitialSteps(), status, elapsed))

      if (status.status === 'completed') {
        stopPolling()
        setTaskError(null)
        setIsResearching(false)
        toast.success(t('common.success'), t('research.completed'))
        return
      }

      if (status.status === 'failed') {
        stopPolling()
        const failureMessage = status.current_stage === 'interrupted'
          ? t('research.taskInterrupted')
          : status.message || t('research.taskFailed')
        setTaskError(failureMessage)
        setIsResearching(false)
        toast.error(t('common.error'), failureMessage)
        return
      }

      if (elapsed > RESEARCH_TIMEOUT_MS) {
        stopPolling()
        setTaskError(t('error.timeout'))
        setIsResearching(false)
        setSteps((prev) => prev.map((step) => (step.status === 'running' ? { ...step, status: 'failed' } : step)))
        toast.error(t('common.error'), t('error.timeout'))
      }
    } catch (err) {
      console.error('Polling error:', err)
    } finally {
      pollInFlightRef.current = false
    }
  }, [stopPolling, t, toast])

  const startPolling = useCallback((id: string, startTime: number) => {
    stopPolling()
    pollTaskStatus(id, startTime)
    pollIntervalRef.current = setInterval(() => {
      pollTaskStatus(id, startTime)
    }, POLL_INTERVAL)
  }, [pollTaskStatus, stopPolling])

  useEffect(() => {
    const q = searchParams.get('q')?.trim()
    if (q && !isResearching) setSelectedSymbol(q.toUpperCase())
  }, [isResearching, searchParams])

  useEffect(() => {
    saveResearchState({
      selectedSymbol,
      taskId,
      isResearching,
      taskLifecycle,
      taskError,
      steps,
      totalDuration,
      startedAt,
    })
  }, [isResearching, selectedSymbol, startedAt, steps, taskError, taskId, taskLifecycle, totalDuration])

  // Older saved UI state did not record the terminal task status. Resolve it
  // before the report component is allowed to fetch a completed-only endpoint.
  useEffect(() => {
    if (!taskId || isResearching || taskLifecycle !== 'unknown') {
      setIsValidatingTask(false)
      return
    }

    let cancelled = false
    setIsValidatingTask(true)
    taskApi.getStatus(taskId)
      .then((status) => {
        if (cancelled) return
        setTaskLifecycle(status.status)
        setSteps((prev) => updateStepsForStage(prev.length ? prev : createInitialSteps(), status, totalDuration || 0))

        if (status.status === 'failed') {
          setTaskError(status.current_stage === 'interrupted'
            ? t('research.taskInterrupted')
            : status.message || t('research.taskFailed'))
        } else if (status.status === 'running' || status.status === 'pending') {
          setTaskError(null)
          setStartedAt((value) => value || Date.now())
          setIsResearching(true)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error('Failed to validate saved research task:', err)
          setTaskError(t('error.serverError'))
        }
      })
      .finally(() => {
        if (!cancelled) setIsValidatingTask(false)
      })

    return () => {
      cancelled = true
    }
  }, [isResearching, taskId, taskLifecycle, t, totalDuration])

  useEffect(() => {
    if (taskId && isResearching) {
      startPolling(taskId, startedAt || Date.now())
    }

    return stopPolling
  }, [isResearching, startedAt, startPolling, stopPolling, taskId])

  const handleNewResearch = async () => {
    if (!selectedSymbol) {
      toast.error(t('common.error'), t('stock.enterSymbol'))
      return
    }

    try {
      stopPolling()

      const startTime = Date.now()
      const initialSteps = createInitialSteps()

      setIsResearching(true)
      setTaskLifecycle('pending')
      setTaskError(null)
      setIsValidatingTask(false)
      setTaskId(null)
      setStartedAt(startTime)
      setTotalDuration(undefined)
      setSteps(initialSteps)

      const query = t('research.defaultQuery', { symbol: selectedSymbol })
      const task = await taskApi.create(query, 1)

      setTaskId(task.task_id)

      // The server may have accepted the task even if this response times out.
      // Start status polling first and only stop for a definite HTTP failure.
      startPolling(task.task_id, startTime)
      try {
        await taskApi.run(task.task_id)
      } catch (runError: unknown) {
        const responseStatus = (runError as { response?: { status?: number } }).response?.status
        if (responseStatus && responseStatus !== 400) throw runError
        console.warn('Task start response was ambiguous; continuing status polling.', runError)
      }
    } catch (err) {
      stopPolling()
      setTaskLifecycle('failed')
      setTaskError(err instanceof Error ? err.message : t('research.taskFailed'))
      setIsResearching(false)
      setSteps((prev) => prev.map((step) => (step.status === 'running' ? { ...step, status: 'failed' } : step)))
      toast.error(t('common.error'), err instanceof Error ? err.message : t('research.taskFailed'))
    }
  }

  const handleViewReport = () => {
    if (taskId) {
      navigate(`/report/${taskId}`)
    }
  }

  return (
    <div className="app-workspace flex flex-col px-6 py-6 lg:px-8 lg:py-8 2xl:px-10">
      <PageHeader
        title={t('research.title')}
        subtitle={t('research.startResearch')}
      >
        <button
          onClick={handleNewResearch}
          disabled={isResearching || !selectedSymbol}
          className="flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-white bg-primary-500 hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed rounded transition-colors"
        >
          {isResearching ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Plus className="w-4 h-4" />
          )}
          {isResearching ? t('research.analyzing') : t('research.newTask')}
        </button>
        {taskId && !isResearching && (
          <button
            onClick={handleViewReport}
            className="flex items-center gap-2 px-3.5 py-2 text-sm text-primary-400 hover:text-primary-200 bg-dark-card border border-dark-border rounded transition-colors"
          >
            {t('report.viewFullReport')}
          </button>
        )}
      </PageHeader>

      <div className="flex-1 min-h-0 grid grid-cols-1 gap-6 xl:grid-cols-[minmax(18rem,0.95fr)_minmax(36rem,3fr)_minmax(18rem,0.95fr)]">
        <div className="min-h-[300px] xl:min-h-0">
          <StockPool selectedSymbol={selectedSymbol} onSelect={setSelectedSymbol} />
        </div>

        <div className="min-h-[400px] xl:min-h-0">
          <ResearchReport
            symbol={selectedSymbol}
            taskId={taskId}
            isLoading={isResearching || isValidatingTask}
            errorMessage={taskError}
          />
        </div>

        <div className="min-h-[300px] xl:min-h-0">
          <AgentExecution
            taskId={taskId}
            steps={steps}
            totalDuration={totalDuration}
          />
        </div>
      </div>
    </div>
  )
}
