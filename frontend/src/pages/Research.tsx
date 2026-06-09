import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Rocket, Loader2, CheckCircle, AlertCircle, FileText, Brain, Zap, Lightbulb, Target, Clock } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import { taskApi } from '../services/api'
import { cleanAIText } from '../utils/utils'
import type { TaskStatusResponse, TaskResultResponse } from '../types/api'

type Phase = 'idle' | 'creating' | 'running' | 'completed' | 'error'

const markdownComponents = {
  h1: ({children}: { children?: React.ReactNode }) => <h1 className="text-xl font-bold text-primary-50 mb-3">{children}</h1>,
  h2: ({children}: { children?: React.ReactNode }) => <h2 className="text-lg font-semibold text-primary-100 mb-3">{children}</h2>,
  h3: ({children}: { children?: React.ReactNode }) => <h3 className="text-base font-semibold text-primary-200 mb-2">{children}</h3>,
  p: ({children}: { children?: React.ReactNode }) => <p className="text-sm text-primary-200 leading-relaxed mb-2">{children}</p>,
  ul: ({children}: { children?: React.ReactNode }) => <ul className="list-disc list-inside text-sm text-primary-200 mb-3 space-y-1">{children}</ul>,
  ol: ({children}: { children?: React.ReactNode }) => <ol className="list-decimal list-inside text-sm text-primary-200 mb-3 space-y-1">{children}</ol>,
  li: ({children}: { children?: React.ReactNode }) => <li className="text-primary-200">{children}</li>,
  strong: ({children}: { children?: React.ReactNode }) => <strong className="font-semibold text-primary-100">{children}</strong>,
  em: ({children}: { children?: React.ReactNode }) => <em className="italic text-primary-300">{children}</em>,
  table: ({children}: { children?: React.ReactNode }) => (
    <div className="my-4 rounded-xl border border-dark-border overflow-hidden bg-dark-bg/50">
      <div className="overflow-x-auto">
        <table className="w-full text-sm min-w-[700px]">{children}</table>
      </div>
    </div>
  ),
  thead: ({children}: { children?: React.ReactNode }) => <thead className="bg-gradient-to-r from-primary-500/20 to-primary-600/10">{children}</thead>,
  tbody: ({children}: { children?: React.ReactNode }) => <tbody className="divide-y divide-dark-border">{children}</tbody>,
  tr: ({children}: { children?: React.ReactNode }) => <tr className="hover:bg-primary-500/5 transition-colors">{children}</tr>,
  th: ({children}: { children?: React.ReactNode }) => (
    <th className="px-5 py-3.5 text-left text-xs font-bold text-primary-200 uppercase tracking-wider border-r border-dark-border/50 last:border-r-0">
      {children}
    </th>
  ),
  td: ({children}: { children?: React.ReactNode }) => (
    <td className="px-5 py-4 text-sm text-primary-300 border-r border-dark-border/30 last:border-r-0 align-top">
      {children}
    </td>
  ),
  code: ({children}: { children?: React.ReactNode }) => <code className="bg-dark-card px-1.5 py-0.5 rounded text-xs text-primary-300 font-mono">{children}</code>,
  hr: () => <hr className="border-dark-border my-6" />,
}

const POLL_INTERVAL = 2000
const STORAGE_KEY = 'research_state'

interface SavedState {
  query: string
  phase: Phase
  taskId: string | null
  result?: TaskResultResponse | null
  taskStatus?: TaskStatusResponse | null
  error?: string | null
}

function saveState(state: SavedState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch { /* ignore */ }
}

function loadState(): SavedState | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return null
}

function clearState() {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch { /* ignore */ }
}

