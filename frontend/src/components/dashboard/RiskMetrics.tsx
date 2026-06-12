import { useTranslation } from 'react-i18next'
import { Shield, TrendingDown, BarChart3, PieChart } from 'lucide-react'

export default function RiskMetrics() {
  const { t } = useTranslation()

  const metrics = [
    {
      label: t('dashboard.portfolioBeta'),
      value: '1.15',
      status: 'warning' as const,
      icon: BarChart3,
      description: t('dashboard.betaDesc'),
    },
    {
      label: t('dashboard.sharpeRatio'),
      value: '1.82',
      status: 'good' as const,
      icon: TrendingDown,
      description: t('dashboard.sharpeDesc'),
    },
    {
      label: t('dashboard.maxDrawdown'),
      value: '-8.5%',
      status: 'warning' as const,
      icon: TrendingDown,
      description: t('dashboard.drawdownDesc'),
    },
    {
      label: t('dashboard.var95'),
      value: '-2.3%',
      status: 'good' as const,
      icon: PieChart,
      description: t('dashboard.varDesc'),
    },
  ]

  const statusColors = {
    good: { text: 'text-green-400', bg: 'bg-green-500/10', border: 'border-green-500/20' },
    warning: { text: 'text-yellow-400', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20' },
    danger: { text: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/20' },
  }

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-dark-border">
        <div className="flex items-center gap-2">
          <Shield className="w-3.5 h-3.5 text-primary-500" />
          <span className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('dashboard.riskMetrics')}</span>
        </div>
      </div>
      <div className="p-3 grid grid-cols-2 gap-3">
        {metrics.map((metric) => {
          const Icon = metric.icon
          const colors = statusColors[metric.status]
          return (
            <div key={metric.label} className={`${colors.bg} border ${colors.border} rounded-lg p-3`}>
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`w-3.5 h-3.5 ${colors.text}`} />
                <span className="text-xs text-primary-400">{metric.label}</span>
              </div>
              <div className={`text-lg font-bold font-mono ${colors.text}`}>
                {metric.value}
              </div>
              <p className="text-xs text-primary-500 mt-1">{metric.description}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
