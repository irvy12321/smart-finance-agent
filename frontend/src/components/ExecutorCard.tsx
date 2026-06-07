import { 
  Zap, 
  CheckCircle, 
  Clock, 
  AlertCircle,
  Loader2,
  Play
} from 'lucide-react'

interface ExecutorCardProps {
  status: 'pending' | 'running' | 'completed' | 'error'
  totalTasks?: number
  completedTasks?: number
  successTasks?: number
  failedTasks?: number
  currentTask?: string
}

export default function ExecutorCard({ 
  status, 
  totalTasks = 0, 
  completedTasks = 0, 
  successTasks = 0, 
  failedTasks = 0,
  currentTask
}: ExecutorCardProps) {
  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'running':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />
      default:
        return <Clock className="w-5 h-5 text-yellow-500" />
    }
  }

  const getStatusBadge = () => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-success">COMPLETED</span>
      case 'running':
        return <span className="badge badge-running">RUNNING</span>
      case 'error':
        return <span className="badge badge-error">ERROR</span>
      default:
        return <span className="badge badge-pending">PENDING</span>
    }
  }

  const progress = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
            <Zap className="w-5 h-5 text-blue-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-primary-50">Executor</h3>
            <p className="text-xs text-primary-400">Parallel Task Execution Agent</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          {getStatusBadge()}
        </div>
      </div>

      {currentTask && (
        <div className="mb-4 p-3 bg-dark-bg rounded-lg border border-dark-border">
          <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-2">
            Current Task
          </p>
          <div className="flex items-center gap-2">
            <Play className="w-4 h-4 text-blue-500" />
            <p className="text-sm text-primary-200">{currentTask}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
          <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-1">
            Total Tasks
          </p>
          <p className="text-2xl font-bold text-primary-50">{totalTasks}</p>
        </div>
        <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
          <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-1">
            Completed
          </p>
          <p className="text-2xl font-bold text-primary-50">{completedTasks}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
          <p className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-1">
            Success
          </p>
          <p className="text-2xl font-bold text-green-500">{successTasks}</p>
        </div>
        <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
          <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-1">
            Failed
          </p>
          <p className="text-2xl font-bold text-red-500">{failedTasks}</p>
        </div>
      </div>

      {status === 'running' && (
        <div className="mt-4">
          <div className="flex justify-between text-xs text-primary-400 mb-1">
            <span>Executing tasks...</span>
            <span>{completedTasks}/{totalTasks}</span>
          </div>
          <div className="w-full bg-dark-border rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-300" 
              style={{ width: `${progress}%` }} 
            />
          </div>
        </div>
      )}
    </div>
  )
}