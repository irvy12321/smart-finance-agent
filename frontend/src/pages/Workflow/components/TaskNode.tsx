import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { useTranslation } from 'react-i18next'
import type { TaskNodeData } from '../types'
import { NODE_STYLES, TOOL_DISPLAY_NAMES } from '../types'

function TaskNodeComponent({ data, selected }: NodeProps<TaskNodeData>) {
  const { t } = useTranslation()
  const style = NODE_STYLES[data.status]
  const displayName = TOOL_DISPLAY_NAMES[data.tool] || data.label

  return (
    <div
      className="relative px-4 py-3 rounded-lg shadow-lg min-w-[160px] transition-all duration-300"
      style={{
        border: style.border,
        backgroundColor: style.backgroundColor,
        boxShadow: selected ? `0 0 0 2px ${style.color}` : undefined,
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 !bg-gray-500"
      />

      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{style.icon}</span>
        <span className="font-medium text-sm" style={{ color: style.color }}>
          {displayName}
        </span>
      </div>

      <div className="flex items-center gap-2 text-xs text-gray-400">
        <span
          className="px-1.5 py-0.5 rounded-full text-xs font-medium"
          style={{
            backgroundColor: `${style.color}20`,
            color: style.color,
          }}
        >
          {t(`workflow.status.${data.status}`)}
        </span>
        {data.duration_ms > 0 && (
          <span>{(data.duration_ms / 1000).toFixed(1)}s</span>
        )}
      </div>

      {data.description && (
        <div className="mt-1 text-xs text-gray-500 truncate max-w-[140px]">
          {data.description}
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 !bg-gray-500"
      />
    </div>
  )
}

export const TaskNode = memo(TaskNodeComponent)
