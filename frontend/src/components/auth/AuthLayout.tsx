import type { ReactNode } from 'react'

interface AuthLayoutProps {
  icon: ReactNode
  title: string
  subtitle: string
  children: ReactNode
  footer: ReactNode
}

export default function AuthLayout({ icon, title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <div className="auth-page">
      <main className="auth-shell">
        <div className="auth-header">
          <div className="auth-icon">{icon}</div>
          <h1 className="auth-title">{title}</h1>
          <p className="auth-subtitle">{subtitle}</p>
        </div>

        <section className="auth-card">
          {children}

          <div className="auth-footer">{footer}</div>
        </section>
      </main>
    </div>
  )
}
