import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { FileText, Download, ExternalLink, Brain, AlertTriangle, Target, Loader2 } from 'lucide-react'
import { reportApi } from '../../services/api'

interface ReportData {
  title: string
  summary: string
  keyFindings: string[]
  riskFactors: { text: string; severity: string }[]
  recommendations: string[]
  confidence: number
}

interface ResearchReportProps {
  symbol: string | null
  taskId?: string | null
  isLoading?: boolean
}

export default function ResearchReport({ symbol, taskId, isLoading }: ResearchReportProps) {
  const { t } = useTranslation()
  const [report, setReport] = useState<ReportData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchReport = useCallback(async () => {
    if (!taskId) return

    try {
      setLoading(true)
      setError(null)

      const data = await reportApi.get(taskId)
      setReport({
        title: data.report_title || `${symbol} Analysis`,
        summary: data.summary || '',
        keyFindings: data.key_findings || [],
        riskFactors: (data.risk_factors || []).map((r: any) => ({
          text: typeof r === 'string' ? r : (r.factor ?? r.text ?? r.description ?? ''),
          severity: (typeof r === 'object' && r?.severity) ? r.severity : 'medium'
        })),
        recommendations: data.recommendations || [],
        confidence: data.confidence || 0,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch report')
    } finally {
      setLoading(false)
    }
  }, [taskId, symbol])

  useEffect(() => {
    // Only fetch once the task has finished running; fetching while the task is
    // still in progress returns 400 ("Task is not completed"). When isLoading
    // flips false on completion this re-runs and pulls the finished report.
    if (taskId && !isLoading) {
      fetchReport()
    }
  }, [taskId, isLoading, fetchReport])

  if (!taskId && !symbol) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg h-full flex items-center justify-center">
        <div className="text-center text-primary-500">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm">{t('research.noResults')}</p>
          <p className="text-xs mt-1">{t('research.startResearch')}</p>
        </div>
      </div>
    )
  }

  if (loading || isLoading) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg h-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-primary-500 animate-spin mx-auto mb-3" />
          <p className="text-sm text-primary-400">{t('research.analyzing')}</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg h-full flex items-center justify-center">
        <div className="text-center text-red-400">
          <AlertTriangle className="w-8 h-8 mx-auto mb-3" />
          <p className="text-sm">{error}</p>
          <button
            onClick={fetchReport}
            className="mt-2 text-xs text-primary-500 hover:text-primary-300"
          >
            {t('common.refresh')}
          </button>
        </div>
      </div>
    )
  }

  if (!report) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg h-full flex items-center justify-center">
        <div className="text-center text-primary-500">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm">{t('report.noReport')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border">
        <div>
          <h2 className="text-sm font-semibold text-primary-100">{report.title}</h2>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-primary-500">{t('report.summary')}:</span>
            <div className="w-20 h-1.5 bg-dark-border rounded-full">
              <div
                className="h-1.5 bg-green-500 rounded-full"
                style={{ width: `${report.confidence * 100}%` }}
              />
            </div>
            <span className="text-xs text-green-400">{(report.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="p-1.5 text-primary-400 hover:text-primary-200 hover:bg-dark-bg rounded transition-colors">
            <Download className="w-4 h-4" />
          </button>
          <button className="p-1.5 text-primary-400 hover:text-primary-200 hover:bg-dark-bg rounded transition-colors">
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {/* Summary */}
        {report.summary && (
          <div>
            <h3 className="text-xs font-semibold text-primary-300 uppercase tracking-wider mb-2">{t('report.summary')}</h3>
            <p className="text-xs text-primary-200 leading-relaxed">{report.summary}</p>
          </div>
        )}

        {/* Key Findings */}
        {report.keyFindings.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-3.5 h-3.5 text-blue-400" />
              <h3 className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('report.keyFindings')}</h3>
            </div>
            <div className="space-y-2">
              {report.keyFindings.map((finding, i) => (
                <div key={i} className="flex items-start gap-2 p-2 bg-dark-bg rounded">
                  <div className="w-5 h-5 bg-blue-500/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-blue-400">{i + 1}</span>
                  </div>
                  <p className="text-xs text-primary-200">{finding}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Risk Factors */}
        {report.riskFactors.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />
              <h3 className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('report.riskFactors')}</h3>
            </div>
            <div className="space-y-1.5">
              {report.riskFactors.map((risk, i) => (
                <div key={i} className="flex items-center gap-2 p-2 bg-dark-bg rounded">
                  <div className={`w-1.5 h-1.5 rounded-full ${
                    risk.severity === 'high' ? 'bg-red-500' : risk.severity === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                  }`} />
                  <p className="text-xs text-primary-200">{risk.text}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {report.recommendations.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-3.5 h-3.5 text-green-400" />
              <h3 className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('report.recommendations')}</h3>
            </div>
            <div className="space-y-1.5">
              {report.recommendations.map((rec, i) => (
                <div key={i} className="flex items-start gap-2 p-2 bg-dark-bg rounded">
                  <span className="text-green-400 mt-0.5">•</span>
                  <p className="text-xs text-primary-200">{rec}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
