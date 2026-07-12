import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  AlertTriangle,
  BarChart3,
  Brain,
  Download,
  ExternalLink,
  FileText,
  Loader2,
  Target,
} from 'lucide-react'
import { reportApi } from '../../services/api'
import SimpleChart from '../SimpleChart'
import type { ChartSpec } from '../../types/api'

interface ReportData {
  title: string
  answer: string
  summary: string
  keyFindings: string[]
  riskFactors: { text: string; severity: string }[]
  marketTrends: string[]
  recommendations: string[]
  chartSpecs: ChartSpec[]
  confidence: number
}

interface ResearchReportProps {
  symbol: string | null
  taskId?: string | null
  isLoading?: boolean
}

type RawRiskFactor =
  | string
  | {
      factor?: string
      text?: string
      description?: string
      severity?: string
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
        answer: data.answer || '',
        summary: data.summary || '',
        keyFindings: data.key_findings || [],
        riskFactors: (data.risk_factors || []).map((risk: RawRiskFactor) => ({
          text:
            typeof risk === 'string'
              ? risk
              : (risk.factor ?? risk.text ?? risk.description ?? ''),
          severity: typeof risk === 'object' && risk?.severity ? risk.severity : 'medium',
        })),
        marketTrends: data.market_trends || [],
        recommendations: data.recommendations || [],
        chartSpecs: data.chart_specs || [],
        confidence: data.confidence || 0,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch report')
    } finally {
      setLoading(false)
    }
  }, [taskId, symbol])

  useEffect(() => {
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
      <div className="flex items-center justify-between px-4 py-3 border-b border-dark-border">
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-primary-100 truncate">{report.title}</h2>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-primary-500">{t('report.summary')}:</span>
            <div className="w-20 h-1.5 bg-dark-border rounded-full">
              <div
                className="h-1.5 bg-green-500 rounded-full"
                style={{ width: `${report.confidence * 100}%` }}
              />
            </div>
            <span className="text-xs text-green-400">
              {(report.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button className="p-1.5 text-primary-400 hover:text-primary-200 hover:bg-dark-bg rounded transition-colors">
            <Download className="w-4 h-4" />
          </button>
          <button className="p-1.5 text-primary-400 hover:text-primary-200 hover:bg-dark-bg rounded transition-colors">
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-3 flex flex-col gap-3">
        <div className="grid grid-cols-1 2xl:grid-cols-[minmax(0,1.15fr)_minmax(18rem,0.85fr)] gap-3">
          {report.summary && (
            <div className="bg-dark-bg border border-dark-border rounded p-3">
              <h3 className="text-xs font-semibold text-primary-300 uppercase tracking-wider mb-2">
                {t('report.summary')}
              </h3>
              <p className="text-xs text-primary-200 leading-relaxed">{report.summary}</p>
            </div>
          )}

          {report.chartSpecs.length > 0 && (
            <div className="bg-dark-bg border border-dark-border rounded p-3">
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
                <h3 className="text-xs font-semibold text-primary-300 uppercase tracking-wider">
                  Visuals
                </h3>
              </div>
              <div className="grid grid-cols-1 gap-3">
                {report.chartSpecs.slice(0, 2).map((chart, index) => (
                  <SimpleChart
                    key={`${chart.title}-${index}`}
                    data={chart.data || []}
                    type={chart.chart_type === 'line' ? 'line' : 'bar'}
                    title={chart.title}
                    height={150}
                    showLabels
                    showValues
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {report.marketTrends.length > 0 && (
          <div className="bg-dark-bg border border-dark-border rounded p-3">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
              <h3 className="text-xs font-semibold text-primary-300 uppercase tracking-wider">
                {t('report.marketTrends')}
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {report.marketTrends.slice(0, 3).map((trend, index) => (
                <div key={index} className="p-2 bg-dark-card border border-dark-border rounded">
                  <p className="text-xs text-primary-200 leading-relaxed">{trend}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 2xl:grid-cols-2 gap-3">
          {report.keyFindings.length > 0 && (
            <div className="bg-dark-bg border border-dark-border rounded p-3">
              <div className="flex items-center gap-2 mb-2">
                <Brain className="w-3.5 h-3.5 text-blue-400" />
                <h3 className="text-xs font-semibold text-primary-300 uppercase tracking-wider">
                  {t('report.keyFindings')}
                </h3>
              </div>
              <div className="space-y-2">
                {report.keyFindings.slice(0, 4).map((finding, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-2 p-2 bg-dark-card border border-dark-border rounded"
                  >
                    <div className="w-5 h-5 bg-blue-500/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="text-xs font-bold text-blue-400">{index + 1}</span>
                    </div>
                    <p className="text-xs text-primary-200">{finding}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {report.riskFactors.length > 0 && (
            <div className="bg-dark-bg border border-dark-border rounded p-3">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />
                <h3 className="text-xs font-semibold text-primary-300 uppercase tracking-wider">
                  {t('report.riskFactors')}
                </h3>
              </div>
              <div className="space-y-1.5">
                {report.riskFactors.slice(0, 4).map((risk, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 p-2 bg-dark-card border border-dark-border rounded"
                  >
                    <div
                      className={`w-1.5 h-1.5 rounded-full ${
                        risk.severity === 'high'
                          ? 'bg-red-500'
                          : risk.severity === 'medium'
                            ? 'bg-yellow-500'
                            : 'bg-green-500'
                      }`}
                    />
                    <p className="text-xs text-primary-200">{risk.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {report.recommendations.length > 0 && (
          <div className="bg-dark-bg border border-dark-border rounded p-3">
            <div className="flex items-center gap-2 mb-2">
              <Target className="w-3.5 h-3.5 text-green-400" />
              <h3 className="text-xs font-semibold text-primary-300 uppercase tracking-wider">
                {t('report.recommendations')}
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {report.recommendations.slice(0, 3).map((recommendation, index) => (
                <div
                  key={index}
                  className="flex items-start gap-2 p-2 bg-dark-card border border-dark-border rounded"
                >
                  <span className="text-green-400 mt-0.5">-</span>
                  <p className="text-xs text-primary-200">{recommendation}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {report.answer && (
          <div className="bg-dark-bg border border-dark-border rounded p-3 flex-1 min-h-[260px]">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-3.5 h-3.5 text-primary-400" />
              <h3 className="text-xs font-semibold text-primary-300 uppercase tracking-wider">
                Detailed Analysis
              </h3>
            </div>
            <div className="h-full max-h-[520px] overflow-auto pr-2">
              <p className="whitespace-pre-wrap text-xs text-primary-200 leading-relaxed">
                {formatReportText(report.answer)}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function formatReportText(value: string): string {
  return value
    .replace(/#{1,6}\s*/g, '')
    .replace(/\*\*/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}