export default function Research() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  // Initialize from localStorage if available
  const saved = loadState()
  const [query, setQuery] = useState(saved?.query || '')
  const [phase, setPhase] = useState<Phase>(saved?.phase || 'idle')
  const [taskId, setTaskId] = useState<string | null>(saved?.taskId || null)
  const [taskStatus, setTaskStatus] = useState<TaskStatusResponse | null>(saved?.taskStatus || null)
  const [result, setResult] = useState<TaskResultResponse | null>(saved?.result || null)
  const [error, setError] = useState<string | null>(saved?.error || null)
  const stopRef = useRef(false)
  const pollingRef = useRef(false)
  const mountedRef = useRef(true)

  // Persist state changes
  useEffect(() => {
    if (phase === 'running' || phase === 'creating') {
      saveState({ query, phase, taskId, taskStatus })
    } else if (phase === 'completed') {
      saveState({ query, phase, taskId, result, taskStatus })
    } else if (phase === 'error') {
      saveState({ query, phase, taskId, error })
    } else if (phase === 'idle') {
      clearState()
    }
  }, [query, phase, taskId, taskStatus, result, error])

  // Resume polling if returning to page with active task
  useEffect(() => {
    mountedRef.current = true
    stopRef.current = false

    if ((phase === 'running' || phase === 'creating') && taskId && !pollingRef.current) {
      resumePolling(taskId)
    }
    return () => {
      mountedRef.current = false
      stopRef.current = true
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const resumePolling = useCallback(async (activeTaskId: string) => {
    console.log('[Research] resumePolling called for task:', activeTaskId)
    if (pollingRef.current) {
      console.log('[Research] Already polling, skipping')
      return
    }
    pollingRef.current = true
    stopRef.current = false

    // Immediately fetch current status
    try {
      console.log('[Research] Fetching initial status...')
      const statusResp = await taskApi.getStatus(activeTaskId)
      console.log('[Research] Initial status:', statusResp.status, 'progress:', statusResp.progress)
      if (stopRef.current || !mountedRef.current) {
        pollingRef.current = false
        return
      }
      setTaskStatus(statusResp)

      // Check if already completed
      if (statusResp.status === 'completed') {
        pollingRef.current = false
        try {
          console.log('[Research] Task completed, fetching result...')
          const resultResp = await taskApi.getResult(activeTaskId)
          console.log('[Research] Result received:', resultResp ? 'success' : 'empty')
          if (!stopRef.current && mountedRef.current) {
            setResult(resultResp)
            setPhase('completed')
            saveState({ query, phase: 'completed', taskId: activeTaskId, result: resultResp, taskStatus: statusResp })
          }
        } catch (err) {
          console.error('[Research] Failed to fetch result:', err)
          if (!stopRef.current && mountedRef.current) {
            setError(t('error.serverError'))
            setPhase('error')
          }
        }
        return
      }

      // Check if already failed - show error immediately
      if (statusResp.status === 'failed') {
        pollingRef.current = false
        if (!stopRef.current && mountedRef.current) {
          setError(statusResp.message || t('research.taskFailed'))
          setPhase('error')
        }
        return
      }
    } catch (err) {
      console.error('[Research] Failed to fetch initial status:', err)
      // Status fetch failed, will retry in polling loop
    }
    pollingRef.current = true
    stopRef.current = false

    // Immediately fetch current status
    try {
      console.log('[Research] Fetching initial status...')
      const statusResp = await taskApi.getStatus(activeTaskId)
      console.log('[Research] Initial status:', statusResp.status, 'progress:', statusResp.progress)
      if (stopRef.current || !mountedRef.current) {
        pollingRef.current = false
        return
      }
      setTaskStatus(statusResp)

      // Check if already completed
      if (statusResp.status === 'completed') {
        pollingRef.current = false
        try {
          console.log('[Research] Task completed, fetching result...')
          const resultResp = await taskApi.getResult(activeTaskId)
          console.log('[Research] Result received:', resultResp ? 'success' : 'empty')
          if (!stopRef.current && mountedRef.current) {
            setResult(resultResp)
            setPhase('completed')
            saveState({ query, phase: 'completed', taskId: activeTaskId, result: resultResp, taskStatus: statusResp })
          }
        } catch (err) {
          console.error('[Research] Failed to fetch result:', err)
          if (!stopRef.current && mountedRef.current) {
            setError(t('error.serverError'))
            setPhase('error')
          }
        }
        return
      }

      // Check if already failed - show error immediately
      if (statusResp.status === 'failed') {
        pollingRef.current = false
        if (!stopRef.current && mountedRef.current) {
          setError(statusResp.message || t('research.taskFailed'))
          setPhase('error')
        }
        return
      }
    } catch (err) {
      console.error('[Research] Failed to fetch initial status:', err)
      // Status fetch failed, will retry in polling loop
    }

    // Continue polling
    let pollCount = 0
    const maxPolls = 300
    let stopped = false

    const poll = async () => {
      if (stopped || stopRef.current || !mountedRef.current) {
        console.log('[Research] Polling stopped')
        pollingRef.current = false
        return
      }
      pollCount++
      console.log(`[Research] Poll #${pollCount}`)
      if (pollCount > maxPolls) {
        stopped = true
        pollingRef.current = false
        if (mountedRef.current) {
          setError(t('error.timeout'))
          setPhase('error')
        }
        return
      }

      try {
        const statusResp = await taskApi.getStatus(activeTaskId)
        console.log('[Research] Poll status:', statusResp.status, 'progress:', statusResp.progress)
        if (stopped || stopRef.current || !mountedRef.current) {
          pollingRef.current = false
          return
        }

        setTaskStatus(statusResp)

        if (statusResp.status === 'completed') {
          stopped = true
          pollingRef.current = false
          try {
            console.log('[Research] Task completed, fetching result...')
            const resultResp = await taskApi.getResult(activeTaskId)
            console.log('[Research] Result received:', resultResp ? 'success' : 'empty')
            if (!stopRef.current && mountedRef.current) {
              setResult(resultResp)
              setPhase('completed')
              saveState({ query, phase: 'completed', taskId: activeTaskId, result: resultResp, taskStatus: statusResp })
            }
          } catch (err) {
            console.error('[Research] Failed to fetch result:', err)
            if (!stopRef.current && mountedRef.current) {
              setError(t('error.serverError'))
              setPhase('error')
            }
          }
          return
        }

        if (statusResp.status === 'failed') {
          stopped = true
          pollingRef.current = false
          if (!stopRef.current && mountedRef.current) {
            setError(statusResp.message || t('research.taskFailed'))
            setPhase('error')
          }
          return
        }

        if (!stopped && !stopRef.current && mountedRef.current) {
          setTimeout(poll, POLL_INTERVAL)
        }
      } catch (err) {
        console.error('[Research] Poll error:', err)
        if (!stopped && !stopRef.current && mountedRef.current) {
          setTimeout(poll, POLL_INTERVAL)
        }
      }
    }

    poll()
  }, [t])

  const handleReset = useCallback(() => {
    stopRef.current = true
    pollingRef.current = false
    setPhase('idle')
    setTaskId(null)
    setTaskStatus(null)
    setResult(null)
    setError(null)
    setQuery('')
    clearState()
  }, [])

  const startResearch = useCallback(async () => {
    if (!query.trim() || phase === 'running' || phase === 'creating') return

    console.log('[Research] Starting research for query:', query)
    stopRef.current = false
    pollingRef.current = false
    setPhase('creating')
    setError(null)
    setResult(null)
    setTaskStatus(null)

    try {
      console.log('[Research] Creating task...')
      const createResp = await taskApi.create(query)
      const newTaskId = createResp.task_id
      console.log('[Research] Task created:', newTaskId)
      setTaskId(newTaskId)

      console.log('[Research] Running task...')
      await taskApi.run(newTaskId)
      console.log('[Research] Task started, beginning polling...')
      setPhase('running')
      saveState({ query, phase: 'running', taskId: newTaskId })

      resumePolling(newTaskId)
    } catch (err: unknown) {
      console.error('[Research] Error starting research:', err)
      setError(err instanceof Error ? err.message : t('error.serverError'))
      setPhase('error')
    }
  }, [query, phase, t, resumePolling])

  const getStageLabel = (stage: string) => {
    switch (stage) {
      case 'planning': return t('research.planning')
      case 'executing': return t('research.executing')
      case 'reasoning': return t('research.reasoning')
      case 'reporting': return t('research.reporting')
      default: return t('common.loading')
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-primary-50">{t('research.title')}</h1>
        <p className="text-sm text-primary-400 mt-1">{t('research.queryPlaceholder')}</p>
      </div>

      {/* Input */}
      <div className="card">
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && startResearch()}
            placeholder={t('research.queryPlaceholder')}
            className="input flex-1"
            disabled={phase === 'running' || phase === 'creating'}
          />
          <button
            onClick={startResearch}
            disabled={!query.trim() || phase === 'running' || phase === 'creating'}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 disabled:from-primary-500/50 disabled:to-primary-600/50 disabled:cursor-not-allowed text-white rounded-full shadow-lg shadow-primary-500/20 transition-all duration-200 hover:shadow-primary-500/30 hover:scale-[1.02] disabled:hover:scale-100"
          >
            <Rocket className={`w-4 h-4 ${phase === 'running' || phase === 'creating' ? 'hidden' : ''}`} />
            <Loader2 className={`w-4 h-4 animate-spin ${phase === 'running' || phase === 'creating' ? '' : 'hidden'}`} />
            <span className="font-medium">
              {phase === 'creating' ? t('research.analyzing') : phase === 'running' ? t('research.analyzing') : t('research.startResearch')}
            </span>
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card border-red-500/30">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <div>
              <p className="text-sm font-medium text-red-500">{t('common.error')}</p>
              <p className="text-xs text-red-400 mt-1">{error}</p>
            </div>
          </div>
          <button onClick={handleReset} className="mt-3 text-sm text-red-500 hover:text-red-400">{t('error.tryAgain')}</button>
        </div>
      )}

      {/* Loading / Progress */}
      {(phase === 'creating' || phase === 'running') && (
        <div className="card">
          <div className="flex flex-col items-center py-8">
            <Loader2 className="w-12 h-12 text-primary-500 animate-spin mb-4" />
            <p className="text-lg font-semibold text-primary-200 mb-2">
              {phase === 'creating' ? t('research.analyzing') : getStageLabel(taskStatus?.current_stage || '')}
            </p>
            {taskStatus && (
              <div className="w-full max-w-md">
                <div className="flex justify-between text-sm text-primary-400 mb-2">
                  <span>{taskStatus.current_stage}</span>
                  <span>{taskStatus.progress.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-dark-border rounded-full h-3">
                  <div
                    className="bg-gradient-to-r from-primary-500 to-blue-500 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${taskStatus.progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Completed Result */}
      {phase === 'completed' && result && (
        <div className="space-y-6">
          {/* Success Banner */}
          <div className="card border-green-500/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-6 h-6 text-green-500" />
                <div>
                  <p className="text-sm font-medium text-green-500">{t('research.completed')}</p>
                  <p className="text-xs text-green-400 mt-1">
                    {result.total_tasks || 0} {t('dashboard.totalTasks')} | {t('system.metrics')}: {result.confidence ? `${(result.confidence * 100).toFixed(0)}%` : '-'}
                  </p>
                </div>
              </div>
              <div className="flex gap-3">
                <button onClick={handleReset} className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary-200 bg-primary-500/10 hover:bg-primary-500/20 border border-primary-500/30 rounded-lg transition-all duration-200 hover:scale-[1.02]">
                  <Zap className="w-4 h-4" /> {t('research.newTask')}
                </button>
                {taskId && (
                  <button onClick={() => navigate(`/report/${taskId}`)} className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-200 bg-blue-500/15 hover:bg-blue-500/25 border border-blue-400/40 rounded-xl transition-all duration-200 hover:scale-[1.02] shadow-lg shadow-blue-500/10">
                    <FileText className="w-4 h-4" /> {t('report.title')}
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Answer */}
          {result.answer && (
            <div className="card">
              <h2 className="text-lg font-semibold text-primary-50 mb-3">{t('research.results')}</h2>
              <div className="bg-dark-bg rounded-lg p-4 border border-dark-border max-h-[600px] overflow-y-auto">
                <ReactMarkdown rehypePlugins={[rehypeSanitize]} components={markdownComponents}>
                  {result.answer}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* Key Findings */}
          {result.key_findings && result.key_findings.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-5 h-5 text-blue-500" />
                <h3 className="text-lg font-semibold text-primary-50">{t('report.keyFindings')}</h3>
              </div>
              <div className="space-y-2">
                {result.key_findings.map((finding, i) => (
                  <div key={`finding-${i}`} className="flex items-start gap-3 p-3 bg-dark-bg rounded-lg border border-dark-border">
                    <div className="w-6 h-6 bg-blue-500/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-xs font-bold text-blue-500">{i + 1}</span>
                    </div>
                    <p className="text-sm text-primary-200">{cleanAIText(finding)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {result.recommendations && result.recommendations.length > 0 && (
            <div className="card">
              <div className="flex items-center gap-2 mb-3">
                <Target className="w-5 h-5 text-green-500" />
                <h3 className="text-lg font-semibold text-primary-50">{t('report.recommendations')}</h3>
              </div>
              <div className="space-y-2">
                {result.recommendations.map((rec, i) => (
                  <div key={`rec-${i}`} className="flex items-start gap-3 p-3 bg-dark-bg rounded-lg border border-dark-border">
                    <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                    <p className="text-sm text-primary-200">{cleanAIText(rec)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-5 gap-4">
            <div className="card text-center">
              <Brain className="w-5 h-5 text-blue-500 mx-auto mb-2" />
              <p className="text-xs text-primary-400 uppercase">{t('dashboard.totalTasks')}</p>
              <p className="text-2xl font-bold text-primary-50">{result.total_tasks || 0}</p>
            </div>
            <div className="card text-center">
              <CheckCircle className="w-5 h-5 text-green-500 mx-auto mb-2" />
              <p className="text-xs text-green-400 uppercase">{t('dashboard.completedTasks')}</p>
              <p className="text-2xl font-bold text-green-500">{result.success_tasks || 0}</p>
            </div>
            <div className="card text-center">
              <Lightbulb className="w-5 h-5 text-yellow-500 mx-auto mb-2" />
              <p className="text-xs text-yellow-400 uppercase">{t('research.priority')}</p>
              <p className="text-2xl font-bold text-yellow-500">{result.confidence ? `${(result.confidence * 100).toFixed(0)}%` : '-'}</p>
            </div>
            <div className="card text-center">
              <Zap className="w-5 h-5 text-purple-500 mx-auto mb-2" />
              <p className="text-xs text-purple-400 uppercase">{t('report.keyFindings')}</p>
              <p className="text-2xl font-bold text-purple-500">{result.reasoning_insights?.length || 0}</p>
            </div>
            <div className="card text-center">
              <Clock className="w-5 h-5 text-cyan-500 mx-auto mb-2" />
              <p className="text-xs text-cyan-400 uppercase">{t('system.uptime')}</p>
              <p className="text-2xl font-bold text-cyan-500">{result.elapsed ? `${result.elapsed.toFixed(1)}s` : '-'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Idle State */}
      {phase === 'idle' && !error && (
        <div className="card text-center py-12">
          <Brain className="w-16 h-16 text-primary-400/20 mx-auto mb-4" />
          <p className="text-primary-400">{t('research.queryPlaceholder')}</p>
          <p className="text-xs text-primary-500 mt-2">{t('research.startResearch')}</p>
        </div>
      )}
    </div>
  )
}
