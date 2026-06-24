import { 
  Brain, 
  CheckCircle, 
  Clock, 
  AlertCircle,
  Loader2
} from 'lucide-react'

interface PlannerCardProps {
  status: 'pending' | 'running' | 'completed' | 'error'
  planReasoning?: string
  subtaskCount?: number
  confidence?: number
}

export default function PlannerCard({ 
  status, 
  planReasoning, 
  subtaskCount = 0, 
  confidence = 0 
}: PlannerCardProps) {
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

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-dark-hover rounded-lg flex items-center justify-center">
            <Brain className="w-5 h-5 text-primary-300" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-primary-50">Planner</h3>
            <p className="text-xs text-primary-400">Task Decomposition Agent</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          {getStatusBadge()}
        </div>
      </div>

      {planReasoning && (
        <div className="mb-4 p-3 bg-dark-bg rounded-lg border border-dark-border">
          <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-2">
            Plan Reasoning
          </p>
          <p className="text-sm text-primary-200 leading-relaxed">
            {planReasoning}
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
          <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-1">
            Subtasks
          </p>
          <p className="text-2xl font-bold text-primary-50">{subtaskCount}</p>
        </div>
        <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
          <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-1">
            Confidence
          </p>
          <p className="text-2xl font-bold text-primary-50">
            {confidence > 0 ? `${(confidence * 100).toFixed(1)}%` : '-'}
          </p>
        </div>
      </div>

      {status === 'running' && (
        <div className="mt-4">
          <div className="flex justify-between text-xs text-primary-400 mb-1">
            <span>Analyzing complexity...</span>
            <span>Processing</span>
          </div>
          <div className="w-full bg-dark-border rounded-full h-2">
            <div className="bg-primary-500 h-2 rounded-full animate-pulse" style={{ width: '60%' }} />
          </div>
        </div>
      )}
    </div>
  )
}