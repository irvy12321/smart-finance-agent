import { useTranslation } from 'react-i18next'
import { Brain, CheckCircle, Loader2, Clock, AlertCircle } from 'lucide-react'

interface AgentStep {
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  duration?: number
}

interface AgentExecutionProps {
  taskId: string | null
  steps?: AgentStep[]
  traceId?: string
  totalDuration?: number
}

export default function AgentExecution({ taskId, steps = [], traceId, totalDuration }: AgentExecutionProps) {
  const { t } = useTranslation()
  const completedSteps = steps.filter(s => s.status === 'completed').length
  const totalSteps = steps.length

  if (!taskId) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg h-full flex items-center justify-center">
        <div className="text-center text-primary-500">
          <Brain className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-xs">{t('system.agents')}</p>
        </div>
      </div>
    )
  }

  if (steps.length === 0) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg h-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-6 h-6 text-primary-500 animate-spin mx-auto mb-2" />
          <p className="text-xs text-primary-400">{t('common.loading')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="px-3 py-2 border-b border-dark-border">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('system.agents')}</span>
          {taskId && (
            <span className="text-xs text-primary-500 font-mono">#{taskId}</span>
          )}
        </div>
        {traceId && (
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-primary-500">Trace:</span>
            <span className="text-xs text-primary-400 font-mono">{traceId}</span>
          </div>
        )}
      </div>

      {/* Steps */}
      <div className="flex-1 overflow-auto p-3 space-y-2">
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1
          return (
            <div key={step.name}>
              <div className="flex items-center gap-3">
                {/* Status Icon */}
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                  step.status === 'completed' ? 'bg-green-500/10' :
                  step.status === 'running' ? 'bg-blue-500/10' :
                  step.status === 'failed' ? 'bg-red-500/10' :
                  'bg-dark-bg'
                }`}>
                  {step.status === 'completed' ? (
                    <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                  ) : step.status === 'running' ? (
                    <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin" />
                  ) : step.status === 'failed' ? (
                    <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                  ) : (
                    <div className="w-2 h-2 bg-primary-500 rounded-full" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-medium ${
                      step.status === 'completed' ? 'text-primary-200' :
                      step.status === 'running' ? 'text-blue-400' :
                      step.status === 'failed' ? 'text-red-400' :
                      'text-primary-500'
                    }`}>
                      {step.name}
                    </span>
                    {step.duration && (
                      <span className="text-xs text-primary-500 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {(step.duration / 1000).toFixed(1)}s
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Connector */}
              {!isLast && (
                <div className="ml-3 pl-3 border-l border-dark-border h-2" />
              )}
            </div>
          )
        })}
      </div>

      {/* Footer */}
      <div className="px-3 py-2 border-t border-dark-border bg-dark-bg/50">
        <div className="flex items-center justify-between">
          <span className="text-xs text-primary-500">
            {t('common.status')}: {completedSteps}/{totalSteps}
          </span>
          {totalDuration && (
            <span className="text-xs text-primary-500">
              {t('system.avgLatency')}: {(totalDuration / 1000).toFixed(1)}s
            </span>
          )}
        </div>
        <div className="w-full bg-dark-border rounded-full h-1.5 mt-1">
          <div
            className="bg-primary-500 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${(completedSteps / totalSteps) * 100}%` }}
          />
        </div>
      </div>
    </div>
  )
}
