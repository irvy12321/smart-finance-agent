import { PageHeader } from '../components/layout'
import { Activity } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export default function SystemMonitor() {
  const { t } = useTranslation()
  return (
    <div className="app-page app-page-narrow space-y-6">
      <PageHeader
        title={t('systemMonitor.title')}
        subtitle={t('systemMonitor.subtitle')}
      />

      <div className="card flex flex-col items-center justify-center py-16">
        <div className="w-16 h-16 bg-primary-500/10 rounded-full flex items-center justify-center mb-4">
          <Activity className="w-8 h-8 text-primary-400" />
        </div>
        <h2 className="text-xl font-semibold text-primary-200 mb-2">
          {t('systemMonitor.comingSoon')}
        </h2>
        <p className="text-sm text-primary-400 text-center max-w-md">
          {t('systemMonitor.description')}
        </p>
      </div>
    </div>
  )
}
