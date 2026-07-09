import axios, { AxiosError, AxiosRequestConfig } from 'axios'
import i18n from '../i18n'
import type {
  UserCreate,
  UserLogin,
  Token,
  RefreshTokenRequest,
  LogoutRequest,
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

// Token refresh state
let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token!)
    }
  })
  failedQueue = []
}

interface ApiErrorPayload {
  detail?: string
  message?: string
}

type ApiErrorWithUserMessage = AxiosError<ApiErrorPayload> & {
  userMessage?: string
}

interface RAGDocument {
  id: string
  filename: string
  file_type: string
  file_size: number
  chunk_count: number
  status: string
  created_at: string
  updated_at: string
  metadata: Record<string, unknown>
}

interface RAGSearchResult {
  text: string
  score: number
  metadata: Record<string, unknown>
}

// Request interceptor - add auth token and language
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // Add language header for i18n
    config.headers['Accept-Language'] = i18n.language || 'en'
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for error handling with automatic token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorPayload>) => {
    // Ignore cancelled requests (AbortController)
    if (error.code === 'ERR_CANCELED' || error.name === 'CanceledError') {
      return Promise.reject(error)
    }

    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }

    // Handle 401 - attempt token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      const currentPath = window.location.pathname
      const isAuthPage = currentPath.includes('/login') || currentPath.includes('/register')

      // Don't attempt refresh on auth pages or if already retrying
      if (isAuthPage) {
        return Promise.reject(error)
      }

      // If already refreshing, queue this request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${token}`
          }
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = localStorage.getItem('auth_refresh_token')

      if (!refreshToken) {
        // No refresh token available, redirect to login
        isRefreshing = false
        processQueue(error, null)
        localStorage.removeItem('auth_token')
        localStorage.removeItem('auth_refresh_token')
        localStorage.removeItem('auth_user')
        window.location.href = '/login'
        return Promise.reject(error)
      }

      try {
        // Call refresh endpoint directly (not through interceptor)
        const response = await axios.post<Token>(
          '/api/auth/refresh',
          { refresh_token: refreshToken } as RefreshTokenRequest,
          {
            headers: { 'Content-Type': 'application/json' },
            timeout: 10000,
          }
        )

        const { access_token, refresh_token: newRefreshToken } = response.data

        // Update stored tokens
        localStorage.setItem('auth_token', access_token)
        localStorage.setItem('auth_refresh_token', newRefreshToken)

        // Update default headers
        api.defaults.headers.common.Authorization = `Bearer ${access_token}`

        // Process queued requests
        processQueue(null, access_token)

        // Retry original request
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`
        }
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh failed, clear auth and redirect
        processQueue(refreshError, null)
        localStorage.removeItem('auth_token')
        localStorage.removeItem('auth_refresh_token')
        localStorage.removeItem('auth_user')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // Handle other errors
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An unexpected error occurred'

    console.error('API Error:', {
      status: error.response?.status,
      url: error.config?.url,
      message,
    })

    const apiError = error as ApiErrorWithUserMessage
    if (error.response?.status === 404) {
      apiError.userMessage = 'Resource not found.'
    } else if (error.response?.status === 500) {
      apiError.userMessage = `Server error: ${message}`
    } else if (error.code === 'ECONNABORTED') {
      apiError.userMessage = 'Request timed out. Please try again.'
    } else if (!error.response) {
      apiError.userMessage = 'Cannot connect to server. Please check if backend is running.'
    } else {
      apiError.userMessage = message
    }

    return Promise.reject(error)
  }
)

// Task API
export const taskApi = {
  create: async (query: string, priority: number = 1): Promise<TaskCreateResponse> => {
    const response = await api.post<TaskCreateResponse>('/task/create', { query, priority })
    return response.data
  },

  getStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    const response = await api.get<TaskStatusResponse>(`/task/${taskId}/status`)
    return response.data
  },

  run: async (taskId: string): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>(`/task/${taskId}/run`)
    return response.data
  },

  getResult: async (taskId: string): Promise<TaskResultResponse> => {
    const response = await api.get<TaskResultResponse>(`/task/${taskId}/result`)
    return response.data
  },

  list: async (): Promise<TaskListResponse> => {
    const response = await api.get<TaskListResponse>('/task/list')
    return response.data
  },
}

// Report API
export const reportApi = {
  get: async (taskId: string): Promise<ReportResponse> => {
    const response = await api.get<ReportResponse>(`/report/${taskId}`)
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
  getStatus: async (): Promise<SystemStatusResponse> => {
    const response = await api.get<SystemStatusResponse>('/system/status')
    return response.data
  },

  getMetrics: async (): Promise<SystemMetricsResponse> => {
    const response = await api.get<SystemMetricsResponse>('/system/metrics')
    return response.data
  },

  getAgentStatus: async (): Promise<AgentStatusResponse> => {
    const response = await api.get<AgentStatusResponse>('/system/agents')
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

  getStockHistory: async (symbol: string, period?: string): Promise<StockHistoryResponse> => {
    const response = await api.post<StockHistoryResponse>('/tools/stock/history', { symbol, period })
    return response.data
  },

  getFinancialReport: async (symbol: string): Promise<FinancialReportResponse> => {
    const response = await api.post<FinancialReportResponse>('/tools/financial/report', { symbol })
    return response.data
  },

  getFinancialAnalysis: async (symbol: string): Promise<FinancialAnalysisResponse> => {
    const response = await api.post<FinancialAnalysisResponse>('/tools/financial/analysis', { symbol })
    return response.data
  },

  searchNews: async (query: string, maxResults?: number): Promise<NewsResponse> => {
    const response = await api.post<NewsResponse>('/tools/news/search', { query, max_results: maxResults })
    return response.data
  },

  getNewsAnalysis: async (query: string): Promise<NewsAnalysisResponse> => {
    const response = await api.post<NewsAnalysisResponse>('/tools/news/analysis', { query })
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
    const response = await api.post<ChatResponse>(`/chat/conversations/${conversationId}/messages`, {
      message,
    })
    return response.data
  },

  getHistory: async (conversationId: string): Promise<ConversationHistoryResponse> => {
    const response = await api.get<ConversationHistoryResponse>(`/chat/conversations/${conversationId}`)
    return response.data
  },

  listConversations: async (): Promise<ConversationListResponse> => {
    const response = await api.get<ConversationListResponse>('/chat/conversations')
    return response.data
  },

  deleteConversation: async (conversationId: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/chat/conversations/${conversationId}`)
    return response.data
  },
}

