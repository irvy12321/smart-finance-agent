declare module 'reactflow' {
  import { ComponentType, CSSProperties, ReactNode } from 'react'

  export interface Node<T = any> {
    id: string
    type?: string
    position: { x: number; y: number }
    data: T
    style?: CSSProperties
    className?: string
    sourcePosition?: Position
    targetPosition?: Position
    hidden?: boolean
    selected?: boolean
    dragging?: boolean
    draggable?: boolean
    selectable?: boolean
    connectable?: boolean
    deletable?: boolean
    dragHandle?: string
    width?: number
    height?: number
    parentId?: string
    zIndex?: number
    extent?: 'parent' | [number, number, number, number]
    expandParent?: boolean
    ariaLabel?: string
    focusable?: boolean
  }

  export interface Edge<T = any> {
    id: string
    type?: string
    source: string
    target: string
    sourceHandle?: string | null
    targetHandle?: string | null
    label?: string | ReactNode
    labelStyle?: CSSProperties
    labelShowBg?: boolean
    labelBgStyle?: CSSProperties
    labelBgPadding?: [number, number]
    labelBgBorderRadius?: number
    style?: CSSProperties
    animated?: boolean
    hidden?: boolean
    selected?: boolean
    data?: T
    markerStart?: string
    markerEnd?: string
    zIndex?: number
    ariaLabel?: string
    focusable?: boolean
    reconnectable?: boolean
  }

  export enum Position {
    Left = 'left',
    Top = 'top',
    Right = 'right',
    Bottom = 'bottom',
  }

  export enum ConnectionLineType {
    Bezier = 'default',
    Straight = 'straight',
    Step = 'step',
    SmoothStep = 'smoothstep',
    SimpleBezier = 'simplebezier',
  }

  export interface Connection {
    source: string | null
    target: string | null
    sourceHandle: string | null
    targetHandle: string | null
  }

  export interface NodeProps<T = any> {
    id: string
    data: T
    selected: boolean
    isConnectable: boolean
    xPos: number
    yPos: number
    dragging: boolean
    sourcePosition?: Position
    targetPosition?: Position
  }

  export interface EdgeProps {
    id: string
    source: string
    target: string
    sourceX: number
    sourceY: number
    targetX: number
    targetY: number
    selected: boolean
    animated?: boolean
    style?: CSSProperties
    data?: any
    markerStart?: string
    markerEnd?: string
    sourcePosition?: Position
    targetPosition?: Position
  }

  export type OnNodesChange = (changes: NodeChange[]) => void
  export type OnEdgesChange = (changes: EdgeChange[]) => void
  export type OnConnect = (connection: Connection) => void

  export interface NodeChange {
    id: string
    type: string
    [key: string]: any
  }

  export interface EdgeChange {
    id: string
    type: string
    [key: string]: any
  }

  export interface ReactFlowProps {
    nodes: Node[]
    edges: Edge[]
    onNodesChange?: OnNodesChange
    onEdgesChange?: OnEdgesChange
    onConnect?: OnConnect
    onNodeClick?: (event: React.MouseEvent, node: Node) => void
    onEdgeClick?: (event: React.MouseEvent, edge: Edge) => void
    onPaneClick?: (event: React.MouseEvent) => void
    nodeTypes?: Record<string, ComponentType<any>>
    edgeTypes?: Record<string, ComponentType<any>>
    connectionLineType?: ConnectionLineType
    fitView?: boolean
    fitViewOptions?: { padding?: number }
    minZoom?: number
    maxZoom?: number
    defaultZoom?: number
    defaultPosition?: [number, number]
    proOptions?: { hideAttribution?: boolean }
    children?: ReactNode
    style?: CSSProperties
    className?: string
  }

  export function useNodesState(initialNodes: Node[]): [Node[], (nodes: Node[]) => void, (changes: NodeChange[]) => void]
  export function useEdgesState(initialEdges: Edge[]): [Edge[], (edges: Edge[]) => void, (changes: EdgeChange[]) => void]

  export function addEdge(edgeParams: Edge | Connection, edges: Edge[]): Edge[]

  export const Handle: ComponentType<any>
  export const Background: ComponentType<any>
  export const Controls: ComponentType<any>
  export const MiniMap: ComponentType<any>

  const ReactFlow: ComponentType<ReactFlowProps>
  export default ReactFlow
}

declare module 'dagre' {
  export class graphlib {
    static Graph: new () => Graph
  }

  export interface Graph {
    setDefaultEdgeLabel(callback: () => any): void
    setGraph(config: any): void
    setNode(id: string, config: any): void
    setEdge(source: string, target: string, config?: any): void
    node(id: string): any
    edge(source: string, target: string): any
    nodes(): string[]
    edges(): Array<{ v: string; w: string }>
  }

  export function layout(graph: Graph): void
}
