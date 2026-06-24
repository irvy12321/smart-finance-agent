import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { useTranslation } from 'react-i18next'
import type { TaskNodeData } from '../types'
import { NODE_STYLES } from '../types'

function PlannerNodeComponent({ data, selected }: NodeProps<TaskNodeData>) {
  const { t } = useTranslation()
  const style = NODE_STYLES[data.status]

  return (
    <div
      className="relative px-4 py-3 rounded-lg shadow-lg min-w-[160px] transition-all duration-300"
      style={{
        border: style.border,
        backgroundColor: style.backgroundColor,
        boxShadow: selected ? `0 0 0 2px ${style.color}` : undefined,
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">🧠</span>
        <span className="font-medium text-sm text-primary-300">{t('workflow.planner')}</span>
      </div>

      <div className="flex items-center gap-2 text-xs text-gray-400">
        <span className="px-1.5 py-0.5 rounded-full text-xs font-medium bg-dark-hover text-primary-300">
          {data.status === 'running' ? t('workflow.planning') : data.status === 'success' ? t('workflow.planReady') : t('workflow.waiting')}
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 !bg-primary-500"
      />
    </div>
  )
}

export const PlannerNode = memo(PlannerNodeComponent)
