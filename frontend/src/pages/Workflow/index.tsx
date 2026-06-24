import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useWorkflow } from './hooks/useWorkflow'
import { WorkflowHeader } from './components/WorkflowHeader'
import { DAGPanel } from './components/DAGPanel'
import { DetailPanel } from './components/DetailPanel'
import { MetricsPanel } from './components/MetricsPanel'
import { EventLog } from './components/EventLog'
import { Loader2, ArrowLeft, RefreshCw } from 'lucide-react'

export default function WorkflowVisualization() {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [state, actions] = useWorkflow()

  // Connect to SSE on mount
  useEffect(() => {
    if (taskId) {
      actions.connect(taskId)
    }

    return () => {
      actions.disconnect()
    }
  }, [taskId, actions])

  // Loading state
  if (state.status === 'connecting') {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">{t('workflow.connecting')}</p>
        </div>
      </div>
    )
  }

  // Error state
  if (state.status === 'error') {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-center">
          <div className="text-red-500 text-4xl mb-4">⚠</div>
          <p className="text-gray-300 mb-4">{t('workflow.connectFailed')}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={actions.retryConnection}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              {t('workflow.retry')}
            </button>
            <button
              onClick={() => navigate(-1)}
              className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition-colors"
            >
              {t('workflow.goBack')}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Back button */}
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">{t('workflow.back')}</span>
        </button>

        {/* Header */}
        <WorkflowHeader
          query={state.query}
          traceId={state.traceId}
          status={state.status}
          totalTasks={state.metrics.totalTasks}
          completedTasks={state.metrics.completedTasks}
        />

        {/* Main content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* DAG Panel - takes 2 columns */}
          <div className="lg:col-span-2">
            <DAGPanel
              nodes={state.nodes}
              edges={state.edges}
              selectedTaskId={state.selectedTaskId}
              onSelectTask={actions.selectTask}
            />
          </div>

          {/* Side panel */}
          <div className="space-y-4">
            {/* Detail Panel */}
            {state.selectedTask && (
              <DetailPanel
                task={state.selectedTask}
                onClose={() => actions.selectTask(null)}
              />
            )}

            {/* Event Log */}
            <EventLog events={state.events} />
          </div>
        </div>

        {/* Metrics */}
        <MetricsPanel
          totalTasks={state.metrics.totalTasks}
          completedTasks={state.metrics.completedTasks}
          failedTasks={state.metrics.failedTasks}
          totalDuration={state.metrics.totalDuration}
          avgTaskDuration={state.metrics.avgTaskDuration}
        />
      </div>
    </div>
  )
}
