import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageHeader } from '../components/layout'
import { MarketOverview, HotStocksList, AIMarketInsight, RiskMetrics, RecentTasks } from '../components/dashboard'
import { RefreshCw } from 'lucide-react'

export default function Dashboard() {
  const { t } = useTranslation()
  const [refreshKey, setRefreshKey] = useState(0)

  return (
    <div className="app-page app-page-wide space-y-6">
      <PageHeader
        title={t('dashboard.title')}
        subtitle={t('dashboard.systemOverview')}
      >
        <button
          type="button"
          onClick={() => setRefreshKey((current) => current + 1)}
          className="flex items-center gap-2 px-3.5 py-2 text-sm text-primary-400 hover:text-primary-200 bg-dark-card border border-dark-border rounded transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          {t('common.refresh')}
        </button>
      </PageHeader>

      {/* Market Overview */}
      <MarketOverview refreshKey={refreshKey} />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        <div className="min-w-0 xl:col-span-8">
          <HotStocksList refreshKey={refreshKey} />
        </div>

        <div className="min-w-0 xl:col-span-4">
          <AIMarketInsight />
        </div>

        <div className="min-w-0 xl:col-span-8">
          <RiskMetrics />
        </div>

        <div className="min-w-0 xl:col-span-4">
          <RecentTasks />
        </div>
      </div>
    </div>
  )
}
