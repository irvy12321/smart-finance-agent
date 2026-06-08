import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Rocket, Loader2, CheckCircle, AlertCircle, FileText, Brain, Zap, Lightbulb, Target } from 'lucide-react'
import { taskApi } from '../services/api'
import type { TaskStatusResponse, TaskResultResponse } from '../types/api'

type Phase = 'idle' | 'creating' | 'running' | 'completed' | 'error'

const POLL_INTERVAL = 2000

export default function Research() {
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
      // Step 1: Create task
      const createResp = await taskApi.create(query)
      const newTaskId = createResp.task_id
      setTaskId(newTaskId)

      // Step 2: Run task
      await taskApi.run(newTaskId)
      setPhase('running')

      // Step 3: Poll status (recursive setTimeout, not setInterval)
      let pollCount = 0
      const maxPolls = 120
      let stopped = false

      const poll = async () => {
        if (stopped || stopRef.current) return
        pollCount++
        if (pollCount > maxPolls) {
          stopped = true
          setError('任务超时（4分钟），请重试')
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
                setError('任务完成但获取结果失败')
                setPhase('error')
              }
            }
            return
          }

          if (statusResp.status === 'failed') {
            stopped = true
            if (!stopRef.current) {
              setError(statusResp.message || '任务执行失败')
              setPhase('error')
            }
            return
          }

          // Continue polling
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
      setError(err.message || '任务启动失败')
      setPhase('error')
    }
  }, [query, phase])

  const getStageLabel = (stage: string) => {
    switch (stage) {
      case 'planning': return '规划中：分析复杂度...'
      case 'executing': return '执行中：运行子任务...'
      case 'reasoning': return '推理中：提取洞察...'
      case 'reporting': return '报告中：编译报告...'
      default: return '处理中...'
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-primary-50">Research</h1>
        <p className="text-sm text-primary-400 mt-1">输入金融研究问题，AI 自动分析</p>
      </div>

      {/* Input */}
      <div className="card">
        <div className="flex gap-4">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && startResearch()}
            placeholder="e.g. Analyze the impact of AI on semiconductor stocks"
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
            {phase === 'creating' ? '创建中...' : phase === 'running' ? '运行中...' : 'Run Research'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card border-red-500/30">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <div>
              <p className="text-sm font-medium text-red-500">错误</p>
              <p className="text-xs text-red-400 mt-1">{error}</p>
            </div>
          </div>
          <button onClick={handleReset} className="mt-3 text-sm text-red-500 hover:text-red-400">重试</button>
        </div>
      )}

      {/* Loading / Progress */}
      {(phase === 'creating' || phase === 'running') && (
        <div className="card">
          <div className="flex flex-col items-center py-8">
            <Loader2 className="w-12 h-12 text-primary-500 animate-spin mb-4" />
            <p className="text-lg font-semibold text-primary-200 mb-2">
              {phase === 'creating' ? '正在创建任务...' : getStageLabel(taskStatus?.current_stage || '')}
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
                <p className="text-xs text-primary-500 mt-2 text-center">
                  预计耗时 1-3 分钟，请耐心等待...
                </p>
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
                  <p className="text-sm font-medium text-green-500">研究完成</p>
                  <p className="text-xs text-green-400 mt-1">
                    {result.total_tasks || 0} 个任务 | 置信度: {result.confidence ? `${(result.confidence * 100).toFixed(0)}%` : '-'}
                  </p>
                </div>
              </div>
              <div className="flex gap-3">
                <button onClick={handleReset} className="text-sm text-primary-400 hover:text-primary-200">新研究</button>
                {taskId && (
                  <button onClick={() => navigate(`/report/${taskId}`)} className="btn-primary flex items-center gap-2 text-sm">
                    <FileText className="w-4 h-4" /> 查看报告
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Answer */}
          {result.answer && (
            <div className="card">
              <h2 className="text-lg font-semibold text-primary-50 mb-3">分析结果</h2>
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
                <h3 className="text-lg font-semibold text-primary-50">关键发现</h3>
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
                <h3 className="text-lg font-semibold text-primary-50">建议</h3>
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
              <p className="text-xs text-primary-400 uppercase">任务数</p>
              <p className="text-2xl font-bold text-primary-50">{result.total_tasks || 0}</p>
            </div>
            <div className="card text-center">
              <CheckCircle className="w-5 h-5 text-green-500 mx-auto mb-2" />
              <p className="text-xs text-green-400 uppercase">成功</p>
              <p className="text-2xl font-bold text-green-500">{result.success_tasks || 0}</p>
            </div>
            <div className="card text-center">
              <Lightbulb className="w-5 h-5 text-yellow-500 mx-auto mb-2" />
              <p className="text-xs text-yellow-400 uppercase">置信度</p>
              <p className="text-2xl font-bold text-yellow-500">{result.confidence ? `${(result.confidence * 100).toFixed(0)}%` : '-'}</p>
            </div>
            <div className="card text-center">
              <Zap className="w-5 h-5 text-purple-500 mx-auto mb-2" />
              <p className="text-xs text-purple-400 uppercase">洞察</p>
              <p className="text-2xl font-bold text-purple-500">{result.reasoning_insights?.length || 0}</p>
            </div>
          </div>
        </div>
      )}

      {/* Idle State */}
      {phase === 'idle' && !error && (
        <div className="card text-center py-12">
          <Brain className="w-16 h-16 text-primary-400/20 mx-auto mb-4" />
          <p className="text-primary-400">输入研究问题，点击 Run Research 开始分析</p>
          <p className="text-xs text-primary-500 mt-2">AI 将自动规划、执行、推理并生成报告（约 1-3 分钟）</p>
        </div>
      )}
    </div>
  )
}
