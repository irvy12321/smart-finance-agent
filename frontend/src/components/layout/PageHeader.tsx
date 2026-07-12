import { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: ReactNode
  children?: ReactNode
}

export default function PageHeader({ title, subtitle, actions, children }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6 pb-4 border-b border-dark-border">
      <div className="min-w-0">
        <h1 className="text-xl font-semibold text-primary-50">{title}</h1>
        {subtitle && <p className="text-sm text-primary-400 mt-1">{subtitle}</p>}
      </div>
      <div className="flex flex-shrink-0 items-center gap-2">
        {children}
        {actions}
      </div>
    </div>
  )
}
