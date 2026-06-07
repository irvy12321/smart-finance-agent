import { useState } from 'react'
import { TrendingUp, TrendingDown, BarChart3, Activity } from 'lucide-react'

interface DataPoint {
  label: string
  value: number
  color?: string
}

interface SimpleChartProps {
  data: DataPoint[]
  type?: 'bar' | 'line'
  title?: string
  height?: number
  showLabels?: boolean
  showValues?: boolean
}

export default function SimpleChart({ 
  data, 
  type = 'bar', 
  title, 
  height = 200,
  showLabels = true,
  showValues = true 
}: SimpleChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  if (!data || data.length === 0) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-8">
          <div className="text-center">
            <BarChart3 className="w-8 h-8 text-primary-400 mx-auto mb-2" />
            <p className="text-sm text-primary-400">No data available</p>
          </div>
        </div>
      </div>
    )
  }

  const maxValue = Math.max(...data.map(d => d.value))
  const minValue = Math.min(...data.map(d => d.value))
  const range = maxValue - minValue || 1

  const defaultColors = [
    '#6366f1', // primary
    '#10b981', // green
    '#f59e0b', // yellow
    '#ef4444', // red
    '#8b5cf6', // purple
    '#06b6d4', // cyan
    '#f97316', // orange
    '#ec4899', // pink
  ]

  const getBarHeight = (value: number) => {
    return ((value - minValue) / range) * (height - 40) + 20
  }

  const getLineColor = () => {
    const firstValue = data[0].value
    const lastValue = data[data.length - 1].value
    return lastValue >= firstValue ? '#10b981' : '#ef4444'
  }

  return (
    <div className="card">
      {title && (
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-5 h-5 text-primary-400" />
          <h3 className="text-lg font-semibold text-primary-50">{title}</h3>
        </div>
      )}

      <div className="relative" style={{ height: `${height}px` }}>
        {type === 'bar' ? (
          /* Bar Chart */
          <div className="flex items-end justify-between h-full gap-2 px-4">
            {data.map((item, index) => {
              const barHeight = getBarHeight(item.value)
              const color = item.color || defaultColors[index % defaultColors.length]
              const isHovered = hoveredIndex === index

              return (
                <div
                  key={index}
                  className="flex-1 flex flex-col items-center"
                  onMouseEnter={() => setHoveredIndex(index)}
                  onMouseLeave={() => setHoveredIndex(null)}
                >
                  {/* Value Label */}
                  {showValues && (
                    <div className={`text-xs font-medium mb-2 transition-opacity ${
                      isHovered ? 'text-primary-200 opacity-100' : 'text-primary-400 opacity-70'
                    }`}>
                      {item.value.toLocaleString()}
                    </div>
                  )}

                  {/* Bar */}
                  <div
                    className="w-full rounded-t-md transition-all duration-300 cursor-pointer"
                    style={{
                      height: `${barHeight}px`,
                      backgroundColor: isHovered ? color : `${color}88`,
                      boxShadow: isHovered ? `0 4px 12px ${color}40` : 'none',
                    }}
                  />

                  {/* Label */}
                  {showLabels && (
                    <div className={`text-xs mt-2 text-center transition-colors ${
                      isHovered ? 'text-primary-200' : 'text-primary-400'
                    }`}>
                      {item.label}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          /* Line Chart */
          <svg className="w-full h-full" viewBox={`0 0 ${data.length * 60} ${height}`}>
            {/* Grid Lines */}
            {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
              const y = height - (ratio * (height - 40)) - 20
              return (
                <line
                  key={i}
                  x1="0"
                  y1={y}
                  x2={data.length * 60}
                  y2={y}
                  stroke="#2a2a3e"
                  strokeWidth="1"
                  strokeDasharray="4,4"
                />
              )
            })}

            {/* Line Path */}
            <path
              d={data.map((item, index) => {
                const x = index * 60 + 30
                const y = height - getBarHeight(item.value) - 20
                return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
              }).join(' ')}
              fill="none"
              stroke={getLineColor()}
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Data Points */}
            {data.map((item, index) => {
              const x = index * 60 + 30
              const y = height - getBarHeight(item.value) - 20
              const isHovered = hoveredIndex === index

              return (
                <g
                  key={index}
                  onMouseEnter={() => setHoveredIndex(index)}
                  onMouseLeave={() => setHoveredIndex(null)}
                >
                  {/* Point */}
                  <circle
                    cx={x}
                    cy={y}
                    r={isHovered ? 6 : 4}
                    fill={isHovered ? getLineColor() : '#1a1a2e'}
                    stroke={getLineColor()}
                    strokeWidth="2"
                    className="cursor-pointer transition-all"
                  />

                  {/* Hover Label */}
                  {isHovered && (
                    <>
                      <rect
                        x={x - 30}
                        y={y - 30}
                        width="60"
                        height="24"
                        rx="4"
                        fill="#1a1a2e"
                        stroke="#2a2a3e"
                      />
                      <text
                        x={x}
                        y={y - 15}
                        textAnchor="middle"
                        fill="#f0f0f5"
                        fontSize="12"
                        fontWeight="600"
                      >
                        {item.value.toLocaleString()}
                      </text>
                    </>
                  )}

                  {/* Label */}
                  {showLabels && (
                    <text
                      x={x}
                      y={height - 5}
                      textAnchor="middle"
                      fill={isHovered ? '#f0f0f5' : '#8888a0'}
                      fontSize="10"
                    >
                      {item.label}
                    </text>
                  )}
                </g>
              )
            })}
          </svg>
        )}
      </div>

      {/* Legend */}
      {data.length > 0 && (
        <div className="flex items-center justify-center gap-4 mt-4 pt-4 border-t border-dark-border">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-green-500" />
            <span className="text-xs text-primary-400">
              Max: {maxValue.toLocaleString()}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-red-500" />
            <span className="text-xs text-primary-400">
              Min: {minValue.toLocaleString()}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

// Example usage component
export function ChartDemo() {
  const barData = [
    { label: 'Jan', value: 1200 },
    { label: 'Feb', value: 1800 },
    { label: 'Mar', value: 1500 },
    { label: 'Apr', value: 2200 },
    { label: 'May', value: 1900 },
    { label: 'Jun', value: 2500 },
  ]

  const lineData = [
    { label: 'Week 1', value: 150 },
    { label: 'Week 2', value: 180 },
    { label: 'Week 3', value: 165 },
    { label: 'Week 4', value: 210 },
    { label: 'Week 5', value: 195 },
    { label: 'Week 6', value: 240 },
  ]

  return (
    <div className="space-y-6">
      <SimpleChart data={barData} type="bar" title="Monthly Revenue" />
      <SimpleChart data={lineData} type="line" title="Weekly Growth" />
    </div>
  )
}