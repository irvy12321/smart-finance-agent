import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
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
  BarChart3,
  FileText
} from 'lucide-react'
import { chatApi } from '../services/api'
import { cleanAIText } from '../utils/utils'
import type { ChatMessage, ConversationListItem } from '../types/api'

const CHAT_STORAGE_KEY = 'chat_state'

const REPORT_LINK_RE = /\n*(?:完整研究报告|Full research report):\s*\/report\/([0-9a-f-]{4,})\s*$/i

function extractReportLink(content: string): { text: string; reportTaskId: string | null } {
  const match = content.match(REPORT_LINK_RE)
  if (!match) return { text: content, reportTaskId: null }
  return { text: content.replace(REPORT_LINK_RE, '').trimEnd(), reportTaskId: match[1] }
}

interface SavedChatState {
  conversationId: string | null
  messages: ChatMessage[]
}

function saveChatState(state: SavedChatState) {
  try {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(state))
  } catch { /* ignore */ }
}

function loadChatState(): SavedChatState | null {
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return null
}

function clearChatState() {
  try {
    localStorage.removeItem(CHAT_STORAGE_KEY)
  } catch { /* ignore */ }
}

export default function Chat() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  // Initialize from localStorage
  const saved = loadChatState()
  const [messages, setMessages] = useState<ChatMessage[]>(saved?.messages || [])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(saved?.conversationId || null)
  const [conversations, setConversations] = useState<ConversationListItem[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Persist state when it changes
  useEffect(() => {
    if (conversationId && messages.length > 0) {
      saveChatState({ conversationId, messages })
    }
  }, [conversationId, messages])

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
    } catch (error: unknown) {
      if (error instanceof Error && (error.name === 'AbortError' || (error as { code?: string }).code === 'ERR_CANCELED')) return
      console.error('Failed to fetch conversations:', error)
    }
  }

  const createNewConversation = async () => {
    try {
      const data = await chatApi.createConversation()
      setConversationId(data.conversation_id)
      setMessages([])
      clearChatState()
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
      saveChatState({ conversationId: convId, messages: data.messages || [] })
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
        clearChatState()
      }
      fetchConversations()
    } catch (error) {
      console.error('Failed to delete conversation:', error)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage: ChatMessage = {
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

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: data.timestamp,
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Failed to send message:', error)
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: t('chat.failedToSend'),
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
      label: t('stock.price'),
      query: t('chat.quickStockPrice'),
      color: 'text-green-500',
      bg: 'bg-green-500/10',
    },
    {
      icon: BarChart3,
      label: t('stock.getAnalysis'),
      query: t('chat.quickAnalysis'),
      color: 'text-blue-500',
      bg: 'bg-blue-500/10',
    },
    {
      icon: Newspaper,
      label: t('report.sources'),
      query: t('chat.quickNews'),
      color: 'text-primary-200',
      bg: 'bg-dark-hover',
    },
    {
      icon: DollarSign,
      label: t('report.marketTrends'),
      query: t('chat.quickTrends'),
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
            {t('chat.newConversation')}
          </button>
        </div>

        <div className="flex-1 overflow-auto p-2">
          {conversations.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="w-8 h-8 text-primary-400 mx-auto mb-2" />
              <p className="text-xs text-primary-400">{t('chat.noConversations')}</p>
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
                      {t('chat.title')} {conv.conversation_id.slice(0, 6)}
                    </p>
                    <p className="text-xs text-primary-400 mt-1">
                      {conv.message_count} {t('chat.typeMessage')}
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
              <h1 className="text-xl font-bold text-primary-50">{t('chat.title')}</h1>
              <p className="text-sm text-primary-400 mt-1">
                {t('chat.typeMessage')}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="status-dot status-dot-success" />
              <span className="text-xs text-primary-300">{t('sidebar.apiConnected')}</span>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.length === 0 && !loading && (
              <div className="flex flex-col items-center justify-center h-full py-12">
                <div className="text-center max-w-2xl">
                  <div className="w-12 h-12 rounded-lg bg-dark-card border border-dark-border flex items-center justify-center mx-auto mb-6">
                    <Bot className="w-6 h-6 text-accent" />
                  </div>
                  <h2 className="text-2xl font-bold text-primary-50 mb-4">
                    {t('sidebar.title')}
                  </h2>
                  <p className="text-primary-400 mb-8">
                    {t('chat.typeMessage')}
                  </p>

                  {/* Quick Actions */}
                  <div className="grid grid-cols-2 gap-4">
                    {quickActions.map((action, index) => (
                      <button
                        key={index}
                        onClick={() => handleQuickAction(action.query)}
                        className="flex items-center gap-3 p-4 bg-dark-card rounded-lg border border-dark-border hover:border-accent/40 hover:bg-dark-hover transition-colors text-left"
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
                  className={`max-w-[70%] rounded-xl px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-accent text-[#06121f]'
                      : 'bg-dark-card border border-dark-border'
                  }`}
                >
                  {message.role === 'assistant' ? (() => {
                    const { text, reportTaskId } = extractReportLink(message.content)
                    return (
                      <>
                        <p className="text-sm whitespace-pre-wrap">{cleanAIText(text)}</p>
                        {reportTaskId && (
                          <button
                            onClick={() => navigate(`/report/${reportTaskId}`)}
                            className="mt-3 flex items-center gap-2 px-3 py-2 text-xs font-medium text-primary-200 bg-dark-hover hover:bg-dark-border border border-dark-border rounded-lg transition-colors"
                          >
                            <FileText className="w-4 h-4" />
                            {t('chat.viewFullReport')}
                          </button>
                        )}
                      </>
                    )
                  })() : (
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  )}
                  <p className={`text-xs mt-2 ${
                    message.role === 'user' ? 'text-[#06121f]/60' : 'text-primary-400'
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
                <div className="bg-dark-card border border-dark-border rounded-xl px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-primary-400 animate-spin" />
                    <p className="text-sm text-primary-400">{t('chat.thinking')}</p>
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
                  placeholder={t('chat.typeMessage')}
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
              {t('chat.send')} (Enter) | Shift+Enter
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
