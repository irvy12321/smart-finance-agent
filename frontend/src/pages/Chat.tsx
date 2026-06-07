import { useState, useEffect, useRef } from 'react'
import { 
  Send, 
  Bot, 
  User, 
  Loader2, 
  MessageSquare,
  Plus,
  Trash2,
  TrendingUp,
  DollarSign,
  Newspaper,
  BarChart3
} from 'lucide-react'
import { chatApi } from '../services/api'

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

interface Conversation {
  conversation_id: string
  created_at: string
  updated_at: string
  message_count: number
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchConversations()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const fetchConversations = async () => {
    try {
      const data = await chatApi.listConversations()
      setConversations(data.conversations || [])
    } catch (error) {
      console.error('Failed to fetch conversations:', error)
    }
  }

  const createNewConversation = async () => {
    try {
      const data = await chatApi.createConversation()
      setConversationId(data.conversation_id)
      setMessages([])
      fetchConversations()
    } catch (error) {
      console.error('Failed to create conversation:', error)
    }
  }

  const loadConversation = async (convId: string) => {
    try {
      const data = await chatApi.getHistory(convId)
      setConversationId(convId)
      setMessages(data.messages || [])
    } catch (error) {
      console.error('Failed to load conversation:', error)
    }
  }

  const deleteConversation = async (convId: string) => {
    try {
      await chatApi.deleteConversation(convId)
      if (conversationId === convId) {
        setConversationId(null)
        setMessages([])
      }
      fetchConversations()
    } catch (error) {
      console.error('Failed to delete conversation:', error)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      let convId = conversationId
      if (!convId) {
        const convData = await chatApi.createConversation()
        convId = convData.conversation_id
        setConversationId(convId)
        fetchConversations()
      }

      const data = await chatApi.sendMessage(convId!, input)
      
      const assistantMessage: Message = {
        role: 'assistant',
        content: data.response,
        timestamp: data.timestamp,
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Failed to send message:', error)
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const quickActions = [
    {
      icon: TrendingUp,
      label: 'Stock Price',
      query: 'What is the current stock price of AAPL?',
      color: 'text-green-500',
      bg: 'bg-green-500/10',
    },
    {
      icon: BarChart3,
      label: 'Financial Analysis',
      query: 'Provide a financial analysis for Tesla',
      color: 'text-blue-500',
      bg: 'bg-blue-500/10',
    },
    {
      icon: Newspaper,
      label: 'Latest News',
      query: 'What are the latest news about Apple?',
      color: 'text-purple-500',
      bg: 'bg-purple-500/10',
    },
    {
      icon: DollarSign,
      label: 'Market Trends',
      query: 'Analyze the current market trends for tech stocks',
      color: 'text-yellow-500',
      bg: 'bg-yellow-500/10',
    },
  ]

  const handleQuickAction = (query: string) => {
    setInput(query)
  }

  return (
    <div className="flex h-full">
      {/* Conversations Sidebar */}
      <div className="w-64 bg-dark-sub border-r border-dark-border flex flex-col">
        <div className="p-4 border-b border-dark-border">
          <button
            onClick={createNewConversation}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-auto p-2">
          {conversations.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="w-8 h-8 text-primary-400 mx-auto mb-2" />
              <p className="text-xs text-primary-400">No conversations yet</p>
            </div>
          ) : (
            <div className="space-y-1">
              {conversations.map((conv) => (
                <div
                  key={conv.conversation_id}
                  className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                    conversationId === conv.conversation_id
                      ? 'bg-primary-500/10 text-primary-500'
                      : 'text-primary-300 hover:bg-dark-card'
                  }`}
                  onClick={() => loadConversation(conv.conversation_id)}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      Chat {conv.conversation_id.slice(0, 6)}
                    </p>
                    <p className="text-xs text-primary-400 mt-1">
                      {conv.message_count} messages
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteConversation(conv.conversation_id)
                    }}
                    className="p-1 text-primary-400 hover:text-red-500 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-dark-border">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-primary-50">AI Financial Assistant</h1>
              <p className="text-sm text-primary-400 mt-1">
                Ask me about stocks, financial reports, news, and market analysis
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="status-dot status-dot-success" />
              <span className="text-xs text-primary-300">Connected</span>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.length === 0 && !loading && (
              <div className="flex flex-col items-center justify-center h-full py-12">
                <div className="text-center max-w-2xl">
                  <div className="w-16 h-16 bg-primary-500/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <Bot className="w-8 h-8 text-primary-500" />
                  </div>
                  <h2 className="text-2xl font-bold text-primary-50 mb-4">
                    Welcome to Smart Finance Agent
                  </h2>
                  <p className="text-primary-400 mb-8">
                    I can help you with stock prices, financial analysis, news research, and comprehensive market analysis. 
                    Try one of the quick actions below or ask me anything!
                  </p>

                  {/* Quick Actions */}
                  <div className="grid grid-cols-2 gap-4">
                    {quickActions.map((action, index) => (
                      <button
                        key={index}
                        onClick={() => handleQuickAction(action.query)}
                        className="flex items-center gap-3 p-4 bg-dark-card rounded-xl border border-dark-border hover:border-primary-500/30 transition-all text-left"
                      >
                        <div className={`w-10 h-10 ${action.bg} rounded-lg flex items-center justify-center`}>
                          <action.icon className={`w-5 h-5 ${action.color}`} />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-primary-200">{action.label}</p>
                          <p className="text-xs text-primary-400 mt-1 line-clamp-1">{action.query}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex gap-4 ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {message.role === 'assistant' && (
                  <div className="w-8 h-8 bg-primary-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-primary-500" />
                  </div>
                )}
                
                <div
                  className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-primary-500 text-white'
                      : 'bg-dark-card border border-dark-border'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  <p className={`text-xs mt-2 ${
                    message.role === 'user' ? 'text-white/60' : 'text-primary-400'
                  }`}>
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </p>
                </div>

                {message.role === 'user' && (
                  <div className="w-8 h-8 bg-blue-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4 text-blue-500" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-4 justify-start">
                <div className="w-8 h-8 bg-primary-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-primary-500" />
                </div>
                <div className="bg-dark-card border border-dark-border rounded-2xl px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-primary-400 animate-spin" />
                    <p className="text-sm text-primary-400">Thinking...</p>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="p-4 border-t border-dark-border">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-4">
              <div className="flex-1 relative">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask me about stocks, financial reports, news..."
                  className="w-full px-4 py-3 bg-dark-card border border-dark-border rounded-xl text-primary-200 placeholder-primary-400 focus:outline-none focus:border-primary-500 resize-none"
                  rows={1}
                  disabled={loading}
                />
              </div>
              <button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className="px-4 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/50 disabled:cursor-not-allowed text-white rounded-xl transition-colors flex items-center gap-2"
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
            <p className="text-xs text-primary-400 mt-2 text-center">
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
