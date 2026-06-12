import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Clock, Server } from 'lucide-react'

export default function StatusBar() {
  const { t } = useTranslation()
  const [time, setTime] = useState(new Date())
  const [isConnected, setIsConnected] = useState(true)

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Check backend health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/api/system/health')
        setIsConnected(res.ok)
      } catch {
        setIsConnected(false)
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <footer className="h-7 bg-dark-sub border-t border-dark-border flex items-center px-4 text-xs text-primary-500">
      {/* Connection Status */}
      <div className="flex items-center gap-1.5 mr-4">
        {isConnected ? (
          <>
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
            <span className="text-green-400">{t('sidebar.apiConnected')}</span>
          </>
        ) : (
          <>
            <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
            <span className="text-red-400">{t('error.networkError')}</span>
          </>
        )}
      </div>

      {/* Separator */}
      <div className="w-px h-3 bg-dark-border mr-4" />

      {/* Server */}
      <div className="flex items-center gap-1.5 mr-4">
        <Server className="w-3 h-3" />
        <span>{import.meta.env.VITE_API_URL || window.location.host}</span>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Version */}
      <span className="mr-4">v1.0.0</span>

      {/* Separator */}
      <div className="w-px h-3 bg-dark-border mr-4" />

      {/* Time */}
      <div className="flex items-center gap-1.5">
        <Clock className="w-3 h-3" />
        <span className="font-mono">{time.toLocaleTimeString()}</span>
      </div>
    </footer>
  )
}