// RAG API
export const ragApi = {
  listDocuments: async (): Promise<{ documents: RAGDocument[] }> => {
    const response = await api.get<{ documents: RAGDocument[] }>('/rag/documents')
    return response.data
  },

  uploadDocument: async (file: File): Promise<{ message: string; document_id: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post<{ message: string; document_id: string }>('/rag/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  getDocument: async (docId: string): Promise<RAGDocument> => {
    const response = await api.get<RAGDocument>(`/rag/documents/${docId}`)
    return response.data
  },

  deleteDocument: async (docId: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/rag/documents/${docId}`)
    return response.data
  },

  search: async (query: string, topK?: number): Promise<{ results: RAGSearchResult[] }> => {
    const response = await api.post<{ results: RAGSearchResult[] }>('/rag/search', { query, top_k: topK })
    return response.data
  },

  getStats: async (): Promise<{ total_documents: number; total_chunks: number }> => {
    const response = await api.get<{ total_documents: number; total_chunks: number }>('/rag/stats')
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

  refreshToken: async (data: RefreshTokenRequest): Promise<Token> => {
    const response = await axios.post<Token>(
      '/api/auth/refresh',
      data,
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: 10000,
      }
    )
    return response.data
  },

  logout: async (data: LogoutRequest): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>('/auth/logout', data)
    return response.data
  },
}

export default api
