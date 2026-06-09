import axios from 'axios'
import type {
  UserCreate,
  UserLogin,
  Token,
  UserResponse,
  TaskCreateResponse,
  TaskStatusResponse,
  TaskResultResponse,
  TaskListResponse,
  ReportResponse,
  ReportSummaryResponse,
  ReportMarkdownResponse,
  ReportChartsResponse,
  ReportAnalysisResponse,
  ReportSourcesResponse,
  ReportProcessResponse,
  SystemStatusResponse,
  SystemMetricsResponse,
  AgentStatusResponse,
  SystemConfigResponse,
  HealthResponse,
  VersionResponse,
  ToolListResponse,
  StockPriceResponse,
  StockHistoryResponse,
  FinancialReportResponse,
  FinancialAnalysisResponse,
  NewsResponse,
  NewsAnalysisResponse,
  ChatResponse,
  ConversationCreateResponse,
  ConversationHistoryResponse,
  ConversationListResponse,
} from '../types/api'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 忽略被取消的请求（AbortController）
    if (error.code === 'ERR_CANCELED' || error.name === 'CanceledError') {
      return Promise.reject(error)
    }

    const message = error.response?.data?.detail 
      || error.response?.data?.message 
      || error.message 
      || 'An unexpected error occurred'
    
    console.error('API Error:', {
      status: error.response?.status,
      url: error.config?.url,
      message,
    })

    // Handle 401 - redirect to login
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_user')
      // Only redirect if not already on login/register page
      if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
        window.location.href = '/login'
      }
      error.userMessage = 'Session expired. Please login again.'
    } else if (error.response?.status === 404) {
      error.userMessage = 'Resource not found.'
    } else if (error.response?.status === 500) {
      error.userMessage = `Server error: ${message}`
    } else if (error.code === 'ECONNABORTED') {
      error.userMessage = 'Request timed out. Please try again.'
    } else if (!error.response) {
      error.userMessage = 'Cannot connect to server. Please check if backend is running.'
    } else {
      error.userMessage = message
    }

    return Promise.reject(error)
  }
)

type SignalConfig = { signal?: AbortSignal }

// Task API
export const taskApi = {
  create: async (query: string, priority: number = 1): Promise<TaskCreateResponse> => {
    const response = await api.post<TaskCreateResponse>('/task/create', { query, priority })
    return response.data
  },

  getStatus: async (taskId: string, config?: SignalConfig): Promise<TaskStatusResponse> => {
    const response = await api.get<TaskStatusResponse>(`/task/${taskId}/status`, { ...config, timeout: 10000 })
    return response.data
  },

  run: async (taskId: string): Promise<{ message: string; task_id: string }> => {
    const response = await api.post(`/task/${taskId}/run`)
    return response.data
  },

  getResult: async (taskId: string): Promise<TaskResultResponse> => {
    const response = await api.get<TaskResultResponse>(`/task/${taskId}/result`)
    return response.data
  },

  list: async (config?: SignalConfig): Promise<TaskListResponse> => {
    const response = await api.get<TaskListResponse>('/task/list', config)
    return response.data
  },
}

// Report API
export const reportApi = {
  get: async (taskId: string, config?: SignalConfig): Promise<ReportResponse> => {
    const response = await api.get<ReportResponse>(`/report/${taskId}`, config)
    return response.data
  },

  getSummary: async (taskId: string): Promise<ReportSummaryResponse> => {
    const response = await api.get<ReportSummaryResponse>(`/report/${taskId}/summary`)
    return response.data
  },

  getMarkdown: async (taskId: string): Promise<ReportMarkdownResponse> => {
    const response = await api.get<ReportMarkdownResponse>(`/report/${taskId}/markdown`)
    return response.data
  },

  getCharts: async (taskId: string): Promise<ReportChartsResponse> => {
    const response = await api.get<ReportChartsResponse>(`/report/${taskId}/charts`)
    return response.data
  },

  getAnalysis: async (taskId: string): Promise<ReportAnalysisResponse> => {
    const response = await api.get<ReportAnalysisResponse>(`/report/${taskId}/analysis`)
    return response.data
  },

  getSources: async (taskId: string): Promise<ReportSourcesResponse> => {
    const response = await api.get<ReportSourcesResponse>(`/report/${taskId}/sources`)
    return response.data
  },

  getProcess: async (taskId: string): Promise<ReportProcessResponse> => {
    const response = await api.get<ReportProcessResponse>(`/report/${taskId}/process`)
    return response.data
  },
}

// System API
export const systemApi = {
  getStatus: async (config?: SignalConfig): Promise<SystemStatusResponse> => {
    const response = await api.get<SystemStatusResponse>('/system/status', config)
    return response.data
  },

  getMetrics: async (config?: SignalConfig): Promise<SystemMetricsResponse> => {
    const response = await api.get<SystemMetricsResponse>('/system/metrics', config)
    return response.data
  },

  getAgentStatus: async (config?: SignalConfig): Promise<AgentStatusResponse> => {
    const response = await api.get<AgentStatusResponse>('/system/agents', config)
    return response.data
  },

  getConfig: async (): Promise<SystemConfigResponse> => {
    const response = await api.get<SystemConfigResponse>('/system/config')
    return response.data
  },

  getHealth: async (): Promise<HealthResponse> => {
    const response = await api.get<HealthResponse>('/system/health')
    return response.data
  },

  getVersion: async (): Promise<VersionResponse> => {
    const response = await api.get<VersionResponse>('/system/version')
    return response.data
  },
}

