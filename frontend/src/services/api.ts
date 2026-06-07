import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail 
      || error.response?.data?.message 
      || error.message 
      || 'An unexpected error occurred'
    
    console.error('API Error:', {
      status: error.response?.status,
      url: error.config?.url,
      message,
    })

    // Enhance error with user-friendly message
    if (error.response?.status === 401) {
      error.userMessage = 'Authentication failed. Please check API key configuration.'
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

// Task API
export const taskApi = {
  create: async (query: string, priority: number = 1) => {
    const response = await api.post('/task/create', { query, priority })
    return response.data
  },

  getStatus: async (taskId: string) => {
    const response = await api.get(`/task/${taskId}/status`, { timeout: 10000 })
    return response.data
  },

  run: async (taskId: string) => {
    const response = await api.post(`/task/${taskId}/run`)
    return response.data
  },

  getResult: async (taskId: string) => {
    const response = await api.get(`/task/${taskId}/result`)
    return response.data
  },

  list: async () => {
    const response = await api.get('/task/list')
    return response.data
  },
}

// Report API
export const reportApi = {
  get: async (taskId: string) => {
    const response = await api.get(`/report/${taskId}`)
    return response.data
  },

  getSummary: async (taskId: string) => {
    const response = await api.get(`/report/${taskId}/summary`)
    return response.data
  },

  getMarkdown: async (taskId: string) => {
    const response = await api.get(`/report/${taskId}/markdown`)
    return response.data
  },

  getCharts: async (taskId: string) => {
    const response = await api.get(`/report/${taskId}/charts`)
    return response.data
  },

  getAnalysis: async (taskId: string) => {
    const response = await api.get(`/report/${taskId}/analysis`)
    return response.data
  },

  getSources: async (taskId: string) => {
    const response = await api.get(`/report/${taskId}/sources`)
    return response.data
  },

  getProcess: async (taskId: string) => {
    const response = await api.get(`/report/${taskId}/process`)
    return response.data
  },
}

// System API
export const systemApi = {
  getStatus: async () => {
    const response = await api.get('/system/status')
    return response.data
  },

  getMetrics: async () => {
    const response = await api.get('/system/metrics')
    return response.data
  },

  getAgentStatus: async () => {
    const response = await api.get('/system/agents')
    return response.data
  },

  getConfig: async () => {
    const response = await api.get('/system/config')
    return response.data
  },

  getHealth: async () => {
    const response = await api.get('/system/health')
    return response.data
  },

  getVersion: async () => {
    const response = await api.get('/system/version')
    return response.data
  },
}

// Tools API
export const toolsApi = {
  list: async () => {
    const response = await api.get('/tools/list')
    return response.data
  },

  getStockPrice: async (symbol: string) => {
    const response = await api.post('/tools/stock/price', { symbol })
    return response.data
  },

  getStockHistory: async (symbol: string, period: string = '1m') => {
    const response = await api.post('/tools/stock/history', { symbol, period })
    return response.data
  },

  getFinancialReport: async (symbol: string, reportType: string = 'summary') => {
    const response = await api.post('/tools/financial/report', { symbol, report_type: reportType })
    return response.data
  },

  getFinancialAnalysis: async (symbol: string, analysisType: string = 'comprehensive') => {
    const response = await api.post('/tools/financial/analysis', { symbol, analysis_type: analysisType })
    return response.data
  },

  searchNews: async (query: string, maxResults: number = 5) => {
    const response = await api.post('/tools/news/search', { query, max_results: maxResults })
    return response.data
  },

  getNewsAnalysis: async (query: string, period: string = '7d') => {
    const response = await api.post('/tools/news/analysis', { query, period })
    return response.data
  },
}

// Chat API
export const chatApi = {
  createConversation: async () => {
    const response = await api.post('/chat/conversations')
    return response.data
  },

  sendMessage: async (conversationId: string, message: string) => {
    const response = await api.post(`/chat/conversations/${conversationId}/messages`, { message })
    return response.data
  },

  getHistory: async (conversationId: string) => {
    const response = await api.get(`/chat/conversations/${conversationId}`)
    return response.data
  },

  listConversations: async () => {
    const response = await api.get('/chat/conversations')
    return response.data
  },

  deleteConversation: async (conversationId: string) => {
    const response = await api.delete(`/chat/conversations/${conversationId}`)
    return response.data
  },
}

export default api