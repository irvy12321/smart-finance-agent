import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Clock, CheckCircle, Loader2, AlertCircle, ExternalLink } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { taskApi } from '../../services/api'
import { useAuth } from '../../contexts/AuthContext'
import type { TaskListItem } from '../../types/api'

export default function RecentTasks() {
  const { t } = useTranslation()
  const { hasAnyRole } = useAuth()
  const [tasks, setTasks] = useState<TaskListItem[]>([])
  const [loading, setLoading] = useState(true)

  const fetchTasks = useCallback(async () => {
    if (!hasAnyRole(['admin', 'analyst'])) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      const data = await taskApi.list()
      setTasks((data.tasks || []).slice(0, 5))
    } catch (err) {
      console.warn('Failed to fetch tasks:', err)
    } finally {
      setLoading(false)
    }
  }, [hasAnyRole])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  const statusConfig: Record<string, { icon: LucideIcon; color: string; bg: string; label: string; animate: string }> = {
    pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-500/10', label: t('dashboard.pendingTasks'), animate: '' },
    running: { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-500/10', label: t('dashboard.runningTasks'), animate: 'animate-spin' },
    completed: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10', label: t('dashboard.completedTasks'), animate: '' },
    failed: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-500/10', label: t('dashboard.failedTasks'), animate: '' },
  }

  const formatTime = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      const now = new Date()
      const diff = now.getTime() - date.getTime()
      const minutes = Math.floor(diff / 60000)
      const hours = Math.floor(diff / 3600000)
      const days = Math.floor(diff / 86400000)

      if (minutes < 1) return t('common.justNow')
      if (minutes < 60) return `${minutes}m ${t('common.ago')}`
      if (hours < 24) return `${hours}h ${t('common.ago')}`
      return `${days}d ${t('common.ago')}`
    } catch {
      return dateStr
    }
  }

  if (loading) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden h-full min-h-[18rem] flex flex-col">
        <div className="flex items-center justify-between px-3 py-2 border-b border-dark-border">
          <span className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('dashboard.recentTasks')}</span>
        </div>
        <div className="flex-1 p-8 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
        </div>
      </div>
    )
  }

  if (!hasAnyRole(['admin', 'analyst'])) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden h-full min-h-[18rem] flex flex-col">
        <div className="flex items-center justify-between px-3 py-2 border-b border-dark-border">
          <span className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('dashboard.recentTasks')}</span>
        </div>
        <div className="flex-1 p-4 text-center text-xs text-primary-500">
          {t('error.forbidden')}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden h-full min-h-[18rem] flex flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-dark-border">
        <span className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('dashboard.recentTasks')}</span>
        <Link to="/research" className="text-xs text-primary-500 hover:text-primary-300 flex items-center gap-1">
          {t('common.viewAll')} <ExternalLink className="w-3 h-3" />
        </Link>
      </div>
      <div className="min-h-0 flex-1 divide-y divide-dark-border overflow-auto">
        {tasks.length === 0 ? (
          <div className="p-4 text-center text-xs text-primary-500">
            {t('dashboard.noTasksYet')}
          </div>
        ) : (
          tasks.map((task) => {
            const config = statusConfig[task.status] || statusConfig.pending
            const Icon = config.icon
            return (
              <Link
                key={task.task_id}
                to={task.status === 'completed' ? `/report/${task.task_id}` : `/workflow/${task.task_id}`}
                className="flex items-center gap-3 px-3 py-2.5 hover:bg-dark-bg/50 transition-colors"
              >
                <div className={`w-6 h-6 ${config.bg} rounded-full flex items-center justify-center flex-shrink-0`}>
                  <Icon className={`w-3.5 h-3.5 ${config.color} ${config.animate}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-primary-200 truncate">{task.query}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={`text-xs ${config.color}`}>{config.label}</span>
                    <span className="text-xs text-primary-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatTime(task.created_at)}
                    </span>
                  </div>
                </div>
              </Link>
            )
          })
        )}
      </div>
    </div>
  )
}
