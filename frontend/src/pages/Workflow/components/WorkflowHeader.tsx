interface WorkflowHeaderProps {
  query: string | null
  traceId: string | null
  status: string
  totalTasks: number
  completedTasks: number
}

export function WorkflowHeader({ query, traceId, status, totalTasks, completedTasks }: WorkflowHeaderProps) {
  const statusColors: Record<string, string> = {
    idle: 'bg-gray-500/20 text-gray-400',
    connecting: 'bg-yellow-500/20 text-yellow-400',
    running: 'bg-blue-500/20 text-blue-400',
    completed: 'bg-green-500/20 text-green-400',
    error: 'bg-red-500/20 text-red-400',
  }

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-white">Agent Workflow</h2>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[status] || statusColors.idle}`}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </span>
          {traceId && (
            <span className="px-2 py-1 bg-gray-700 rounded text-xs text-gray-400 font-mono">
              Trace: {traceId}
            </span>
          )}
        </div>
      </div>

      {query && (
        <div className="mb-3">
          <span className="text-xs text-gray-500 uppercase tracking-wider">Query</span>
          <p className="text-sm text-gray-300 mt-1">{query}</p>
        </div>
      )}

      <div className="flex gap-4">
        <div>
          <span className="text-xs text-gray-500 uppercase tracking-wider">Tasks</span>
          <p className="text-sm text-gray-300">{completedTasks} / {totalTasks}</p>
        </div>
      </div>
    </div>
  )
}
