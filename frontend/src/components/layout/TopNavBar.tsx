import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
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
import { useAuth } from '../../contexts/AuthContext'
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

  const visibleNavItems = navItems.filter((item) => hasAnyRole(item.roles))

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

  const navAliases: { path: string; keywords: string[] }[] = [
    { path: '/', keywords: ['dashboard', 'home', '仪表盘', '首页', '主页'] },
    { path: '/research', keywords: ['research', '研究', '调研'] },
    { path: '/chat', keywords: ['chat', '对话', '聊天'] },
    { path: '/knowledge', keywords: ['knowledge', '知识库', '知识'] },
    { path: '/rag', keywords: ['rag', '检索', '文档'] },
    { path: '/portfolio', keywords: ['portfolio', '投资组合', '组合', '持仓'] },
    { path: '/system', keywords: ['system', '系统', '监控'] },
  ]

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()

    const query = searchQuery.trim()
    if (!query) return

    const q = query.toLowerCase()
    const match = navAliases.find(
      (alias) =>
        visibleNavItems.some((item) => item.path === alias.path) &&
        alias.keywords.some((keyword) => keyword === q || q.includes(keyword))
    )

    if (match) {
      navigate(match.path)
    } else {
      navigate(`/research?q=${encodeURIComponent(query)}`)
    }

    setSearchQuery('')
  }

  const roleColors: Record<string, string> = {
    admin: 'text-red-400 bg-red-500/10',
    analyst: 'text-blue-400 bg-blue-500/10',
    viewer: 'text-green-400 bg-green-500/10',
  }

  return (
    <header className="h-14 flex-shrink-0 bg-dark-sub border-b border-dark-border flex items-center px-4 sm:px-6 lg:px-8 z-50 min-w-0">
      <Link to="/" className="flex flex-shrink-0 items-center gap-2 mr-5 lg:mr-7">
        <div className="w-8 h-8 bg-primary-500 rounded flex items-center justify-center">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <span className="text-base font-bold text-primary-50">SFA</span>
      </Link>

      <nav className="scrollbar-none flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto">
        {visibleNavItems.map((item) => {
          const Icon = item.icon

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex flex-shrink-0 items-center gap-2 px-3 py-2 text-sm font-medium rounded transition-colors ${
                isActive(item.path)
                  ? 'bg-primary-500/10 text-primary-500'
                  : 'text-primary-400 hover:text-primary-200 hover:bg-dark-card'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="whitespace-nowrap">{t(item.label)}</span>
            </Link>
          )
        })}
      </nav>

      <form onSubmit={handleSearch} className="relative ml-4 mr-3 hidden flex-shrink-0 sm:block">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-primary-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={t('common.search') + '...'}
          className="w-44 lg:w-64 h-9 pl-9 pr-3 bg-dark-bg border border-dark-border rounded text-sm text-primary-200 placeholder:text-primary-500 focus:outline-none focus:border-primary-500"
        />
      </form>

      <div className="mr-1 flex-shrink-0 sm:mr-2">
        <LanguageSwitcher />
      </div>

      <button className="p-2 text-primary-400 hover:text-primary-200 hover:bg-dark-card rounded transition-colors mr-1 flex-shrink-0">
        <Bell className="w-4 h-4" />
      </button>

      <div className="relative flex-shrink-0" ref={menuRef}>
        <button
          onClick={() => setShowUserMenu(!showUserMenu)}
          className="flex items-center gap-2 px-2 py-2 text-primary-400 hover:text-primary-200 hover:bg-dark-card rounded transition-colors"
        >
          <div className="w-7 h-7 bg-primary-500/10 rounded-full flex items-center justify-center">
            <User className="w-4 h-4 text-primary-500" />
          </div>
          <span className="hidden text-sm font-medium lg:inline">{user?.username}</span>
          <ChevronDown className="w-3.5 h-3.5" />
        </button>

        {showUserMenu && (
          <div className="absolute right-0 top-full mt-2 w-52 bg-dark-card border border-dark-border rounded-lg shadow-lg py-1.5 z-50">
            <div className="px-3 py-2.5 border-b border-dark-border">
              <p className="text-sm font-medium text-primary-200">{user?.username}</p>
              <p className="text-xs text-primary-500 mt-0.5">{user?.email}</p>
              <span className={`inline-block mt-2 text-xs px-2 py-0.5 rounded ${roleColors[user?.role || 'viewer']}`}>
                {user?.role?.toUpperCase()}
              </span>
            </div>

            <Link
              to="/settings"
              className="flex items-center gap-2 px-3 py-2 text-sm text-primary-400 hover:text-primary-200 hover:bg-dark-bg"
              onClick={() => setShowUserMenu(false)}
            >
              <Settings className="w-4 h-4" />
              {t('nav.settings')}
            </Link>
            <button
              onClick={() => {
                setShowUserMenu(false)
                logout()
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-dark-bg"
            >
              <LogOut className="w-4 h-4" />
              {t('auth.logout')}
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
