import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useTranslation } from 'react-i18next'
import {
  LayoutDashboard,
  FlaskConical,
  Database,
  Briefcase,
  Activity,
  Search,
  Bell,
  Settings,
  User,
  LogOut,
  ChevronDown,
  Zap,
  MessageSquare,
  FileText,
} from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import LanguageSwitcher from '../LanguageSwitcher'

const navItems = [
  { path: '/', label: 'nav.dashboard', icon: LayoutDashboard, roles: ['admin', 'analyst', 'viewer'] },
  { path: '/research', label: 'nav.research', icon: FlaskConical, roles: ['admin', 'analyst'] },
  { path: '/chat', label: 'nav.chat', icon: MessageSquare, roles: ['admin', 'analyst'] },
  { path: '/knowledge', label: 'nav.knowledge', icon: Database, roles: ['admin', 'analyst'] },
  { path: '/rag', label: 'nav.rag', icon: FileText, roles: ['admin', 'analyst'] },
  { path: '/portfolio', label: 'nav.portfolio', icon: Briefcase, roles: ['admin', 'analyst', 'viewer'] },
  { path: '/system', label: 'nav.system', icon: Activity, roles: ['admin', 'analyst', 'viewer'] },
]

export default function TopNavBar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout, hasAnyRole } = useAuth()
  const { t } = useTranslation()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const menuRef = useRef<HTMLDivElement>(null)

  // Filter nav items based on user role
  const visibleNavItems = navItems.filter(item => hasAnyRole(item.roles))

  // Close menu on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/research?q=${encodeURIComponent(searchQuery.trim())}`)
      setSearchQuery('')
    }
  }

  const roleColors: Record<string, string> = {
    admin: 'text-red-400 bg-red-500/10',
    analyst: 'text-blue-400 bg-blue-500/10',
    viewer: 'text-green-400 bg-green-500/10',
  }

  return (
    <header className="h-12 bg-dark-sub border-b border-dark-border flex items-center px-4 z-50">
      {/* Logo */}
      <Link to="/" className="flex items-center gap-2 mr-6">
        <div className="w-7 h-7 bg-primary-500 rounded flex items-center justify-center">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <span className="text-sm font-bold text-primary-50 hidden sm:block">SFA</span>
      </Link>

      {/* Navigation */}
      <nav className="flex items-center gap-1">
        {visibleNavItems.map((item) => {
          const Icon = item.icon
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                isActive(item.path)
                  ? 'bg-primary-500/10 text-primary-500'
                  : 'text-primary-400 hover:text-primary-200 hover:bg-dark-card'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="hidden md:block">{t(item.label)}</span>
            </Link>
          )
        })}
      </nav>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Search */}
      <form onSubmit={handleSearch} className="relative mr-3">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-primary-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={t('common.search') + '...'}
          className="w-48 lg:w-64 h-8 pl-8 pr-3 bg-dark-bg border border-dark-border rounded text-xs text-primary-200 placeholder:text-primary-500 focus:outline-none focus:border-primary-500"
        />
      </form>

      {/* Language Switcher */}
      <div className="mr-2">
        <LanguageSwitcher />
      </div>

      {/* Notifications */}
      <button className="p-1.5 text-primary-400 hover:text-primary-200 hover:bg-dark-card rounded transition-colors mr-1">
        <Bell className="w-4 h-4" />
      </button>

      {/* User Menu */}
      <div className="relative" ref={menuRef}>
        <button
          onClick={() => setShowUserMenu(!showUserMenu)}
          className="flex items-center gap-2 px-2 py-1.5 text-primary-400 hover:text-primary-200 hover:bg-dark-card rounded transition-colors"
        >
          <div className="w-6 h-6 bg-primary-500/10 rounded-full flex items-center justify-center">
            <User className="w-3.5 h-3.5 text-primary-500" />
          </div>
          <span className="text-xs font-medium hidden sm:block">{user?.username}</span>
          <ChevronDown className="w-3 h-3" />
        </button>

        {/* Dropdown */}
        {showUserMenu && (
          <div className="absolute right-0 top-full mt-1 w-48 bg-dark-card border border-dark-border rounded-lg shadow-lg py-1 z-50">
            {/* User Info */}
            <div className="px-3 py-2 border-b border-dark-border">
              <p className="text-xs font-medium text-primary-200">{user?.username}</p>
              <p className="text-xs text-primary-500">{user?.email}</p>
              <span className={`inline-block mt-1 text-xs px-1.5 py-0.5 rounded ${roleColors[user?.role || 'viewer']}`}>
                {user?.role?.toUpperCase()}
              </span>
            </div>

            {/* Actions */}
            <Link
              to="/settings"
              className="flex items-center gap-2 px-3 py-1.5 text-xs text-primary-400 hover:text-primary-200 hover:bg-dark-bg"
              onClick={() => setShowUserMenu(false)}
            >
              <Settings className="w-3.5 h-3.5" />
              {t('nav.settings')}
            </Link>
            <button
              onClick={() => {
                setShowUserMenu(false)
                logout()
              }}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-red-400 hover:text-red-300 hover:bg-dark-bg"
            >
              <LogOut className="w-3.5 h-3.5" />
              {t('auth.logout')}
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
