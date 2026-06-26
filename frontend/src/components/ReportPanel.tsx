import {
  FileText,
  TrendingUp,
  AlertTriangle,
  Target,
  CheckCircle,
  Clock,
  BarChart3,
  PieChart
} from 'lucide-react'
import SimpleChart from './SimpleChart'

interface ReportPanelProps {
  report: {
    report_title?: string
    summary?: string
    key_findings?: string[]
    risk_factors?: Array<{ factor: string; severity: string; description: string }>
    market_trends?: string[]
    recommendations?: string[]
    confidence?: number
    total_tasks?: number
    success_tasks?: number
    failed_tasks?: number
    elapsed?: number
    chart_specs?: Array<{
      chart_type: string
      title: string
      x_label: string
      y_label: string
      data: Array<{ label: string; value: number }>
    }>
  } | null
  loading?: boolean
}

export default function ReportPanel({ report, loading }: ReportPanelProps) {
  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="w-12 h-12 bg-primary-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <FileText className="w-6 h-6 text-primary-500 animate-pulse" />
            </div>
            <p className="text-primary-400">Loading report...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="w-12 h-12 bg-dark-border rounded-full flex items-center justify-center mx-auto mb-4">
              <FileText className="w-6 h-6 text-primary-400" />
            </div>
            <p className="text-primary-400">No report available</p>
            <p className="text-xs text-primary-500 mt-1">Run a research query to generate a report</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Report Header */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-primary-50">
              {report.report_title || 'Financial Research Report'}
            </h2>
            <p className="text-sm text-primary-400 mt-1">
              AI-Powered Multi-Agent Financial Analysis
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 px-3 py-1.5 bg-green-500/10 rounded-full">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="text-xs font-semibold text-green-500">Complete</span>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4">
          <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
            <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-1">
              Tasks
            </p>
            <p className="text-2xl font-bold text-primary-50">{report.total_tasks || 0}</p>
          </div>
          <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
            <p className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-1">
              Success
            </p>
            <p className="text-2xl font-bold text-green-500">{report.success_tasks || 0}</p>
          </div>
          <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
            <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-1">
              Failed
            </p>
            <p className="text-2xl font-bold text-red-500">{report.failed_tasks || 0}</p>
          </div>
          <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
            <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-1">
              Confidence
            </p>
            <p className="text-2xl font-bold text-primary-50">
              {report.confidence ? `${(report.confidence * 100).toFixed(1)}%` : '-'}
            </p>
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      {report.summary && (
        <div className="card">
          <h3 className="text-lg font-semibold text-primary-50 mb-3">Executive Summary</h3>
          <p className="text-primary-200 leading-relaxed">{report.summary}</p>
        </div>
      )}

      {/* Key Findings */}
      {report.key_findings && report.key_findings.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-blue-500" />
            <h3 className="text-lg font-semibold text-primary-50">Key Findings</h3>
          </div>
          <div className="space-y-3">
            {report.key_findings.map((finding, index) => (
              <div key={index} className="flex items-start gap-3 p-3 bg-dark-bg rounded-lg border border-dark-border">
                <div className="w-6 h-6 bg-blue-500/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-blue-500">{index + 1}</span>
                </div>
                <p className="text-sm text-primary-200">{finding}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk Factors */}
      {report.risk_factors && report.risk_factors.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h3 className="text-lg font-semibold text-primary-50">Risk Factors</h3>
          </div>
          <div className="space-y-3">
            {report.risk_factors.map((risk, index) => (
              <div key={index} className="p-3 bg-dark-bg rounded-lg border border-dark-border">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-primary-200">{risk.factor}</p>
                  <span className={`badge ${
                    risk.severity === 'high' ? 'badge-error' :
                    risk.severity === 'medium' ? 'badge-pending' : 'badge-success'
                  }`}>
                    {risk.severity.toUpperCase()}
                  </span>
                </div>
                <p className="text-xs text-primary-400">{risk.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Market Trends */}
      {report.market_trends && report.market_trends.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-primary-400" />
            <h3 className="text-lg font-semibold text-primary-50">Market Trends</h3>
          </div>
          <div className="space-y-2">
            {report.market_trends.map((trend, index) => (
              <div key={index} className="flex items-center gap-2 p-2 bg-dark-bg rounded-lg border border-dark-border">
                <div className="w-2 h-2 bg-primary-500 rounded-full" />
                <p className="text-sm text-primary-200">{trend}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Charts */}
      {report.chart_specs && report.chart_specs.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <PieChart className="w-5 h-5 text-cyan-500" />
            <h3 className="text-lg font-semibold text-primary-50">Data Visualizations</h3>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {report.chart_specs.map((chart, index) => (
              <SimpleChart
                key={index}
                data={chart.data}
                type={chart.chart_type === 'line' ? 'line' : 'bar'}
                title={chart.title}
                height={200}
              />
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {report.recommendations && report.recommendations.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Target className="w-5 h-5 text-green-500" />
            <h3 className="text-lg font-semibold text-primary-50">Recommendations</h3>
          </div>
          <div className="space-y-3">
            {report.recommendations.map((rec, index) => (
              <div key={index} className="flex items-start gap-3 p-3 bg-dark-bg rounded-lg border border-dark-border">
                <div className="w-6 h-6 bg-green-500/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <CheckCircle className="w-4 h-4 text-green-500" />
                </div>
                <p className="text-sm text-primary-200">{rec}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Execution Summary */}
      <div className="card">
        <h3 className="text-lg font-semibold text-primary-50 mb-4">Execution Summary</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3 p-3 bg-dark-bg rounded-lg border border-dark-border">
            <Clock className="w-5 h-5 text-primary-400" />
            <div>
              <p className="text-xs text-primary-400">Duration</p>
              <p className="text-sm font-semibold text-primary-200">
                {report.elapsed ? `${report.elapsed.toFixed(1)}s` : '-'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-dark-bg rounded-lg border border-dark-border">
            <BarChart3 className="w-5 h-5 text-primary-400" />
            <div>
              <p className="text-xs text-primary-400">Success Rate</p>
              <p className="text-sm font-semibold text-primary-200">
                {report.total_tasks ? `${((report.success_tasks || 0) / report.total_tasks * 100).toFixed(1)}%` : '-'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
