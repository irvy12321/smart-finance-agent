import { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: ReactNode
  children?: ReactNode
}

export default function PageHeader({ title, subtitle, actions, children }: PageHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-4 pb-3 border-b border-dark-border">
      <div>
        <h1 className="text-lg font-semibold text-primary-50">{title}</h1>
        {subtitle && <p className="text-xs text-primary-400 mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2">
        {children}
        {actions}
      </div>
    </div>
  )
}
