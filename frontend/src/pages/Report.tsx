import { useState, useEffect, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, RefreshCw, Download, Trash2, AlertCircle, Loader2, TrendingUp, AlertTriangle, Target, CheckCircle, Clock, BarChart3, Brain } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import { reportApi } from '../services/api'
import LazyChart from '../components/LazyChart'
import type { ReportResponse } from '../types/api'

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
  thead: ({children}: { children?: React.ReactNode }) => <thead className="bg-dark-sub">{children}</thead>,
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

export default function Report() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { taskId } = useParams<{ taskId: string }>()
  const [report, setReport] = useState<ReportResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  const fetchReport = useCallback(async (id: string) => {
    try {
      setLoading(true)
      setError(null)
      setReport(null)
      const data = await reportApi.get(id)
      setReport(data)
    } catch (err: unknown) {
      if (err instanceof Error && (err.name === 'AbortError' || (err as { code?: string }).code === 'ERR_CANCELED')) return
      setError(err instanceof Error ? err.message : t('error.serverError'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    if (taskId) fetchReport(taskId)
  }, [taskId, fetchReport])

  const handleRefresh = () => { if (taskId) fetchReport(taskId) }

  const handleDelete = async () => {
    if (!taskId || !confirm(t('research.confirmDelete'))) return
    try {
      setDeleting(true)
      // Clear from localStorage
      localStorage.removeItem('research_state')
      navigate('/')
    } catch (err) {
      console.error('Delete failed:', err)
    } finally {
      setDeleting(false)
    }
  }

  const handleDownload = () => {
    if (!report) return
    const content = `# ${report.report_title || t('report.title')}

## ${t('report.summary')}
${report.summary || t('report.noReport')}

## ${t('report.keyFindings')}
${report.key_findings?.map((f: string, i: number) => `${i + 1}. ${f}`).join('\n') || t('report.noReport')}

## ${t('report.riskFactors')}
${report.risk_factors?.map((r: { factor: string; severity: string; description: string }) => `- **${r.factor}** [${r.severity}]: ${r.description}`).join('\n') || t('report.noReport')}

## ${t('report.marketTrends')}
${report.market_trends?.map((t: string) => `- ${t}`).join('\n') || t('report.noReport')}

## ${t('report.recommendations')}
${report.recommendations?.map((r: string, i: number) => `${i + 1}. ${r}`).join('\n') || t('report.noReport')}

---
Generated by Smart Finance Agent
${t('research.priority')}: ${report.confidence ? `${(report.confidence * 100).toFixed(1)}%` : 'N/A'}
`
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report-${taskId}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="app-page app-page-readable space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/" className="flex items-center gap-2 px-3 py-2 text-sm text-primary-400 hover:text-primary-200 hover:bg-primary-500/10 rounded-lg transition-all duration-200">
            <ArrowLeft className="w-4 h-4" /> {t('common.back')}
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-primary-50">{t('report.title')}</h1>
            <p className="text-sm text-primary-400 mt-1">{t('common.id')}: {taskId}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleRefresh} className="flex items-center gap-2 px-3 py-2 text-sm text-primary-400 hover:text-primary-200 hover:bg-primary-500/10 rounded-lg transition-all duration-200">
            <RefreshCw className="w-4 h-4" /> {t('common.refresh')}
          </button>
          <button onClick={handleDownload} disabled={!report} className="flex items-center gap-2 px-3 py-2 text-sm text-primary-400 hover:text-primary-200 hover:bg-primary-500/10 rounded-lg transition-all duration-200 disabled:opacity-50">
            <Download className="w-4 h-4" /> {t('report.download')}
          </button>
          <button onClick={handleDelete} disabled={deleting} className="flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-all duration-200 disabled:opacity-50">
            {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />} {t('common.delete')}
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
          <button onClick={handleRefresh} className="mt-3 text-sm text-red-500 hover:text-red-400">{t('error.tryAgain')}</button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="card">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-primary-500 animate-spin mr-3" />
            <p className="text-primary-400">{t('report.loadingReport')}</p>
          </div>
        </div>
      )}

      {/* Report Content */}
      {!loading && report && <ReportContent report={report} t={t} />}
    </div>
  )
}

