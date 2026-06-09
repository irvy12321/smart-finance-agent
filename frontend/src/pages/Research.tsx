import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Rocket, Loader2, CheckCircle, AlertCircle, FileText, Brain, Zap, Lightbulb, Target } from 'lucide-react'
import { taskApi } from '../services/api'
import type { TaskStatusResponse, TaskResultResponse } from '../types/api'

type Phase = 'idle' | 'creating' | 'running' | 'completed' | 'error'

const POLL_INTERVAL = 2000

export default function Research() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [phase, setPhase] = useState<Phase>('idle')
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<TaskStatusResponse | null>(null)
  const [result, setResult] = useState<TaskResultResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const stopRef = useRef(false)

  useEffect(() => {
    return () => { stopRef.current = true }
  }, [])

  const handleReset = useCallback(() => {
    stopRef.current = true
    setPhase('idle')
    setTaskId(null)
    setTaskStatus(null)
    setResult(null)
    setError(null)
    setQuery('')
  }, [])

  const startResearch = useCallback(async () => {
    if (!query.trim() || phase === 'running' || phase === 'creating') return

    stopRef.current = false
    setPhase('creating')
    setError(null)
    setResult(null)
    setTaskStatus(null)

    try {
      const createResp = await taskApi.create(query)
      const newTaskId = createResp.task_id
      setTaskId(newTaskId)

      await taskApi.run(newTaskId)
      setPhase('running')

      let pollCount = 0
      const maxPolls = 120
      let stopped = false

      const poll = async () => {
        if (stopped || stopRef.current) return
        pollCount++
        if (pollCount > maxPolls) {
          stopped = true
          setError(t('error.timeout'))
          setPhase('error')
          return
        }

        try {
          const statusResp = await taskApi.getStatus(newTaskId)
          if (stopped || stopRef.current) return

          setTaskStatus(statusResp)

          if (statusResp.status === 'completed') {
            stopped = true
            try {
              const resultResp = await taskApi.getResult(newTaskId)
              if (!stopRef.current) {
                setResult(resultResp)
                setPhase('completed')
              }
            } catch {
              if (!stopRef.current) {
                setError(t('error.serverError'))
                setPhase('error')
              }
            }
            return
          }

          if (statusResp.status === 'failed') {
            stopped = true
            if (!stopRef.current) {
              setError(statusResp.message || t('research.taskFailed'))
              setPhase('error')
            }
            return
          }

          if (!stopped && !stopRef.current) {
            setTimeout(poll, POLL_INTERVAL)
          }
        } catch {
          if (!stopped && !stopRef.current) {
            setTimeout(poll, POLL_INTERVAL)
          }
        }
      }

      poll()
    } catch (err: any) {
      setError(err.message || t('error.serverError'))
      setPhase('error')
    }
  }, [query, phase, t])

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
        <div className="flex gap-4">
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
            className="btn-primary flex items-center gap-2 disabled:opacity-50"
          >
            <Rocket className={`w-4 h-4 ${phase === 'running' || phase === 'creating' ? 'hidden' : ''}`} />
            <Loader2 className={`w-4 h-4 animate-spin ${phase === 'running' || phase === 'creating' ? '' : 'hidden'}`} />
            {phase === 'creating' ? t('research.analyzing') : phase === 'running' ? t('research.analyzing') : t('research.startResearch')}
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
                <button onClick={handleReset} className="text-sm text-primary-400 hover:text-primary-200">{t('research.newTask')}</button>
                {taskId && (
                  <button onClick={() => navigate(`/report/${taskId}`)} className="btn-primary flex items-center gap-2 text-sm">
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
              <div className="bg-dark-bg rounded-lg p-4 border border-dark-border">
                <p className="text-sm text-primary-200 whitespace-pre-wrap leading-relaxed">{result.answer}</p>
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
                    <p className="text-sm text-primary-200">{finding}</p>
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
                    <p className="text-sm text-primary-200">{rec}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-4 gap-4">
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
