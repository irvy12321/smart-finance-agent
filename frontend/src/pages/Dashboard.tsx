import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { 
  Search, 
  FileText, 
  Activity, 
  Clock,
  CheckCircle,
  AlertCircle,
  Plus,
  MessageSquare
} from 'lucide-react'
import { taskApi } from '../services/api'
import StockPriceCard from '../components/StockPriceCard'
import type { TaskListItem } from '../types/api'

export default function Dashboard() {
  const [tasks, setTasks] = useState<TaskListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await taskApi.list()
      setTasks(response.tasks || [])
    } catch (err: any) {
      setError(err.message || 'Failed to fetch tasks')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    
    const loadData = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await taskApi.list()
        if (!cancelled) setTasks(response.tasks || [])
      } catch (err: any) {
        if (!cancelled) setError(err.message || 'Failed to fetch tasks')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadData()
    const interval = setInterval(loadData, 10000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'running':
        return <Activity className="w-5 h-5 text-blue-500 animate-pulse" />
      case 'error':
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-500" />
      default:
        return <Clock className="w-5 h-5 text-yellow-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-success">COMPLETED</span>
      case 'running':
        return <span className="badge badge-running">RUNNING</span>
      case 'error':
      case 'failed':
        return <span className="badge badge-error">FAILED</span>
      default:
        return <span className="badge badge-pending">PENDING</span>
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary-50">Dashboard</h1>
          <p className="text-sm text-primary-400 mt-1">
            Smart Finance Research Platform
          </p>
        </div>
        <Link
          to="/research"
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Research
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider">
                Total Tasks
              </p>
              <p className="text-2xl font-bold text-primary-50">{tasks.length}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-green-400 uppercase tracking-wider">
                Completed
              </p>
              <p className="text-2xl font-bold text-green-500">
                {tasks.filter(t => t.status === 'completed').length}
              </p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
              <Activity className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider">
                Running
              </p>
              <p className="text-2xl font-bold text-blue-500">
                {tasks.filter(t => t.status === 'running').length}
              </p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-500/10 rounded-lg flex items-center justify-center">
              <Clock className="w-5 h-5 text-yellow-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-yellow-400 uppercase tracking-wider">
                Pending
              </p>
              <p className="text-2xl font-bold text-yellow-500">
                {tasks.filter(t => t.status === 'pending').length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 gap-4">
        <Link
          to="/research"
          className="card hover:border-primary-500/30 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
              <Search className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-sm font-semibold text-primary-200">New Research</p>
              <p className="text-xs text-primary-400">Start a comprehensive research task</p>
            </div>
          </div>
        </Link>
        <Link
          to="/chat"
          className="card hover:border-primary-500/30 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <p className="text-sm font-semibold text-primary-200">AI Chat</p>
              <p className="text-xs text-primary-400">Chat with the financial assistant</p>
            </div>
          </div>
        </Link>
      </div>

      {/* Stock Price Widget */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StockPriceCard />
        
        {/* Recent Tasks */}
        <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-primary-50">Recent Tasks</h2>
          <button 
            onClick={fetchTasks}
            className="text-sm text-primary-400 hover:text-primary-200 transition-colors"
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <Activity className="w-8 h-8 text-primary-500 animate-spin mx-auto mb-4" />
              <p className="text-primary-400">Loading tasks...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-4" />
              <p className="text-red-500">{error}</p>
              <button 
                onClick={fetchTasks}
                className="mt-2 text-sm text-primary-400 hover:text-primary-200"
              >
                Try again
              </button>
            </div>
          </div>
        ) : tasks.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <Search className="w-8 h-8 text-primary-400 mx-auto mb-4" />
              <p className="text-primary-400">No tasks yet</p>
              <p className="text-xs text-primary-500 mt-1">
                Create a new research task to get started
              </p>
              <Link
                to="/research"
                className="mt-4 inline-flex items-center gap-2 text-sm text-primary-500 hover:text-primary-300"
              >
                <Plus className="w-4 h-4" />
                New Research
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.slice(0, 10).map((task) => (
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
                      ID: {task.task_id} • Created: {formatDate(task.created_at)}
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
                      View Report
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      </div>
    </div>
  )
}
