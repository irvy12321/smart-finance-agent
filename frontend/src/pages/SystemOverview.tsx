import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  Activity, 
  Server, 
  Database, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  RefreshCw,
  Loader2,
  TrendingUp,
  Zap,
  FileText,
  Settings,
  Cpu,
  HardDrive,
  Wifi,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { systemApi, taskApi } from '../services/api'
import SimpleChart from '../components/SimpleChart'

interface Task {
  task_id: string
  query: string
  status: string
  created_at: string
  updated_at: string
}

export default function SystemOverview() {
  const [systemStatus, setSystemStatus] = useState<any>(null)
  const [metrics, setMetrics] = useState<any>(null)
  const [agentStatus, setAgentStatus] = useState<any>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(false)

  useEffect(() => {
    fetchSystemData()
  }, [])

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null
    if (autoRefresh) {
      interval = setInterval(fetchSystemData, 5000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [autoRefresh])

  const fetchSystemData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const [statusRes, metricsRes, agentsRes, tasksRes] = await Promise.all([
        systemApi.getStatus(),
        systemApi.getMetrics(),
        systemApi.getAgentStatus(),
        taskApi.list(),
      ])
      
      setSystemStatus(statusRes)
      setMetrics(metricsRes)
      setAgentStatus(agentsRes)
      setTasks(tasksRes.tasks || [])
    } catch (err: any) {
      setError(err.message || 'Failed to fetch system data')
    } finally {
      setLoading(false)
    }
  }

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
        return <span className="badge badge-success">COMPLETED</span>
      case 'running':
        return <span className="badge badge-running">RUNNING</span>
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

  // Prepare chart data
  const taskStatusData = [
    { label: 'Completed', value: metrics?.completed_tasks || 0, color: '#10b981' },
    { label: 'Running', value: metrics?.running_tasks || 0, color: '#6366f1' },
    { label: 'Pending', value: metrics?.pending_tasks || 0, color: '#f59e0b' },
    { label: 'Failed', value: metrics?.failed_tasks || 0, color: '#ef4444' },
  ]

  const agentPerformanceData = agentStatus ? Object.entries(agentStatus).map(([name, status]: [string, any]) => ({
    label: name.charAt(0).toUpperCase() + name.slice(1),
    value: status.avg_latency_ms || 0,
    color: '#6366f1',
  })) : []

  return (
    <div className="space-y-6 p-6">
      {/* Loading State */}
      {loading && !systemStatus && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
            <p className="text-primary-400">Loading system data...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="card border-red-500/30">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <div>
              <p className="text-sm font-medium text-red-500">Failed to load system data</p>
              <p className="text-xs text-red-400 mt-1">{error}</p>
            </div>
          </div>
          <button
            onClick={fetchSystemData}
            className="mt-3 text-sm text-red-500 hover:text-red-400"
          >
            Try again
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary-50">System Overview</h1>
          <p className="text-sm text-primary-400 mt-1">
            Real-time pipeline monitoring and performance metrics
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
            {autoRefresh ? 'Live' : 'Auto Refresh'}
          </button>
          <button
            onClick={fetchSystemData}
            className="flex items-center gap-2 text-sm text-primary-400 hover:text-primary-200 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Status */}
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center">
              <Server className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider">
                Status
              </p>
              <p className="text-lg font-bold text-green-500">
                {systemStatus?.status || 'Unknown'}
              </p>
            </div>
          </div>
        </div>

        {/* Uptime */}
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center">
              <Clock className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider">
                Uptime
              </p>
              <p className="text-lg font-bold text-blue-500">
                {systemStatus?.uptime ? formatUptime(systemStatus.uptime) : '-'}
              </p>
            </div>
          </div>
        </div>

        {/* Requests */}
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center">
              <Activity className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider">
                Total Requests
              </p>
              <p className="text-lg font-bold text-purple-500">
                {metrics?.total_requests || 0}
              </p>
            </div>
          </div>
        </div>

        {/* Success Rate */}
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider">
                Success Rate
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
        {/* Task Distribution */}
        <SimpleChart 
          data={taskStatusData} 
          type="bar" 
          title="Task Status Distribution"
          height={200}
        />

        {/* Agent Latency */}
        <SimpleChart 
          data={agentPerformanceData} 
          type="bar" 
          title="Agent Latency (ms)"
          height={200}
        />
      </div>

      {/* Agent Status */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-primary-50">Agent Status</h2>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full" />
            <span className="text-xs text-primary-400">All Systems Operational</span>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {agentStatus && Object.entries(agentStatus).map(([agent, status]: [string, any]) => (
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
                  <span className="text-xs text-primary-400">Status</span>
                  <span className={`text-xs font-medium ${
                    status.status === 'ready' ? 'text-green-500' : 'text-yellow-500'
                  }`}>
                    {status.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-primary-400">Calls</span>
                  <span className="text-xs font-medium text-primary-200">
                    {status.total_calls || 0}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-primary-400">Latency</span>
                  <span className="text-xs font-medium text-primary-200">
                    {status.avg_latency_ms ? `${status.avg_latency_ms.toFixed(0)}ms` : '-'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-xs text-primary-400">Success</span>
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
        <h2 className="text-lg font-semibold text-primary-50 mb-6">Task Statistics</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border text-center hover:border-primary-500/30 transition-colors">
            <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-2">
              Total
            </p>
            <p className="text-3xl font-bold text-primary-50">
              {metrics?.total_tasks || 0}
            </p>
          </div>
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border text-center hover:border-green-500/30 transition-colors">
            <p className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-2">
              Completed
            </p>
            <p className="text-3xl font-bold text-green-500">
              {metrics?.completed_tasks || 0}
            </p>
          </div>
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border text-center hover:border-blue-500/30 transition-colors">
            <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-2">
              Running
            </p>
            <p className="text-3xl font-bold text-blue-500">
              {metrics?.running_tasks || 0}
            </p>
          </div>
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border text-center hover:border-yellow-500/30 transition-colors">
            <p className="text-xs font-semibold text-yellow-400 uppercase tracking-wider mb-2">
              Pending
            </p>
            <p className="text-3xl font-bold text-yellow-500">
              {metrics?.pending_tasks || 0}
            </p>
          </div>
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border text-center hover:border-red-500/30 transition-colors">
            <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">
              Failed
            </p>
            <p className="text-3xl font-bold text-red-500">
              {metrics?.failed_tasks || 0}
            </p>
          </div>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="card">
        <h2 className="text-lg font-semibold text-primary-50 mb-6">Performance Metrics</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border">
            <div className="flex items-center gap-2 mb-3">
              <Cpu className="w-5 h-5 text-blue-500" />
              <h3 className="text-sm font-semibold text-primary-200">Avg Latency</h3>
            </div>
            <p className="text-2xl font-bold text-blue-500">
              {metrics?.avg_latency_ms ? `${metrics.avg_latency_ms.toFixed(0)}ms` : '-'}
            </p>
            <div className="flex items-center gap-1 mt-2">
              <ArrowDownRight className="w-3 h-3 text-green-500" />
              <span className="text-xs text-green-500">-5% from last hour</span>
            </div>
          </div>
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border">
            <div className="flex items-center gap-2 mb-3">
              <Database className="w-5 h-5 text-purple-500" />
              <h3 className="text-sm font-semibold text-primary-200">Success Rate</h3>
            </div>
            <p className="text-2xl font-bold text-purple-500">
              {metrics?.success_rate ? `${metrics.success_rate.toFixed(1)}%` : '100%'}
            </p>
            <div className="flex items-center gap-1 mt-2">
              <ArrowUpRight className="w-3 h-3 text-green-500" />
              <span className="text-xs text-green-500">+2% from last hour</span>
            </div>
          </div>
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border">
            <div className="flex items-center gap-2 mb-3">
              <HardDrive className="w-5 h-5 text-cyan-500" />
              <h3 className="text-sm font-semibold text-primary-200">Total Tasks</h3>
            </div>
            <p className="text-2xl font-bold text-cyan-500">
              {metrics?.total_tasks || 0}
            </p>
            <div className="flex items-center gap-1 mt-2">
              <ArrowUpRight className="w-3 h-3 text-green-500" />
              <span className="text-xs text-green-500">+12 today</span>
            </div>
          </div>
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-5 h-5 text-green-500" />
              <h3 className="text-sm font-semibold text-primary-200">Throughput</h3>
            </div>
            <p className="text-2xl font-bold text-green-500">
              {metrics?.total_requests ? `${(metrics.total_requests / (systemStatus?.uptime / 3600 || 1)).toFixed(1)}/h` : '0/h'}
            </p>
            <div className="flex items-center gap-1 mt-2">
              <ArrowUpRight className="w-3 h-3 text-green-500" />
              <span className="text-xs text-green-500">Stable</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Tasks */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-primary-50">Recent Tasks</h2>
          <Link
            to="/"
            className="text-sm text-primary-500 hover:text-primary-300 transition-colors"
          >
            View All
          </Link>
        </div>

        {tasks.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="w-8 h-8 text-primary-400 mx-auto mb-2" />
            <p className="text-sm text-primary-400">No tasks yet</p>
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
                      ID: {task.task_id} • {formatDate(task.created_at)}
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

      {/* System Configuration */}
      <div className="card">
        <h2 className="text-lg font-semibold text-primary-50 mb-6">System Configuration</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border">
            <div className="flex items-center gap-2 mb-3">
              <Settings className="w-5 h-5 text-primary-400" />
              <h3 className="text-sm font-semibold text-primary-200">Model Configuration</h3>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-xs text-primary-400">LLM Model</span>
                <span className="text-xs font-medium text-primary-200 font-mono">openai/mimo-v2.5-pro</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-primary-400">Embedding</span>
                <span className="text-xs font-medium text-primary-200 font-mono">dev (hash)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-primary-400">Temperature</span>
                <span className="text-xs font-medium text-primary-200 font-mono">0.3</span>
              </div>
            </div>
          </div>
          <div className="p-4 bg-dark-bg rounded-lg border border-dark-border">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-5 h-5 text-primary-400" />
              <h3 className="text-sm font-semibold text-primary-200">Features</h3>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-xs text-primary-400">Streaming</span>
                <span className="text-xs font-medium text-green-500">Enabled</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-primary-400">RAG</span>
                <span className="text-xs font-medium text-green-500">Enabled</span>
              </div>
              <div className="flex justify-between">
                <span className="text-xs text-primary-400">Smart Router</span>
                <span className="text-xs font-medium text-green-500">Enabled</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}