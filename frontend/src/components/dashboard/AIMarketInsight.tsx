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
    <div className="min-w-0 bg-dark-card border border-dark-border rounded-lg overflow-hidden h-full min-h-[18rem] flex flex-col">
      <div className="flex items-center justify-between gap-4 px-4 py-3 border-b border-dark-border">
        <div className="flex items-center gap-2">
          <Brain className="w-3.5 h-3.5 text-primary-500" />
          <span className="text-xs font-semibold text-primary-300 uppercase tracking-wider">
            {t('dashboard.aiInsights')}
          </span>
        </div>
        <span className="text-xs text-primary-500 whitespace-nowrap">{t('dashboard.updatedAgo')}</span>
      </div>

      <div className="min-h-0 flex-1 p-4 sm:p-5 space-y-4 overflow-auto">
        {insights.map((insight) => {
          const Icon = insight.icon

          return (
            <div key={insight.type} className={`${insight.bgColor} rounded-lg px-4 py-3.5`}>
              <div className="flex items-center gap-2.5 mb-2.5">
                <Icon className={`w-4 h-4 ${insight.color} flex-shrink-0`} />
                <span className={`text-sm font-semibold ${insight.color}`}>{insight.title}</span>
              </div>

              {insight.content && (
                <p className="text-sm text-primary-300 leading-relaxed break-words pl-6">{insight.content}</p>
              )}

              {insight.items && (
                <ul className="space-y-1.5 pl-6">
                  {insight.items.map((item, i) => (
                    <li key={i} className="text-sm text-primary-300 flex items-start gap-2.5 break-words leading-relaxed">
                      <span className="mt-2 h-1 w-1 rounded-full bg-primary-500 flex-shrink-0" />
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
