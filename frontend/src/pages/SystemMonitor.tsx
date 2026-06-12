import { PageHeader } from '../components/layout'
import { Activity } from 'lucide-react'

export default function SystemMonitor() {
  return (
    <div className="p-4 lg:p-6 space-y-4">
      <PageHeader
        title="System Monitor"
        subtitle="Monitor system performance and health"
      />

      <div className="card flex flex-col items-center justify-center py-16">
        <div className="w-16 h-16 bg-primary-500/10 rounded-full flex items-center justify-center mb-4">
          <Activity className="w-8 h-8 text-primary-400" />
        </div>
        <h2 className="text-xl font-semibold text-primary-200 mb-2">
          System Monitor - Coming Soon
        </h2>
        <p className="text-sm text-primary-400 text-center max-w-md">
          This feature is under development. You will be able to monitor real-time system metrics, agent performance, and resource utilization.
        </p>
      </div>
    </div>
  )
}
