// Auth API Types
export interface UserCreate {
  username: string
  email: string
  password: string
}

export interface UserLogin {
  username: string
  password: string
}

export interface UserResponse {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
  created_at: string
}

export interface Token {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserResponse
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface LogoutRequest {
  refresh_token: string
}

// Task API Types
export interface TaskCreateResponse {
  task_id: string
  status: string
  message: string
}

export interface TaskStatusResponse {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  current_stage: string
  message: string
}

export interface TaskResultResponse {
  task_id: string
  status: string
  query: string
  answer: string
  report_markdown: string
  report_title: string
  summary: string
  key_findings: string[]
  risk_factors: RiskFactor[]
  market_trends: string[]
  recommendations: string[]
  confidence: number
  chart_paths: string[]
  chart_specs: ChartSpec[]
  sources: Source[]
  dag_subtasks: DagSubtask[]
  task_states: Record<string, TaskState>
  elapsed: number
  total_tasks: number
  success_tasks: number
  failed_tasks: number
  plan_reasoning: string
  reasoning_insights: string[]
  events: PipelineEvent[]
  updated_at: string
}

export interface TaskListItem {
  task_id: string
  query: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  created_at: string
  updated_at: string
}

export interface TaskListResponse {
  tasks: TaskListItem[]
}

// Report API Types
export interface ReportResponse {
  task_id: string
  report_markdown: string
  report_title: string
  summary: string
  key_findings: string[]
  risk_factors: RiskFactor[]
  market_trends: string[]
  recommendations: string[]
  confidence: number
  chart_paths: string[]
  chart_specs: ChartSpec[]
  sources: Source[]
  dag_subtasks: DagSubtask[]
  task_states: Record<string, TaskState>
  elapsed: number
  total_tasks: number
  success_tasks: number
  failed_tasks: number
  plan_reasoning: string
  reasoning_insights: string[]
  updated_at: string
  answer?: string
}

export interface ReportSummaryResponse {
  task_id: string
  report_title: string
  summary: string
  key_findings: string[]
  confidence: number
  total_tasks: number
  success_tasks: number
  failed_tasks: number
}

export interface ReportMarkdownResponse {
  task_id: string
  markdown: string
  title: string
}

export interface ReportChartsResponse {
  task_id: string
  chart_paths: string[]
  chart_specs: ChartSpec[]
}

export interface ReportAnalysisResponse {
  task_id: string
  key_findings: string[]
  risk_factors: RiskFactor[]
  market_trends: string[]
  recommendations: string[]
  confidence: number
  reasoning_insights: string[]
}

export interface ReportSourcesResponse {
  task_id: string
  sources: Source[]
  dag_subtasks: DagSubtask[]
  task_states: Record<string, TaskState>
}

export interface ReportProcessResponse {
  task_id: string
  plan_reasoning: string
  dag_subtasks: DagSubtask[]
  task_states: Record<string, TaskState>
  elapsed: number
  total_tasks: number
  success_tasks: number
  failed_tasks: number
}

// System API Types
export interface SystemStatusResponse {
  status: string
  version: string
  uptime: number
  total_requests: number
  success_rate: number
  avg_latency_ms: number
  timestamp: string
}

export interface SystemMetricsResponse {
  total_requests: number
  successful_requests: number
  failed_requests: number
  success_rate: number
  avg_latency_ms: number
  total_tasks: number
  completed_tasks: number
  pending_tasks: number
  running_tasks: number
  failed_tasks: number
  timestamp: string
}

export interface AgentStatus {
  status: string
  total_calls: number
  avg_latency_ms: number
  success_rate: number
  active_tasks?: number
  total_requests?: number
  uptime?: number
}

export interface AgentStatusResponse {
  planner: AgentStatus
  executor: AgentStatus
  reasoner: AgentStatus
  report_agent: AgentStatus
  orchestrator: AgentStatus
}

export interface SystemConfigResponse {
  model: string
  embedding: string
  features: Record<string, boolean>
  version: string
}

export interface HealthResponse {
  status: string
  timestamp: string
  uptime: number
}

export interface VersionResponse {
  version: string
  build: string
  api_version: string
}

// Tools API Types
export interface ToolInfo {
  name: string
  description: string
}

export interface ToolListResponse {
  tools: ToolInfo[]
  total: number
}

export interface StockPriceResponse {
  symbol: string
  name: string
  price: number
  change: number
  change_percent: number
  volume: number
  market_cap: number
  pe_ratio: number
  high_52w: number
  low_52w: number
  timestamp: string
  source: string
}

export interface StockHistoryResponse {
  symbol: string
  period: string
  history: HistoryPoint[]
  source: string
}

export interface HistoryPoint {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface FinancialReportResponse {
  symbol: string
  name: string
  sector: string
  industry: string
  financials: Record<string, unknown>
  quarterly: Record<string, unknown>
  timestamp: string
  source: string
}

export interface FinancialAnalysisResponse {
  symbol: string
  analysis_type: string
  analysis: Record<string, unknown>
  timestamp: string
}

export interface NewsResult {
  title: string
  url: string
  snippet: string
  source: string
  date: string
}

export interface NewsResponse {
  query: string
  results: NewsResult[]
  summary: string
  total_results: number
  timestamp: string
  source: string
}

export interface NewsAnalysisResponse {
  query: string
  period: string
  analysis: Record<string, unknown>
  timestamp: string
}

// Chat API Types
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

export interface ChatResponse {
  conversation_id: string
  message: ChatMessage
  response: string
  sources: Source[]
  confidence: number
  timestamp: string
}

export interface ConversationCreateResponse {
  conversation_id: string
  created_at: string
  message: string
}

export interface ConversationHistoryResponse {
  conversation_id: string
  messages: ChatMessage[]
  total_messages: number
}

export interface ConversationListItem {
  conversation_id: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface ConversationListResponse {
  conversations: ConversationListItem[]
  total: number
}

// Shared Types
export interface RiskFactor {
  factor: string
  severity: 'high' | 'medium' | 'low'
  description: string
}

export interface ChartSpec {
  chart_type: 'bar' | 'line' | 'pie' | 'scatter'
  title: string
  x_label: string
  y_label: string
  data: ChartDataPoint[]
  description?: string
}

export interface ChartDataPoint {
  label: string
  value: number
}

export interface Source {
  tool: string
  task_id: string
  duration_ms: number
}

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

export interface TaskState {
  tool: string
  success: boolean
  duration_ms: number
  status: 'running' | 'success' | 'failed' | 'skipped' | 'degraded'
}

export interface PipelineEvent {
  stage: string
  message?: string
  task_id?: string
  tool?: string
  success?: boolean
  duration_ms?: number
  status?: string
  progress?: number
  current_stage?: string
  subtasks?: DagSubtask[]
  route?: RouteDecision
  confidence?: number
  insights?: string[]
  charts_count?: number
  answer?: string
  report_markdown?: string
  report_title?: string
  chart_paths?: string[]
  chart_specs?: ChartSpec[]
  total_duration_ms?: number
  trace_id?: string
  task_states?: Record<string, TaskState>
}

export interface RouteDecision {
  complexity: number
  task_type: string
  plan_hint: string
  selected_model: string
  reasoning: string
  tool_scores: Record<string, number>
}

// Error Types
export interface ApiError {
  response?: {
    status: number
    data?: {
      detail?: string
      message?: string
    }
  }
  message: string
  code?: string
  userMessage?: string
}
