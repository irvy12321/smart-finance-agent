import { 
  Lightbulb, 
  CheckCircle, 
  Clock, 
  AlertCircle,
  Loader2,
  TrendingUp
} from 'lucide-react'

interface ReasonerCardProps {
  status: 'pending' | 'running' | 'completed' | 'error'
  confidence?: number
  keyInsights?: string[]
  reasoning?: string
}

export default function ReasonerCard({ 
  status, 
  confidence = 0, 
  keyInsights = [], 
  reasoning 
}: ReasonerCardProps) {
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
          <div className="w-10 h-10 bg-yellow-500/10 rounded-lg flex items-center justify-center">
            <Lightbulb className="w-5 h-5 text-yellow-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-primary-50">Reasoner</h3>
            <p className="text-xs text-primary-400">Multi-step Reasoning Agent</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          {getStatusBadge()}
        </div>
      </div>

      {reasoning && (
        <div className="mb-4 p-3 bg-dark-bg rounded-lg border border-dark-border">
          <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-2">
            Reasoning
          </p>
          <p className="text-sm text-primary-200 leading-relaxed">
            {reasoning}
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
          <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-1">
            Confidence
          </p>
          <p className="text-2xl font-bold text-primary-50">
            {confidence > 0 ? `${(confidence * 100).toFixed(1)}%` : '-'}
          </p>
        </div>
        <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
          <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-1">
            Insights
          </p>
          <p className="text-2xl font-bold text-primary-50">{keyInsights.length}</p>
        </div>
      </div>

      {keyInsights.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-3">
            Key Insights
          </p>
          <div className="space-y-2">
            {keyInsights.slice(0, 3).map((insight, index) => (
              <div key={index} className="flex items-start gap-2 p-2 bg-dark-bg rounded-lg border border-dark-border">
                <TrendingUp className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-primary-200">{insight}</p>
              </div>
            ))}
            {keyInsights.length > 3 && (
              <p className="text-xs text-primary-400 text-center">
                +{keyInsights.length - 3} more insights
              </p>
            )}
          </div>
        </div>
      )}

      {status === 'running' && (
        <div className="mt-4">
          <div className="flex justify-between text-xs text-primary-400 mb-1">
            <span>Extracting insights...</span>
            <span>Analyzing</span>
          </div>
          <div className="w-full bg-dark-border rounded-full h-2">
            <div className="bg-yellow-500 h-2 rounded-full animate-pulse" style={{ width: '70%' }} />
          </div>
        </div>
      )}
    </div>
  )
}