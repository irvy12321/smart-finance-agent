import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../contexts/AuthContext'
import {
  LayoutDashboard,
  FlaskConical,
  Settings,
  Zap,
  MessageSquare,
  Database,
  LogOut,
  User,
  Shield
} from 'lucide-react'
import LanguageSwitcher from './LanguageSwitcher'

// Role display config
const roleConfig: Record<string, { label: string; color: string }> = {
  admin: { label: 'Admin', color: 'text-red-400 bg-red-500/10' },
  analyst: { label: 'Analyst', color: 'text-blue-400 bg-blue-500/10' },
  viewer: { label: 'Viewer', color: 'text-green-400 bg-green-500/10' },
}

export default function Sidebar() {
  const location = useLocation()
  const { user, logout, hasAnyRole } = useAuth()
  const { t } = useTranslation()

  // Navigation with role-based access
  const allNavigation = [
    { name: t('nav.dashboard'), href: '/', icon: LayoutDashboard, roles: ['admin', 'analyst', 'viewer'] },
    { name: t('nav.research'), href: '/research', icon: FlaskConical, roles: ['admin', 'analyst'] },
    { name: t('nav.chat'), href: '/chat', icon: MessageSquare, roles: ['admin', 'analyst'] },
    { name: t('nav.rag'), href: '/rag', icon: Database, roles: ['admin', 'analyst'] },
    { name: t('nav.system'), href: '/system', icon: Settings, roles: ['admin', 'analyst', 'viewer'] },
  ]

  // Filter navigation based on user role
  const navigation = allNavigation.filter(item =>
    hasAnyRole(item.roles)
  )

  // Get role display config
  const roleInfo = roleConfig[user?.role || 'viewer'] || roleConfig.viewer

  return (
    <div className="w-64 bg-dark-sub border-r border-dark-border flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-dark-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-500 rounded-lg flex items-center justify-center">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-primary-50">{t('sidebar.title')}</h1>
            <p className="text-xs text-primary-400 font-medium">{t('sidebar.subtitle')}</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-4 px-3">
          {t('nav.navigation')}
        </p>
        {navigation.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.href}
              to={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
                isActive
                  ? 'bg-primary-500/10 text-primary-500'
                  : 'text-primary-300 hover:text-primary-100 hover:bg-dark-card'
              }`}
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
            </Link>
          )
        })}
      </nav>

      {/* System Status */}
      <div className="p-4 border-t border-dark-border">
        <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-3 px-3">
          {t('sidebar.systemStatus')}
        </p>
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-3">
            <div className="status-dot status-dot-success" />
            <span className="text-xs text-primary-300">{t('sidebar.orchestratorActive')}</span>
          </div>
          <div className="flex items-center gap-2 px-3">
            <div className="status-dot status-dot-success" />
            <span className="text-xs text-primary-300">{t('sidebar.apiConnected')}</span>
          </div>
        </div>
      </div>

      {/* Language Switcher */}
      <div className="px-4 py-2 border-t border-dark-border">
        <LanguageSwitcher />
      </div>

      {/* User Info */}
      <div className="p-4 border-t border-dark-border">
        <div className="flex items-center gap-3 px-3 mb-3">
          <div className="w-8 h-8 bg-primary-500/10 rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-primary-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-primary-200 truncate">
              {user?.username || t('auth.username')}
            </p>
            <p className="text-xs text-primary-400 truncate">
              {user?.email || ''}
            </p>
          </div>
        </div>

        {/* Role Badge */}
        <div className="flex items-center gap-2 px-3 mb-3">
          <Shield className="w-4 h-4 text-primary-400" />
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${roleInfo.color}`}>
            {roleInfo.label}
          </span>
        </div>

        <button
          onClick={logout}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-primary-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>{t('auth.logout')}</span>
        </button>
      </div>
    </div>
  )
}