function ReportContent({ report, t }: { report: ReportResponse, t: (key: string) => string }) {
  return (
    <>
      {/* Title & Stats */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-primary-50">{report.report_title || t('report.title')}</h2>
            <p className="text-sm text-primary-400 mt-1">Smart Finance Agent</p>
          </div>
          <div className="flex items-center gap-1 px-3 py-1.5 bg-green-500/10 rounded-full">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span className="text-xs font-semibold text-green-500">{t('research.completed')}</span>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-4">
          <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
            <p className="text-xs text-primary-400 uppercase mb-1">{t('dashboard.totalTasks')}</p>
            <p className="text-2xl font-bold text-primary-50">{report.total_tasks || 0}</p>
          </div>
          <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
            <p className="text-xs text-green-400 uppercase mb-1">{t('dashboard.completedTasks')}</p>
            <p className="text-2xl font-bold text-green-500">{report.success_tasks || 0}</p>
          </div>
          <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
            <p className="text-xs text-red-400 uppercase mb-1">{t('dashboard.failedTasks')}</p>
            <p className="text-2xl font-bold text-red-500">{report.failed_tasks || 0}</p>
          </div>
          <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
            <p className="text-xs text-primary-400 uppercase mb-1">{t('research.priority')}</p>
            <p className="text-2xl font-bold text-primary-50">{report.confidence ? `${(report.confidence * 100).toFixed(1)}%` : '-'}</p>
          </div>
        </div>
      </div>

      {/* Answer - Markdown Rendering */}
      {report.answer && (
        <div className="card">
          <h3 className="text-lg font-semibold text-primary-50 mb-3">
            <Brain className="w-5 h-5 inline mr-2 text-blue-500" />
            {t('research.results')}
          </h3>
          <div className="bg-dark-bg rounded-lg p-4 border border-dark-border max-h-[600px] overflow-y-auto">
            <ReactMarkdown rehypePlugins={[rehypeSanitize]} components={markdownComponents}>
              {report.answer}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {/* Key Findings */}
      {report.key_findings && report.key_findings.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-blue-500" />
            <h3 className="text-lg font-semibold text-primary-50">{t('report.keyFindings')}</h3>
          </div>
          <div className="space-y-3">
            {report.key_findings.map((finding: string, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-dark-bg rounded-lg border border-dark-border">
                <div className="w-6 h-6 bg-blue-500/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-blue-500">{i + 1}</span>
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
            <h3 className="text-lg font-semibold text-primary-50">{t('report.riskFactors')}</h3>
          </div>
          <div className="space-y-3">
            {report.risk_factors.map((risk: { factor: string; severity: string; description: string }, i: number) => (
              <div key={i} className="p-3 bg-dark-bg rounded-lg border border-dark-border">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-primary-200">{risk.factor}</p>
                  <span className={`badge ${risk.severity === 'high' ? 'badge-error' : risk.severity === 'medium' ? 'badge-pending' : 'badge-success'}`}>
                    {risk.severity?.toUpperCase()}
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
            <h3 className="text-lg font-semibold text-primary-50">{t('report.marketTrends')}</h3>
          </div>
          <div className="space-y-2">
            {report.market_trends.map((trend: string, i: number) => (
              <div key={i} className="flex items-center gap-2 p-2 bg-dark-bg rounded-lg border border-dark-border">
                <div className="w-2 h-2 bg-primary-500 rounded-full" />
                <p className="text-sm text-primary-200">{trend}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Charts - Lazy Loaded with IntersectionObserver */}
      {report.chart_specs && report.chart_specs.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-cyan-500" />
            <h3 className="text-lg font-semibold text-primary-50">{t('research.results')}</h3>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {report.chart_specs.map((chart: { data?: { label: string; value: number }[]; title: string; chart_type: string }, index: number) => (
              <div key={index} className="bg-dark-bg rounded-lg p-4 border border-dark-border">
                <LazyChart
                  labels={chart.data?.map((d: { label: string; value: number }) => d.label) || []}
                  values={chart.data?.map((d: { label: string; value: number }) => d.value) || []}
                  title={chart.title}
                  type={chart.chart_type === 'line' ? 'line' : 'bar'}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {report.recommendations && report.recommendations.length > 0 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Target className="w-5 h-5 text-green-500" />
            <h3 className="text-lg font-semibold text-primary-50">{t('report.recommendations')}</h3>
          </div>
          <div className="space-y-3">
            {report.recommendations.map((rec: string, i: number) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-dark-bg rounded-lg border border-dark-border">
                <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-primary-200">{rec}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Execution Summary */}
      <div className="card">
        <h3 className="text-lg font-semibold text-primary-50 mb-4">{t('dashboard.systemOverview')}</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3 p-3 bg-dark-bg rounded-lg border border-dark-border">
            <Clock className="w-5 h-5 text-primary-400" />
            <div>
              <p className="text-xs text-primary-400">{t('system.uptime')}</p>
              <p className="text-sm font-semibold text-primary-200">{report.elapsed ? `${report.elapsed.toFixed(1)}s` : '-'}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-dark-bg rounded-lg border border-dark-border">
            <BarChart3 className="w-5 h-5 text-primary-400" />
            <div>
              <p className="text-xs text-primary-400">{t('system.successRate')}</p>
              <p className="text-sm font-semibold text-primary-200">
                {report.total_tasks ? `${((report.success_tasks || 0) / report.total_tasks * 100).toFixed(1)}%` : '-'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
