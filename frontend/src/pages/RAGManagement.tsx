import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Database,
  Upload,
  FileText,
  Trash2,
  RefreshCw,
  Search,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
  HardDrive,
  Brain,
} from 'lucide-react'
import { ragApi } from '../services/api'

interface DocumentInfo {
  id: string
  filename: string
  status: string
  chunks: number
  chunk_count?: number
  file_size?: number
  created_at: string
}

interface RAGStatsResponse {
  total_documents: number
  total_chunks: number
  vector_store_size?: number
  embedding_mode?: string
}
import { useToast } from '../components/ui/ToastContext'

export default function RAGManagement() {
  const { t } = useTranslation()
  const toast = useToast()
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [stats, setStats] = useState<RAGStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<{ text: string; score: number; metadata: Record<string, unknown> }[]>([])
  const [searching, setSearching] = useState(false)
  const [dragActive, setDragActive] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [docsRes, statsRes] = await Promise.all([
        ragApi.listDocuments(),
        ragApi.getStats(),
      ])
      setDocuments(docsRes.documents)
      setStats(statsRes)
    } catch (err: unknown) {
      toast.error(t('common.error'), err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [t, toast])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return

    const file = files[0]
    const allowedTypes = ['.txt', '.md', '.json', '.csv', '.pdf', '.docx']
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()

    if (!allowedTypes.includes(fileExt)) {
      toast.error(t('common.error'), `Unsupported file type: ${fileExt}`)
      return
    }

    setUploading(true)
    try {
      const result = await ragApi.uploadDocument(file)
      toast.success(t('rag.uploadSuccess'), result.message)
      fetchData()
    } catch (err: unknown) {
      toast.error(t('rag.uploadFailed'), err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setUploading(false)
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    handleFileUpload(e.dataTransfer.files)
  }

  const handleDelete = async (docId: string) => {
    if (!window.confirm(t('rag.confirmDelete'))) return

    try {
      await ragApi.deleteDocument(docId)
      toast.success(t('common.success'), t('rag.deleteSuccess'))
      fetchData()
    } catch (err: unknown) {
      toast.error(t('common.error'), err instanceof Error ? err.message : 'Unknown error')
    }
  }

  const handleReindex = async () => {
    try {
      await ragApi.reindex()
      toast.success(t('common.success'), t('rag.reindexStarted'))
      fetchData()
    } catch (err: unknown) {
      toast.error(t('common.error'), err instanceof Error ? err.message : 'Unknown error')
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    setSearching(true)
    try {
      const result = await ragApi.search(searchQuery)
      setSearchResults(result.results)
    } catch (err: unknown) {
      toast.error(t('common.error'), err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setSearching(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'processing':
        return <Clock className="w-4 h-4 text-yellow-500 animate-pulse" />
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />
      default:
        return <Clock className="w-4 h-4 text-gray-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-success">{t('rag.statusCompleted')}</span>
      case 'processing':
        return <span className="badge badge-running">{t('rag.statusProcessing')}</span>
      case 'failed':
        return <span className="badge badge-error">{t('rag.statusFailed')}</span>
      default:
        return <span className="badge badge-pending">{status}</span>
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary-50">{t('rag.title')}</h1>
          <p className="text-sm text-primary-400 mt-1">{t('rag.subtitle')}</p>
        </div>
        <button
          onClick={handleReindex}
          className="btn-secondary flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          {t('rag.reindex')}
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-xs font-semibold text-primary-400 uppercase">{t('rag.totalDocuments')}</p>
                <p className="text-2xl font-bold text-primary-50">{stats.total_documents}</p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-dark-hover rounded-lg flex items-center justify-center">
                <Database className="w-5 h-5 text-primary-300" />
              </div>
              <div>
                <p className="text-xs font-semibold text-primary-400 uppercase">{t('rag.totalChunks')}</p>
                <p className="text-2xl font-bold text-primary-50">{stats.total_chunks}</p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center">
                <HardDrive className="w-5 h-5 text-green-500" />
              </div>
              <div>
                <p className="text-xs font-semibold text-primary-400 uppercase">{t('rag.vectorStore')}</p>
                <p className="text-2xl font-bold text-primary-50">{stats.vector_store_size}</p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-yellow-500/10 rounded-lg flex items-center justify-center">
                <Brain className="w-5 h-5 text-yellow-500" />
              </div>
              <div>
                <p className="text-xs font-semibold text-primary-400 uppercase">{t('rag.embeddingMode')}</p>
                <p className="text-lg font-bold text-primary-50 capitalize">{stats.embedding_mode}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Upload Area */}
      <div className="card">
        <h2 className="text-lg font-semibold text-primary-50 mb-4">{t('rag.uploadDocument')}</h2>
        <div
          className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
            dragActive
              ? 'border-primary-500 bg-primary-500/10'
              : 'border-dark-border hover:border-primary-500/50'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          {uploading ? (
            <div className="flex flex-col items-center">
              <Loader2 className="w-12 h-12 text-primary-500 animate-spin mb-4" />
              <p className="text-primary-400">{t('rag.uploading')}</p>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <Upload className="w-12 h-12 text-primary-400 mb-4" />
              <p className="text-primary-200 mb-2">{t('rag.dragDrop')}</p>
              <p className="text-sm text-primary-400 mb-4">{t('rag.supportedTypes')}</p>
              <label className="flex items-center gap-2 px-5 py-2 bg-accent hover:bg-[#74acff] text-[#06121f] font-medium rounded-lg transition-colors duration-150 cursor-pointer">
                <Upload className="w-4 h-4" />
                <span className="font-medium">{t('rag.browseFiles')}</span>
                <input
                  type="file"
                  className="hidden"
                  accept=".txt,.md,.json,.csv"
                  onChange={(e) => handleFileUpload(e.target.files)}
                />
              </label>
            </div>
          )}
        </div>
      </div>

      {/* Search Section */}
      <div className="card">
        <h2 className="text-lg font-semibold text-primary-50 mb-4">{t('rag.searchDocuments')}</h2>
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-4 h-4 text-primary-400 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder={t('rag.searchPlaceholder')}
              className="w-full py-3 pl-11 pr-4 bg-dark-card border border-dark-border rounded-lg text-primary-200 placeholder-primary-400 focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-all"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={searching || !searchQuery.trim()}
            className="flex items-center gap-2 px-5 py-2 bg-accent hover:bg-[#74acff] text-[#06121f] font-medium rounded-lg transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {searching ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            <span className="font-medium">{t('common.search')}</span>
          </button>
        </div>

        {/* Search Results */}
        {searchResults.length > 0 && (
          <div className="mt-4 space-y-3">
            <h3 className="text-sm font-semibold text-primary-400">
              {t('rag.searchResults')} ({searchResults.length})
            </h3>
            {searchResults.map((result, i) => (
              <div key={i} className="p-3 bg-dark-bg rounded-lg border border-dark-border">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-primary-400">
                    {t('rag.relevance')}: {(result.score * 100).toFixed(1)}%
                  </span>
                  {typeof result.metadata?.doc_id === 'string' && (
                    <span className="text-xs text-primary-500">
                      {t('rag.source')}: {result.metadata.doc_id}
                    </span>
                  )}
                </div>
                <p className="text-sm text-primary-200">{result.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Documents List */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-primary-50">{t('rag.documents')}</h2>
          <span className="text-sm text-primary-400">{documents.length} {t('rag.totalDocuments')}</span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-12">
            <Database className="w-12 h-12 text-primary-400 mx-auto mb-4" />
            <p className="text-primary-400">{t('rag.noDocuments')}</p>
            <p className="text-sm text-primary-500 mt-1">{t('rag.uploadToStart')}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-4 bg-dark-bg rounded-lg border border-dark-border hover:border-primary-500/30 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-primary-500/10 rounded-lg flex items-center justify-center">
                    <FileText className="w-5 h-5 text-primary-500" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-primary-200">{doc.filename}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-primary-400">{formatFileSize(doc.file_size || 0)}</span>
                      <span className="text-xs text-primary-400">•</span>
                      <span className="text-xs text-primary-400">{doc.chunk_count || doc.chunks} {t('rag.chunks')}</span>
                      <span className="text-xs text-primary-400">•</span>
                      <span className="text-xs text-primary-400">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {getStatusIcon(doc.status)}
                  {getStatusBadge(doc.status)}
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-2 text-primary-400 hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                    title={t('common.delete')}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
