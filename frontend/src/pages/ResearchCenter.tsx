import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { PageHeader } from '../components/layout'
import { StockPool, ResearchReport, AgentExecution } from '../components/research'
import { Plus, Loader2 } from 'lucide-react'
import { taskApi } from '../services/api'
import { useToast } from '../components/ui/ToastContext'

interface TaskStep {
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  duration?: number
  icon: any
  color: string
}

export default function ResearchCenter() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const toast = useToast()
  const [searchParams] = useSearchParams()
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [isResearching, setIsResearching] = useState(false)
  const [steps, setSteps] = useState<TaskStep[]>([])
  const [totalDuration, setTotalDuration] = useState<number | undefined>()

  // Prefill the research symbol from the top-bar search query (?q=...).
  useEffect(() => {
    const q = searchParams.get('q')?.trim()
    if (q) setSelectedSymbol(q.toUpperCase())
  }, [searchParams])

  const handleNewResearch = async () => {
    if (!selectedSymbol) {
      toast.error(t('common.error'), t('stock.enterSymbol'))
      return
    }

    try {
      setIsResearching(true)
      setSteps([
        { name: 'Planner', status: 'running', icon: null, color: 'text-primary-300' },
        { name: 'News Search', status: 'pending', icon: null, color: 'text-blue-400' },
        { name: 'RAG Retrieve', status: 'pending', icon: null, color: 'text-cyan-400' },
        { name: 'Financial Report', status: 'pending', icon: null, color: 'text-green-400' },
        { name: 'Synthesizer', status: 'pending', icon: null, color: 'text-yellow-400' },
        { name: 'Report', status: 'pending', icon: null, color: 'text-emerald-400' },
      ])

      // Create task
      const query = `Analyze ${selectedSymbol} stock performance and provide comprehensive research report`
      const task = await taskApi.create(query, 1)
      setTaskId(task.task_id)

      // Run task
      await taskApi.run(task.task_id)

      // Poll for status
      const startTime = Date.now()
      const pollInterval = setInterval(async () => {
        try {
          const status = await taskApi.getStatus(task.task_id)

          // Update steps based on progress
          const elapsed = Date.now() - startTime
          setTotalDuration(elapsed)

          if (status.current_stage === 'planning') {
            setSteps(prev => prev.map(s =>
              s.name === 'Planner' ? { ...s, status: 'running' } : s
            ))
          } else if (status.current_stage === 'executing') {
            setSteps(prev => prev.map(s =>
              s.name === 'Planner' ? { ...s, status: 'completed', duration: elapsed * 0.2 } :
              s.name === 'News Search' ? { ...s, status: 'running' } :
              s.name === 'RAG Retrieve' ? { ...s, status: 'running' } :
              s.name === 'Financial Report' ? { ...s, status: 'running' } :
              s
            ))
          } else if (status.current_stage === 'reasoning') {
            setSteps(prev => prev.map(s =>
              s.name !== 'Synthesizer' && s.name !== 'Report' && s.status !== 'completed'
                ? { ...s, status: 'completed', duration: elapsed * 0.15 } :
              s.name === 'Synthesizer' ? { ...s, status: 'running' } :
              s
            ))
          } else if (status.current_stage === 'reporting') {
            setSteps(prev => prev.map(s =>
              s.name === 'Synthesizer' ? { ...s, status: 'completed', duration: elapsed * 0.1 } :
              s.name === 'Report' ? { ...s, status: 'running' } :
              s
            ))
          }

          if (status.status === 'completed') {
            clearInterval(pollInterval)
            setSteps(prev => prev.map(s => ({ ...s, status: 'completed', duration: elapsed / steps.length })))
            setIsResearching(false)
            toast.success(t('common.success'), t('research.completed'))
          } else if (status.status === 'failed') {
            clearInterval(pollInterval)
            setSteps(prev => prev.map(s =>
              s.status === 'running' ? { ...s, status: 'failed' } : s
            ))
            setIsResearching(false)
            toast.error(t('common.error'), t('research.taskFailed'))
          }
        } catch (err) {
          console.error('Polling error:', err)
        }
      }, 2000)

      // Cleanup after 5 minutes
      setTimeout(() => {
        clearInterval(pollInterval)
        if (isResearching) {
          setIsResearching(false)
          toast.error(t('common.error'), t('error.timeout'))
        }
      }, 300000)
    } catch (err) {
      setIsResearching(false)
      toast.error(t('common.error'), err instanceof Error ? err.message : t('research.taskFailed'))
    }
  }

  const handleViewReport = () => {
    if (taskId) {
      navigate(`/report/${taskId}`)
    }
  }

  return (
    <div className="p-4 lg:p-6 h-full flex flex-col">
      <PageHeader
        title={t('research.title')}
        subtitle={t('research.startResearch')}
      >
        <button
          onClick={handleNewResearch}
          disabled={isResearching || !selectedSymbol}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-primary-500 hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed rounded transition-colors"
        >
          {isResearching ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Plus className="w-3.5 h-3.5" />
          )}
          {isResearching ? t('research.analyzing') : t('research.newTask')}
        </button>
        {taskId && !isResearching && (
          <button
            onClick={handleViewReport}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-primary-400 hover:text-primary-200 bg-dark-card border border-dark-border rounded transition-colors"
          >
            {t('report.viewFullReport')}
          </button>
        )}
      </PageHeader>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-5 gap-4 min-h-0">
        <div className="lg:col-span-1 min-h-[300px] lg:min-h-0">
          <StockPool selectedSymbol={selectedSymbol} onSelect={setSelectedSymbol} />
        </div>

        <div className="lg:col-span-3 min-h-[400px] lg:min-h-0">
          <ResearchReport
            symbol={selectedSymbol}
            taskId={taskId}
            isLoading={isResearching}
          />
        </div>

        <div className="lg:col-span-1 min-h-[300px] lg:min-h-0">
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
