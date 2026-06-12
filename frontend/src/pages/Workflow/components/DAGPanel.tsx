import { useCallback } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  ConnectionLineType,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { TaskNode } from './TaskNode'
import { PlannerNode } from './PlannerNode'
import { SynthesizerNode } from './SynthesizerNode'
import { ReportNode } from './ReportNode'
import { useDAGLayout } from '../hooks/useDAGLayout'
import type { TaskNodeData } from '../types'

// Register custom node types
const nodeTypes = {
  taskNode: TaskNode,
  plannerNode: PlannerNode,
  synthesizerNode: SynthesizerNode,
  reportNode: ReportNode,
}

interface DAGPanelProps {
  nodes: Node<TaskNodeData>[]
  edges: Edge[]
  selectedTaskId: string | null
  onSelectTask: (taskId: string | null) => void
}

export function DAGPanel({ nodes: inputNodes, edges: inputEdges, onSelectTask }: DAGPanelProps) {
  // Apply dagre layout
  const { nodes: layoutedNodes, edges: layoutedEdges } = useDAGLayout(inputNodes, inputEdges)

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges)

  // Update nodes when layout changes
  useCallback(() => {
    setNodes(layoutedNodes)
    setEdges(layoutedEdges)
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges])()

  // Handle node click
  const onNodeClick = useCallback((_: React.MouseEvent, node: Node<TaskNodeData>) => {
    onSelectTask(node.id)
  }, [onSelectTask])

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    onSelectTask(null)
  }, [onSelectTask])

  return (
    <div className="w-full h-[400px] bg-gray-900 rounded-lg border border-gray-700">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        connectionLineType={ConnectionLineType.SmoothStep}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#374151" gap={16} />
        <Controls className="!bg-gray-800 !border-gray-700 !text-gray-300" />
        <MiniMap
          nodeColor={(node: any) => {
            const data = node.data as TaskNodeData
            switch (data.status) {
              case 'success': return '#22c55e'
              case 'running': return '#3b82f6'
              case 'failed': return '#ef4444'
              case 'degraded': return '#f59e0b'
              default: return '#6b7280'
            }
          }}
          maskColor="rgba(0, 0, 0, 0.7)"
          className="!bg-gray-800 !border-gray-700"
        />
      </ReactFlow>
    </div>
  )
}