// Tools API
export const toolsApi = {
  list: async (): Promise<ToolListResponse> => {
    const response = await api.get<ToolListResponse>('/tools/list')
    return response.data
  },

  getStockPrice: async (symbol: string): Promise<StockPriceResponse> => {
    const response = await api.post<StockPriceResponse>('/tools/stock/price', { symbol })
    return response.data
  },

  getStockHistory: async (symbol: string, period: string = '1m'): Promise<StockHistoryResponse> => {
    const response = await api.post<StockHistoryResponse>('/tools/stock/history', { symbol, period })
    return response.data
  },

  getFinancialReport: async (symbol: string, reportType: string = 'summary'): Promise<FinancialReportResponse> => {
    const response = await api.post<FinancialReportResponse>('/tools/financial/report', { symbol, report_type: reportType })
    return response.data
  },

  getFinancialAnalysis: async (symbol: string, analysisType: string = 'comprehensive'): Promise<FinancialAnalysisResponse> => {
    const response = await api.post<FinancialAnalysisResponse>('/tools/financial/analysis', { symbol, analysis_type: analysisType })
    return response.data
  },

  searchNews: async (query: string, maxResults: number = 5): Promise<NewsResponse> => {
    const response = await api.post<NewsResponse>('/tools/news/search', { query, max_results: maxResults })
    return response.data
  },

  getNewsAnalysis: async (query: string, period: string = '7d'): Promise<NewsAnalysisResponse> => {
    const response = await api.post<NewsAnalysisResponse>('/tools/news/analysis', { query, period })
    return response.data
  },
}

// Chat API
export const chatApi = {
  createConversation: async (): Promise<ConversationCreateResponse> => {
    const response = await api.post<ConversationCreateResponse>('/chat/conversations')
    return response.data
  },

  sendMessage: async (conversationId: string, message: string): Promise<ChatResponse> => {
    const response = await api.post<ChatResponse>(`/chat/conversations/${conversationId}/messages`, { message })
    return response.data
  },

  getHistory: async (conversationId: string): Promise<ConversationHistoryResponse> => {
    const response = await api.get<ConversationHistoryResponse>(`/chat/conversations/${conversationId}`)
    return response.data
  },

  listConversations: async (config?: SignalConfig): Promise<ConversationListResponse> => {
    const response = await api.get<ConversationListResponse>('/chat/conversations', config)
    return response.data
  },

  deleteConversation: async (conversationId: string): Promise<{ message: string }> => {
    const response = await api.delete(`/chat/conversations/${conversationId}`)
    return response.data
  },
}

// RAG API
export interface DocumentInfo {
  id: string
  filename: string
  file_type: string
  file_size: number
  chunk_count: number
  status: 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  metadata: Record<string, any>
}

export interface DocumentListResponse {
  documents: DocumentInfo[]
  total: number
}

export interface DocumentUploadResponse {
  document_id: string
  filename: string
  status: string
  message: string
}

export interface RAGSearchResult {
  text: string
  score: number
  metadata: Record<string, any>
}

export interface RAGSearchResponse {
  query: string
  results: RAGSearchResult[]
  total: number
}

export interface RAGStatsResponse {
  total_documents: number
  total_chunks: number
  vector_store_size: number
  embedding_mode: string
}

export const ragApi = {
  listDocuments: async (): Promise<DocumentListResponse> => {
    const response = await api.get<DocumentListResponse>('/rag/documents')
    return response.data
  },

  uploadDocument: async (file: File, metadata?: Record<string, any>): Promise<DocumentUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata))
    }
    const response = await api.post<DocumentUploadResponse>('/rag/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    })
    return response.data
  },

  getDocument: async (docId: string): Promise<DocumentInfo> => {
    const response = await api.get<DocumentInfo>(`/rag/documents/${docId}`)
    return response.data
  },

  deleteDocument: async (docId: string): Promise<{ document_id: string; message: string }> => {
    const response = await api.delete(`/rag/documents/${docId}`)
    return response.data
  },

  search: async (query: string, topK: number = 5): Promise<RAGSearchResponse> => {
    const response = await api.post<RAGSearchResponse>('/rag/search', { query, top_k: topK })
    return response.data
  },

  getStats: async (): Promise<RAGStatsResponse> => {
    const response = await api.get<RAGStatsResponse>('/rag/stats')
    return response.data
  },

  reindex: async (): Promise<{ message: string }> => {
    const response = await api.post('/rag/reindex')
    return response.data
  },
}

// Auth API
export const authApi = {
  register: async (data: UserCreate): Promise<Token> => {
    const response = await api.post<Token>('/auth/register', data)
    return response.data
  },

  login: async (data: UserLogin): Promise<Token> => {
    const response = await api.post<Token>('/auth/login', data)
    return response.data
  },

  getMe: async (): Promise<UserResponse> => {
    const response = await api.get<UserResponse>('/auth/me')
    return response.data
  },

  refreshToken: async (): Promise<Token> => {
    const response = await api.post<Token>('/auth/refresh')
    return response.data
  },
}

export default api
