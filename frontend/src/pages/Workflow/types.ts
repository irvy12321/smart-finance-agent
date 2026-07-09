import { Node, Edge } from 'reactflow'

// Task status enum
export type TaskStatus = 'pending' | 'running' | 'success' | 'failed' | 'degraded' | 'skipped'

// Agent stage
export type AgentStage = 'planning' | 'executing' | 'reasoning' | 'reporting' | 'complete' | 'error'

// Workflow status
export type WorkflowStatus = 'idle' | 'connecting' | 'running' | 'completed' | 'error'

// DAG Subtask (from backend)
export interface DagSubtask {
  id: string
  tool: string
  desc: string
  priority: number
  depends_on: string[]
  tool_priority_score?: number
  task_reasoning?: string
  confidence?: number
}

// Route Decision (from backend)
export interface RouteDecision {
  complexity: number
  task_type: string
  plan_hint: string
  selected_model: string
  reasoning: string
  tool_scores: Record<string, number>
}

// Task Result
export interface TaskResult {
  task_id: string
  tool: string
  success: boolean
  data?: unknown
  error?: string
  duration_ms: number
  status: TaskStatus
}

// Workflow Event (SSE)
export interface WorkflowEvent {
  stage: string
  timestamp: number
  trace_id?: string

  // plan_ready
  subtasks?: DagSubtask[]
  route?: RouteDecision

  // task_start / task_complete
  task_id?: string
  tool?: string
  description?: string
  success?: boolean
  duration_ms?: number
  data?: unknown
  error?: string
  status?: TaskStatus

  // complete
  answer?: string
  report_markdown?: string
  total_duration_ms?: number
}

// Custom node data
export interface TaskNodeData {
  id: string
  label: string
  tool: string
  status: TaskStatus
  duration_ms: number
  description?: string
  confidence?: number
  error?: string
  data?: unknown
}

// Node style config
export interface NodeStyle {
  border: string
  backgroundColor: string
  icon: string
  color: string
  animation?: string
}

// Workflow state
export interface WorkflowState {
  taskId: string | null
  traceId: string | null
  query: string | null
  status: WorkflowStatus

  // DAG data (React Flow format)
  nodes: Node<TaskNodeData>[]
  edges: Edge[]

  // Execution data
  subtasks: DagSubtask[]
  route: RouteDecision | null
  taskResults: Map<string, TaskResult>
  events: WorkflowEvent[]

  // Metrics
  metrics: {
    totalTasks: number
    completedTasks: number
    failedTasks: number
    totalDuration: number
    avgTaskDuration: number
  }

  // Selection
  selectedTaskId: string | null
  selectedTask: TaskResult | null
}

// Workflow actions
export interface WorkflowActions {
  connect: (taskId: string, query?: string) => void
  disconnect: () => void
  selectTask: (taskId: string | null) => void
  retryConnection: () => void
}

// Node status styles
export const NODE_STYLES: Record<TaskStatus, NodeStyle> = {
  pending: {
    border: '2px dashed #6b7280',
    backgroundColor: '#1f2937',
    icon: '⏳',
    color: '#9ca3af',
  },
  running: {
    border: '2px solid #3b82f6',
    backgroundColor: '#1e3a5f',
    icon: '⚡',
    color: '#60a5fa',
    animation: 'pulse',
  },
  success: {
    border: '2px solid #22c55e',
    backgroundColor: '#14532d',
    icon: '✓',
    color: '#4ade80',
  },
  failed: {
    border: '2px solid #ef4444',
    backgroundColor: '#7f1d1d',
    icon: '✗',
    color: '#f87171',
  },
  degraded: {
    border: '2px solid #f59e0b',
    backgroundColor: '#78350f',
    icon: '⚠',
    color: '#fbbf24',
  },
  skipped: {
    border: '2px dashed #6b7280',
    backgroundColor: '#374151',
    icon: '⊘',
    color: '#9ca3af',
  },
}

// Tool display names
export const TOOL_DISPLAY_NAMES: Record<string, string> = {
  news_search: 'News Search',
  crawler: 'Web Crawler',
  rag_retrieve: 'RAG Retrieve',
  stock_price: 'Stock Price',
  stock_history: 'Stock History',
  financial_report: 'Financial Report',
  financial_analysis: 'Financial Analysis',
  news_summary: 'News Summary',
  llm_synthesize: 'LLM Synthesize',
}
