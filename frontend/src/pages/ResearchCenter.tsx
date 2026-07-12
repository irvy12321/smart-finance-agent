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
  steps: TaskStep[]
  totalDuration?: number
  startedAt?: number
}

const STORAGE_KEY = 'research_center_state'
const POLL_INTERVAL = 2000
const RESEARCH_TIMEOUT_MS = 300000

function createInitialSteps(): TaskStep[] {
  return [
    { name: 'Planner', status: 'running', icon: null, color: 'text-primary-300' },
    { name: 'News Search', status: 'pending', icon: null, color: 'text-blue-400' },
    { name: 'RAG Retrieve', status: 'pending', icon: null, color: 'text-cyan-400' },
    { name: 'Financial Report', status: 'pending', icon: null, color: 'text-green-400' },
    { name: 'Synthesizer', status: 'pending', icon: null, color: 'text-yellow-400' },
    { name: 'Report', status: 'pending', icon: null, color: 'text-emerald-400' },
  ]
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

function updateStepsForStage(prev: TaskStep[], status: TaskStatusResponse, elapsed: number): TaskStep[] {
  if (status.status === 'completed') {
    const duration = elapsed / Math.max(prev.length, 1)
    return prev.map((step) => ({ ...step, status: 'completed', duration }))
  }

  if (status.status === 'failed') {
    return prev.map((step) => (step.status === 'running' ? { ...step, status: 'failed' } : step))
  }

  if (status.current_stage === 'planning') {
    return prev.map((step) => (step.name === 'Planner' ? { ...step, status: 'running' } : step))
  }

  if (status.current_stage === 'executing') {
    return prev.map((step) =>
      step.name === 'Planner' ? { ...step, status: 'completed', duration: elapsed * 0.2 } :
      step.name === 'News Search' ? { ...step, status: 'running' } :
      step.name === 'RAG Retrieve' ? { ...step, status: 'running' } :
      step.name === 'Financial Report' ? { ...step, status: 'running' } :
      step
    )
  }

  if (status.current_stage === 'reasoning') {
    return prev.map((step) =>
      step.name !== 'Synthesizer' && step.name !== 'Report' && step.status !== 'completed'
        ? { ...step, status: 'completed', duration: elapsed * 0.15 } :
      step.name === 'Synthesizer' ? { ...step, status: 'running' } :
      step
    )
  }

  if (status.current_stage === 'reporting') {
    return prev.map((step) =>
      step.name === 'Synthesizer' ? { ...step, status: 'completed', duration: elapsed * 0.1 } :
      step.name === 'Report' ? { ...step, status: 'running' } :
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

  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(initialState?.selectedSymbol || null)
  const [taskId, setTaskId] = useState<string | null>(initialState?.taskId || null)
  const [isResearching, setIsResearching] = useState(Boolean(initialState?.isResearching))
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
    try {
      const status = await taskApi.getStatus(id)
      const elapsed = Date.now() - startTime

      setTotalDuration(elapsed)
      setSteps((prev) => updateStepsForStage(prev.length ? prev : createInitialSteps(), status, elapsed))

      if (status.status === 'completed') {
        stopPolling()
        setIsResearching(false)
        toast.success(t('common.success'), t('research.completed'))
        return
      }

      if (status.status === 'failed') {
        stopPolling()
        setIsResearching(false)
        toast.error(t('common.error'), t('research.taskFailed'))
        return
      }

      if (elapsed > RESEARCH_TIMEOUT_MS) {
        stopPolling()
        setIsResearching(false)
        setSteps((prev) => prev.map((step) => (step.status === 'running' ? { ...step, status: 'failed' } : step)))
        toast.error(t('common.error'), t('error.timeout'))
      }
    } catch (err) {
      console.error('Polling error:', err)
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
      steps,
      totalDuration,
      startedAt,
    })
  }, [isResearching, selectedSymbol, startedAt, steps, taskId, totalDuration])

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
      setTaskId(null)
      setStartedAt(startTime)
      setTotalDuration(undefined)
      setSteps(initialSteps)

      const query = `Analyze ${selectedSymbol} stock performance and provide comprehensive research report`
      const task = await taskApi.create(query, 1)

      setTaskId(task.task_id)
      await taskApi.run(task.task_id)
      startPolling(task.task_id, startTime)
    } catch (err) {
      stopPolling()
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
            isLoading={isResearching}
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
