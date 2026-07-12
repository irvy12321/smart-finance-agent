import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Activity,
  Server,
  Clock,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Loader2,
  Zap,
  FileText,
  Wifi
} from 'lucide-react'
import { systemApi, taskApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import SimpleChart from '../components/SimpleChart'
import type {
  SystemStatusResponse,
  SystemMetricsResponse,
  AgentStatusResponse,
  TaskListItem
} from '../types/api'

export default function SystemOverview() {
  const { t } = useTranslation()
  const { hasAnyRole } = useAuth()
  const [systemStatus, setSystemStatus] = useState<SystemStatusResponse | null>(null)
  const [metrics, setMetrics] = useState<SystemMetricsResponse | null>(null)
  const [agentStatus, setAgentStatus] = useState<AgentStatusResponse | null>(null)
  const [tasks, setTasks] = useState<TaskListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(false)

  const fetchSystemData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch system data
      const [statusRes, metricsRes, agentsRes] = await Promise.all([
        systemApi.getStatus(),
        systemApi.getMetrics(),
        systemApi.getAgentStatus(),
      ])

      setSystemStatus(statusRes)
      setMetrics(metricsRes)
      setAgentStatus(agentsRes)

      // Only fetch tasks if user has permission
      if (hasAnyRole(['admin', 'analyst'])) {
        try {
          const tasksRes = await taskApi.list()
          setTasks(tasksRes.tasks || [])
        } catch (taskErr) {
          // Ignore task list errors (e.g., 403 Forbidden)
          console.warn('Failed to fetch tasks:', taskErr)
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && (err.name === 'AbortError' || (err as { code?: string }).code === 'ERR_CANCELED')) return
      setError(err instanceof Error ? err.message : t('error.serverError'))
    } finally {
      setLoading(false)
    }
  }, [t, hasAnyRole])

  const handleRefresh = useCallback(() => {
    fetchSystemData()
  }, [fetchSystemData])

  useEffect(() => {
    fetchSystemData()
  }, [fetchSystemData])

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null
    if (autoRefresh) {
      interval = setInterval(() => {
        fetchSystemData()
      }, 5000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [autoRefresh, fetchSystemData])

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    return `${hours}h ${minutes}m ${secs}s`
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'running':
        return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />
      default:
        return <Clock className="w-4 h-4 text-yellow-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-success">{t('dashboard.completedTasks')}</span>
      case 'running':
        return <span className="badge badge-running">{t('dashboard.runningTasks')}</span>
      case 'failed':
        return <span className="badge badge-error">{t('dashboard.failedTasks')}</span>
      default:
        return <span className="badge badge-pending">{t('dashboard.pendingTasks')}</span>
    }
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return date.toLocaleString()
    } catch {
      return dateString
    }
  }

  const taskStatusData = [
    { label: t('dashboard.completedTasks'), value: metrics?.completed_tasks || 0, color: '#10b981' },
    { label: t('dashboard.runningTasks'), value: metrics?.running_tasks || 0, color: '#5b9dff' },
    { label: t('dashboard.pendingTasks'), value: metrics?.pending_tasks || 0, color: '#f59e0b' },
    { label: t('dashboard.failedTasks'), value: metrics?.failed_tasks || 0, color: '#ef4444' },
  ]

  const agentPerformanceData = agentStatus ? Object.entries(agentStatus).map(([name, status]: [string, { avg_latency_ms?: number }]) => ({
    label: name.charAt(0).toUpperCase() + name.slice(1),
    value: status.avg_latency_ms || 0,
    color: '#5b9dff',
  })) : []

  return (
    <div className="app-page app-page-wide space-y-6">
      {/* Loading State */}
      {loading && !systemStatus && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
            <p className="text-primary-400">{t('common.loading')}</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="card border-red-500/30">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <div>
              <p className="text-sm font-medium text-red-500">{t('error.serverError')}</p>
              <p className="text-xs text-red-400 mt-1">{error}</p>
            </div>
          </div>
          <button
            onClick={handleRefresh}
            className="mt-3 text-sm text-red-500 hover:text-red-400"
          >
            {t('error.tryAgain')}
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary-50">{t('system.title')}</h1>
          <p className="text-sm text-primary-400 mt-1">
            {t('dashboard.systemOverview')}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors ${
              autoRefresh
                ? 'bg-green-500/10 text-green-500 border border-green-500/20'
                : 'text-primary-400 hover:text-primary-200 border border-dark-border'
            }`}
          >
            <Wifi className={`w-4 h-4 ${autoRefresh ? 'animate-pulse' : ''}`} />
            {autoRefresh ? 'Live' : t('common.refresh')}
          </button>
          <button
            onClick={handleRefresh}
            className="flex items-center gap-2 text-sm text-primary-400 hover:text-primary-200 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            {t('common.refresh')}
          </button>
        </div>
      </div>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center">
              <Server className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider">
                {t('system.status')}
              </p>
              <p className="text-lg font-bold text-green-500">
                {systemStatus?.status === 'healthy' ? t('system.healthy') : t('system.unhealthy')}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
              <Clock className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider">
                {t('system.uptime')}
              </p>
              <p className="text-lg font-bold text-blue-500">
                {systemStatus?.uptime ? formatUptime(systemStatus.uptime) : '-'}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-dark-hover rounded-lg flex items-center justify-center">
              <Activity className="w-5 h-5 text-primary-300" />
            </div>
            <div>
              <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider">
                {t('system.totalRequests')}
              </p>
              <p className="text-lg font-bold text-primary-50">
                {metrics?.total_requests || 0}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider">
                {t('system.successRate')}
              </p>
              <p className="text-lg font-bold text-green-500">
                {metrics?.success_rate ? `${metrics.success_rate.toFixed(1)}%` : '100%'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SimpleChart
          data={taskStatusData}
          type="bar"
          title={t('dashboard.totalTasks')}
          height={200}
        />

        <SimpleChart
          data={agentPerformanceData}
          type="bar"
          title={t('system.avgLatency')}
          height={200}
        />
      </div>

      {/* Agent Status */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-primary-50">{t('system.agents')}</h2>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full" />
            <span className="text-xs text-primary-400">{t('system.ready')}</span>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {agentStatus && Object.entries(agentStatus).map(([agent, status]: [string, { status: string; total_calls: number; avg_latency_ms: number; success_rate: number }]) => (
            <div key={agent} className="p-4 bg-dark-bg rounded-lg border border-dark-border hover:border-primary-500/30 transition-colors">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    status.status === 'ready' ? 'bg-green-500' : 'bg-yellow-500'
                  }`} />
                  <h3 className="text-sm font-semibold text-primary-200 capitalize">
                    {agent.replace('_', ' ')}
                  </h3>
                </div>
                <Zap className="w-4 h-4 text-primary-400" />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-xs text-primary-400">{t('system.status')}</span>
                  <span className={`text-xs font-medium ${
                    status.status === 'ready' ? 'text-green-500' : 'text-yellow-500'
                  }`}>
                    {status.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-primary-400">{t('system.totalRequests')}</span>
                  <span className="text-xs font-medium text-primary-200">
                    {status.total_calls || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-primary-400">{t('system.avgLatency')}</span>
                  <span className="text-xs font-medium text-primary-200">
                    {status.avg_latency_ms ? `${status.avg_latency_ms.toFixed(0)}ms` : '-'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-primary-400">{t('system.successRate')}</span>
                  <span className="text-xs font-medium text-primary-200">
                    {status.success_rate ? `${status.success_rate.toFixed(0)}%` : '100%'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Task Statistics */}
      <div className="card">
        <h2 className="text-lg font-semibold text-primary-50 mb-6">{t('dashboard.totalTasks')}</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border text-center hover:border-primary-500/30 transition-colors">
            <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-2">
              {t('dashboard.totalTasks')}
            </p>
            <p className="text-3xl font-bold text-primary-50">
              {metrics?.total_tasks || 0}
            </p>
          </div>
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border text-center hover:border-green-500/30 transition-colors">
            <p className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-2">
              {t('dashboard.completedTasks')}
            </p>
            <p className="text-3xl font-bold text-green-500">
              {metrics?.completed_tasks || 0}
            </p>
          </div>
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border text-center hover:border-blue-500/30 transition-colors">
            <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-2">
              {t('dashboard.runningTasks')}
            </p>
            <p className="text-3xl font-bold text-blue-500">
              {metrics?.running_tasks || 0}
            </p>
          </div>
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border text-center hover:border-yellow-500/30 transition-colors">
            <p className="text-xs font-semibold text-yellow-400 uppercase tracking-wider mb-2">
              {t('dashboard.pendingTasks')}
            </p>
            <p className="text-3xl font-bold text-yellow-500">
              {metrics?.pending_tasks || 0}
            </p>
          </div>
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border text-center hover:border-red-500/30 transition-colors">
            <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">
              {t('dashboard.failedTasks')}
            </p>
            <p className="text-3xl font-bold text-red-500">
              {metrics?.failed_tasks || 0}
            </p>
          </div>
        </div>
      </div>

      {/* Recent Tasks */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-primary-50">{t('dashboard.recentTasks')}</h2>
          <Link
            to="/"
            className="text-sm text-primary-500 hover:text-primary-300 transition-colors"
          >
            {t('common.viewAll')}
          </Link>
        </div>

        {tasks.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="w-8 h-8 text-primary-400 mx-auto mb-2" />
            <p className="text-sm text-primary-400">{t('dashboard.noTasksYet')}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.slice(0, 5).map((task) => (
              <div
                key={task.task_id}
                className="flex items-center justify-between p-4 bg-dark-bg rounded-lg border border-dark-border hover:border-primary-500/30 transition-colors"
              >
                <div className="flex items-center gap-4">
                  {getStatusIcon(task.status)}
                  <div>
                    <p className="text-sm font-medium text-primary-200 line-clamp-1">
                      {task.query}
                    </p>
                    <p className="text-xs text-primary-400 mt-1">
                      {t('common.id')}: {task.task_id} • {formatDate(task.created_at)}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {getStatusBadge(task.status)}
                  {task.status === 'completed' && (
                    <Link
                      to={`/report/${task.task_id}`}
                      className="text-sm text-primary-500 hover:text-primary-300 transition-colors"
                    >
                      {t('dashboard.viewReport')}
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
