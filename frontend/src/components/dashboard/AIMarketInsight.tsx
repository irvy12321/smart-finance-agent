import { useTranslation } from 'react-i18next'
import { Brain, AlertTriangle, Calendar } from 'lucide-react'

export default function AIMarketInsight() {
  const { t } = useTranslation()

  const insights = [
    {
      type: 'sentiment',
      icon: Brain,
      title: t('dashboard.aiInsight'),
      content: t('dashboard.aiInsightContent'),
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
    },
    {
      type: 'event',
      icon: Calendar,
      title: t('dashboard.keyEvents'),
      items: [
        t('dashboard.event1'),
        t('dashboard.event2'),
        t('dashboard.event3'),
      ],
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/10',
    },
    {
      type: 'alert',
      icon: AlertTriangle,
      title: t('dashboard.riskAlerts'),
      items: [
        t('dashboard.alert1'),
        t('dashboard.alert2'),
      ],
      color: 'text-red-400',
      bgColor: 'bg-red-500/10',
    },
  ]

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden h-full">
      <div className="flex items-center justify-between px-3 py-2 border-b border-dark-border">
        <div className="flex items-center gap-2">
          <Brain className="w-3.5 h-3.5 text-primary-500" />
          <span className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('dashboard.aiInsights')}</span>
        </div>
        <span className="text-xs text-primary-500">{t('dashboard.updatedAgo')}</span>
      </div>
      <div className="p-3 space-y-3 overflow-auto max-h-[300px]">
        {insights.map((insight) => {
          const Icon = insight.icon
          return (
            <div key={insight.type} className={`${insight.bgColor} rounded-lg p-3`}>
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`w-3.5 h-3.5 ${insight.color}`} />
                <span className={`text-xs font-semibold ${insight.color}`}>{insight.title}</span>
              </div>
              {insight.content && (
                <p className="text-xs text-primary-300 leading-relaxed">{insight.content}</p>
              )}
              {insight.items && (
                <ul className="space-y-1">
                  {insight.items.map((item, i) => (
                    <li key={i} className="text-xs text-primary-300 flex items-start gap-2">
                      <span className="text-primary-500 mt-1">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
