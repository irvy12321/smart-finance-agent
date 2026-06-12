import type { TaskResult } from '../types'
import { TOOL_DISPLAY_NAMES, NODE_STYLES } from '../types'

interface DetailPanelProps {
  task: TaskResult | null
  onClose: () => void
}

export function DetailPanel({ task, onClose }: DetailPanelProps) {
  if (!task) {
    return null
  }

  const style = NODE_STYLES[task.status]
  const displayName = TOOL_DISPLAY_NAMES[task.tool] || task.tool

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-gray-750 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <span className="text-lg">{style.icon}</span>
          <span className="font-medium text-white">{displayName}</span>
          <span
            className="px-2 py-0.5 rounded-full text-xs font-medium"
            style={{ backgroundColor: `${style.color}20`, color: style.color }}
          >
            {task.status}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white transition-colors"
        >
          ✕
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Duration */}
        <div>
          <span className="text-xs text-gray-500 uppercase tracking-wider">Duration</span>
          <p className="text-sm text-gray-300 mt-1">
            {(task.duration_ms / 1000).toFixed(2)}s ({task.duration_ms.toFixed(0)}ms)
          </p>
        </div>

        {/* Task ID */}
        <div>
          <span className="text-xs text-gray-500 uppercase tracking-wider">Task ID</span>
          <p className="text-sm text-gray-300 mt-1 font-mono">{task.task_id}</p>
        </div>

        {/* Error */}
        {task.error && (
          <div>
            <span className="text-xs text-red-400 uppercase tracking-wider">Error</span>
            <p className="text-sm text-red-300 mt-1 bg-red-900/20 p-2 rounded">{task.error}</p>
          </div>
        )}

        {/* Result Data */}
        {task.data && (
          <div>
            <span className="text-xs text-gray-500 uppercase tracking-wider">Result</span>
            <div className="mt-1 bg-gray-900 rounded p-3 max-h-[200px] overflow-auto">
              <pre className="text-xs text-gray-300 whitespace-pre-wrap">
                {typeof task.data === 'string' ? task.data : JSON.stringify(task.data, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
