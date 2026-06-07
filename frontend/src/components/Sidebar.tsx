import { Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Search, 
  Settings, 
  Zap,
  MessageSquare
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Research', href: '/research', icon: Search },
  { name: 'Chat', href: '/chat', icon: MessageSquare },
  { name: 'System', href: '/system', icon: Settings },
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <div className="w-64 bg-dark-sub border-r border-dark-border flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-dark-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-500 rounded-lg flex items-center justify-center">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-primary-50">Smart Finance</h1>
            <p className="text-xs text-primary-400 font-medium">RESEARCH PLATFORM</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-4 px-3">
          Navigation
        </p>
        {navigation.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
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
          System Status
        </p>
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-3">
            <div className="status-dot status-dot-success" />
            <span className="text-xs text-primary-300">Orchestrator Active</span>
          </div>
          <div className="flex items-center gap-2 px-3">
            <div className="status-dot status-dot-success" />
            <span className="text-xs text-primary-300">API Connected</span>
          </div>
        </div>
      </div>

      {/* Configuration */}
      <div className="p-4 border-t border-dark-border">
        <p className="text-xs font-semibold text-primary-400 uppercase tracking-wider mb-3 px-3">
          Configuration
        </p>
        <div className="px-3 space-y-1">
          <p className="text-xs text-primary-400">
            Model: <span className="text-primary-200 font-mono">gpt-4</span>
          </p>
          <p className="text-xs text-primary-400">
            Embedding: <span className="text-primary-200 font-mono">dev (hash)</span>
          </p>
        </div>
      </div>
    </div>
  )
}