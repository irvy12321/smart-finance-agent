import { useState } from 'react'
import type { WorkflowEvent } from '../types'

interface EventLogProps {
  events: WorkflowEvent[]
}

export function EventLog({ events }: EventLogProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const displayEvents = isExpanded ? events : events.slice(-5)

  const getEventColor = (stage: string) => {
    switch (stage) {
      case 'task_start': return 'text-blue-400'
      case 'task_complete': return 'text-green-400'
      case 'error': return 'text-red-400'
      case 'complete': return 'text-emerald-400'
      default: return 'text-gray-400'
    }
  }

  const getEventIcon = (stage: string) => {
    switch (stage) {
      case 'task_start': return '▶'
      case 'task_complete': return '✓'
      case 'error': return '✗'
      case 'complete': return '●'
      default: return '·'
    }
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700">
        <span className="text-sm font-medium text-gray-300">Event Log</span>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          {isExpanded ? 'Show Less' : `Show All (${events.length})`}
        </button>
      </div>

      <div className="p-2 max-h-[200px] overflow-y-auto">
        {displayEvents.length === 0 ? (
          <p className="text-xs text-gray-500 text-center py-4">No events yet</p>
        ) : (
          <div className="space-y-1">
            {displayEvents.map((event, index) => (
              <div
                key={index}
                className="flex items-start gap-2 px-2 py-1 rounded hover:bg-gray-750"
              >
                <span className={`text-xs mt-0.5 ${getEventColor(event.stage)}`}>
                  {getEventIcon(event.stage)}
                </span>
                <div className="flex-1 min-w-0">
                  <span className={`text-xs font-medium ${getEventColor(event.stage)}`}>
                    {event.stage}
                  </span>
                  {event.task_id && (
                    <span className="text-xs text-gray-500 ml-2">
                      {event.task_id}
                    </span>
                  )}
                  {event.tool && (
                    <span className="text-xs text-gray-500 ml-1">
                      ({event.tool})
                    </span>
                  )}
                  {event.duration_ms !== undefined && (
                    <span className="text-xs text-gray-500 ml-1">
                      {(event.duration_ms / 1000).toFixed(1)}s
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
