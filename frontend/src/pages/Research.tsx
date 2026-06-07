import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Play, 
  Loader2, 
  CheckCircle, 
  AlertCircle,
  Brain,
  Zap,
  Lightbulb,
  FileText
} from 'lucide-react'
import PlannerCard from '../components/PlannerCard'
import ExecutorCard from '../components/ExecutorCard'
import ReasonerCard from '../components/ReasonerCard'
import { useTask } from '../hooks/useApi'

export default function Research() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const cleanupRef = useRef<(() => void) | null>(null)
  const {
    taskId,
    status,
    progress,
    currentStage,
    result,
    error,
    createTask,
    runTask,
    resetTask,
  } = useTask()

  useEffect(() => {
    return () => {
      cleanupRef.current?.()
    }
  }, [])

  const handleStartResearch = async () => {
    if (!query.trim()) return

    try {
      const newTaskId = await createTask(query)
      const cleanup = await runTask(newTaskId)
      cleanupRef.current = cleanup || null
    } catch (err) {
      console.error('Research failed:', err)
    }
  }

  const handleViewReport = () => {
    if (taskId) {
      navigate(`/report/${taskId}`)
    }
  }

  const handleReset = () => {
    cleanupRef.current?.()
    cleanupRef.current = null
    resetTask()
    setQuery('')
  }

  const getPlannerStatus = () => {
    if (status === 'idle' || status === 'pending') return 'pending'
    if (status === 'error') return 'error'
    if (progress >= 30) return 'completed'
    if (status === 'running') return 'running'
    return 'pending'
  }

  const getExecutorStatus = () => {
    if (status === 'idle' || status === 'pending') return 'pending'
    if (status === 'error') return 'error'
    if (progress >= 80) return 'completed'
    if (status === 'running' && progress >= 30) return 'running'
    return 'pending'
  }

  const getReasonerStatus = () => {
    if (status === 'idle' || status === 'pending') return 'pending'
    if (status === 'error') return 'error'
    if (progress >= 90) return 'completed'
    if (status === 'running' && progress >= 80) return 'running'
    return 'pending'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-primary-50">New Research Query</h1>
        <p className="text-sm text-primary-400 mt-1">
          Enter your financial research question to start analysis
        </p>
      </div>

      {/* Query Input */}
      <div className="card">
        <div className="flex gap-4">
          <div className="flex-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your financial research question (e.g., 'Analyze the impact of AI adoption on semiconductor sector valuations')"
              className="input"
              disabled={status === 'running' || status === 'pending'}
            />
          </div>
          <button
            onClick={handleStartResearch}
            disabled={!query.trim() || status === 'running' || status === 'pending'}
            className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {status === 'running' || status === 'pending' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {status === 'running' || status === 'pending' ? 'Running...' : 'Run Research'}
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="card border-red-500/30">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <div>
              <p className="text-sm font-medium text-red-500">Research Failed</p>
              <p className="text-xs text-red-400 mt-1">{error}</p>
            </div>
          </div>
          <button
            onClick={handleReset}
            className="mt-3 text-sm text-red-500 hover:text-red-400"
          >
            Try again
          </button>
        </div>
      )}

      {/* Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <PlannerCard
          status={getPlannerStatus()}
          planReasoning={result?.plan_reasoning}
          subtaskCount={result?.total_tasks}
          confidence={result?.confidence}
        />
        <ExecutorCard
          status={getExecutorStatus()}
          totalTasks={result?.total_tasks}
          completedTasks={result?.success_tasks ? result.success_tasks + (result.failed_tasks || 0) : 0}
          successTasks={result?.success_tasks}
          failedTasks={result?.failed_tasks}
          currentTask={currentStage === 'executing' ? 'Executing tasks...' : undefined}
        />
        <ReasonerCard
          status={getReasonerStatus()}
          confidence={result?.confidence}
          keyInsights={result?.reasoning_insights}
          reasoning={result?.plan_reasoning}
        />
      </div>

      {/* Progress Bar */}
      {status === 'running' && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              <span className="text-sm font-medium text-primary-200">
                {currentStage === 'planning' && 'Planning: Analyzing complexity and selecting strategy...'}
                {currentStage === 'executing' && 'Executing: Running subtasks in parallel...'}
                {currentStage === 'reasoning' && 'Reasoning: Extracting insights and generating charts...'}
                {currentStage === 'reporting' && 'Reporting: Compiling structured research report...'}
                {!currentStage && 'Processing...'}
              </span>
            </div>
            <span className="text-sm font-semibold text-primary-500">
              {progress.toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-dark-border rounded-full h-3">
            <div 
              className="bg-gradient-to-r from-primary-500 to-blue-500 h-3 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Success State */}
      {status === 'completed' && result && (
        <div className="card border-green-500/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-6 h-6 text-green-500" />
              <div>
                <p className="text-sm font-medium text-green-500">
                  Research Completed Successfully
                </p>
                <p className="text-xs text-green-400 mt-1">
                  {result.total_tasks} tasks completed in {result.elapsed?.toFixed(1)}s
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleReset}
                className="text-sm text-primary-400 hover:text-primary-200 transition-colors"
              >
                New Research
              </button>
              <button
                onClick={handleViewReport}
                className="btn-primary flex items-center gap-2"
              >
                <FileText className="w-4 h-4" />
                View Report
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Quick Stats */}
      {result && (
        <div className="grid grid-cols-4 gap-4">
          <div className="card text-center">
            <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center mx-auto mb-2">
              <Brain className="w-5 h-5 text-blue-500" />
            </div>
            <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider">
              Tasks
            </p>
            <p className="text-2xl font-bold text-primary-50">{result.total_tasks || 0}</p>
          </div>
          <div className="card text-center">
            <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center mx-auto mb-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
            </div>
            <p className="text-xs font-semibold text-green-400 uppercase tracking-wider">
              Success
            </p>
            <p className="text-2xl font-bold text-green-500">{result.success_tasks || 0}</p>
          </div>
          <div className="card text-center">
            <div className="w-10 h-10 bg-yellow-500/10 rounded-lg flex items-center justify-center mx-auto mb-2">
              <Lightbulb className="w-5 h-5 text-yellow-500" />
            </div>
            <p className="text-xs font-semibold text-yellow-400 uppercase tracking-wider">
              Confidence
            </p>
            <p className="text-2xl font-bold text-yellow-500">
              {result.confidence ? `${(result.confidence * 100).toFixed(0)}%` : '-'}
            </p>
          </div>
          <div className="card text-center">
            <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center mx-auto mb-2">
              <Zap className="w-5 h-5 text-purple-500" />
            </div>
            <p className="text-xs font-semibold text-purple-400 uppercase tracking-wider">
              Insights
            </p>
            <p className="text-2xl font-bold text-purple-500">
              {result.reasoning_insights?.length || 0}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
