import { useTranslation } from 'react-i18next'
import { PageHeader } from '../components/layout'
import { MarketOverview, HotStocksList, AIMarketInsight, RiskMetrics, RecentTasks } from '../components/dashboard'
import { RefreshCw } from 'lucide-react'

export default function Dashboard() {
  const { t } = useTranslation()

  return (
    <div className="p-4 lg:p-6 space-y-4">
      <PageHeader
        title={t('dashboard.title')}
        subtitle={t('dashboard.systemOverview')}
      >
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-primary-400 hover:text-primary-200 bg-dark-card border border-dark-border rounded transition-colors">
          <RefreshCw className="w-3.5 h-3.5" />
          {t('common.refresh')}
        </button>
      </PageHeader>

      {/* Market Overview */}
      <MarketOverview />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Hot Stocks (2/3) */}
        <div className="lg:col-span-2">
          <HotStocksList />
        </div>

        {/* Right: AI Insights (1/3) */}
        <div>
          <AIMarketInsight />
        </div>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Risk Metrics (2/3) */}
        <div className="lg:col-span-2">
          <RiskMetrics />
        </div>

        {/* Right: Recent Tasks (1/3) */}
        <div>
          <RecentTasks />
        </div>
      </div>
    </div>
  )
}
