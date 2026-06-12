import { memo } from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import type { TaskNodeData } from '../types'
import { NODE_STYLES } from '../types'

function SynthesizerNodeComponent({ data, selected }: NodeProps<TaskNodeData>) {
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
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 !bg-gray-500"
      />

      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">🔄</span>
        <span className="font-medium text-sm text-cyan-400">Synthesizer</span>
      </div>

      <div className="flex items-center gap-2 text-xs text-gray-400">
        <span className="px-1.5 py-0.5 rounded-full text-xs font-medium bg-cyan-500/20 text-cyan-400">
          {data.status === 'running' ? 'Synthesizing...' : data.status === 'success' ? 'Done' : 'Waiting'}
        </span>
        {data.duration_ms > 0 && (
          <span>{(data.duration_ms / 1000).toFixed(1)}s</span>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 !bg-cyan-500"
      />
    </div>
  )
}

export const SynthesizerNode = memo(SynthesizerNodeComponent)
