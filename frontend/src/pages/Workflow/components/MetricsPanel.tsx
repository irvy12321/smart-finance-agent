interface MetricsPanelProps {
  totalTasks: number
  completedTasks: number
  failedTasks: number
  totalDuration: number
  avgTaskDuration: number
}

export function MetricsPanel({
  totalTasks,
  completedTasks,
  failedTasks,
  totalDuration,
  avgTaskDuration,
}: MetricsPanelProps) {
  const metrics = [
    {
      label: 'Total Tasks',
      value: totalTasks,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
    },
    {
      label: 'Completed',
      value: completedTasks,
      color: 'text-green-400',
      bgColor: 'bg-green-500/10',
    },
    {
      label: 'Failed',
      value: failedTasks,
      color: 'text-red-400',
      bgColor: 'bg-red-500/10',
    },
    {
      label: 'Total Time',
      value: `${(totalDuration / 1000).toFixed(1)}s`,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
    },
    {
      label: 'Avg Time',
      value: `${(avgTaskDuration / 1000).toFixed(1)}s`,
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/10',
    },
  ]

  return (
    <div className="grid grid-cols-5 gap-3">
      {metrics.map((metric) => (
        <div
          key={metric.label}
          className={`${metric.bgColor} rounded-lg p-3 text-center`}
        >
          <div className={`text-2xl font-bold ${metric.color}`}>{metric.value}</div>
          <div className="text-xs text-gray-500 mt-1">{metric.label}</div>
        </div>
      ))}
    </div>
  )
}
