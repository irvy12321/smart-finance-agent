import { clsx } from 'clsx'

interface SkeletonProps {
  className?: string
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded'
  width?: string | number
  height?: string | number
  animate?: boolean
}

export function Skeleton({
  className,
  variant = 'text',
  width,
  height,
  animate = true,
}: SkeletonProps) {
  const baseStyles = 'bg-dark-border/50'
  const animateStyles = animate ? 'animate-pulse' : ''

  const variantStyles = {
    text: 'rounded-md h-4',
    circular: 'rounded-full',
    rectangular: '',
    rounded: 'rounded-xl',
  }

  return (
    <div
      className={clsx(baseStyles, animateStyles, variantStyles[variant], className)}
      style={{
        width: width,
        height: height,
      }}
    />
  )
}

export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={clsx('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          variant="text"
          className={i === lines - 1 ? 'w-3/4' : 'w-full'}
        />
      ))}
    </div>
  )
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={clsx('card p-6', className)}>
      <div className="flex items-center gap-4 mb-4">
        <Skeleton variant="circular" width={40} height={40} />
        <div className="flex-1">
          <Skeleton variant="text" className="w-1/3 mb-2" />
          <Skeleton variant="text" className="w-1/2 h-3" />
        </div>
      </div>
      <SkeletonText lines={3} />
    </div>
  )
}

export function SkeletonTable({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="w-full">
      <div className="flex gap-4 mb-4 pb-4 border-b border-dark-border">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} variant="text" className="flex-1 h-5" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4 py-3 border-b border-dark-border/50">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} variant="text" className="flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}

export function SkeletonChart({ className }: { className?: string }) {
  return (
    <div className={clsx('card p-6', className)}>
      <Skeleton variant="text" className="w-1/3 mb-6 h-6" />
      <div className="flex items-end gap-2 h-48">
        {Array.from({ length: 7 }).map((_, i) => (
          <Skeleton
            key={i}
            variant="rounded"
            className="flex-1"
            height={`${Math.random() * 60 + 40}%`}
          />
        ))}
      </div>
    </div>
  )
}

export function SkeletonList({ items = 5 }: { items?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 p-4 bg-dark-bg rounded-lg border border-dark-border">
          <Skeleton variant="circular" width={32} height={32} />
          <div className="flex-1">
            <Skeleton variant="text" className="w-3/4 mb-2" />
            <Skeleton variant="text" className="w-1/2 h-3" />
          </div>
          <Skeleton variant="rounded" width={80} height={24} />
        </div>
      ))}
    </div>
  )
}

export function SkeletonDashboard() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Skeleton variant="text" className="w-48 h-8 mb-2" />
          <Skeleton variant="text" className="w-64 h-4" />
        </div>
        <Skeleton variant="rounded" width={120} height={40} />
      </div>

      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card p-4">
            <div className="flex items-center gap-3">
              <Skeleton variant="rounded" width={40} height={40} />
              <div>
                <Skeleton variant="text" className="w-20 h-3 mb-2" />
                <Skeleton variant="text" className="w-12 h-7" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <SkeletonChart />
        <SkeletonCard />
      </div>
    </div>
  )
}

export default Skeleton
