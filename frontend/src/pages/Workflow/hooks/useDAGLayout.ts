import { useMemo } from 'react'
import { Node, Edge } from 'reactflow'
import dagre from 'dagre'
import type { TaskNodeData } from '../types'

interface LayoutOptions {
  direction: 'TB' | 'LR'
  nodeWidth: number
  nodeHeight: number
  rankSep: number
  nodeSep: number
}

const defaultOptions: LayoutOptions = {
  direction: 'LR',
  nodeWidth: 180,
  nodeHeight: 80,
  rankSep: 120,
  nodeSep: 50,
}

export function useDAGLayout(
  nodes: Node<TaskNodeData>[],
  edges: Edge[],
  options: Partial<LayoutOptions> = {}
) {
  const layoutOptions = { ...defaultOptions, ...options }

  return useMemo(() => {
    if (nodes.length === 0) {
      return { nodes: [], edges }
    }

    const g = new dagre.graphlib.Graph()
    g.setDefaultEdgeLabel(() => ({}))
    g.setGraph({
      rankdir: layoutOptions.direction,
      ranksep: layoutOptions.rankSep,
      nodesep: layoutOptions.nodeSep,
    })

    nodes.forEach((node) => {
      g.setNode(node.id, {
        width: layoutOptions.nodeWidth,
        height: layoutOptions.nodeHeight,
      })
    })

    edges.forEach((edge) => {
      g.setEdge(edge.source, edge.target)
    })

    dagre.layout(g)

    const layoutedNodes = nodes.map((node) => {
      const nodeWithPosition = g.node(node.id)
      return {
        ...node,
        position: {
          x: nodeWithPosition.x - layoutOptions.nodeWidth / 2,
          y: nodeWithPosition.y - layoutOptions.nodeHeight / 2,
        },
      }
    })

    return { nodes: layoutedNodes, edges }
  }, [nodes, edges, layoutOptions])
}
