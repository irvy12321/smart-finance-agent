import { useEffect, useState } from 'react'
import { CheckCircle, AlertCircle, AlertTriangle, Info, X } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

interface ToastProps {
  type: ToastType
  title: string
  message?: string
  onClose: () => void
}

const toastConfig = {
  success: {
    icon: CheckCircle,
    bg: 'bg-green-500/10',
    border: 'border-green-500/30',
    iconColor: 'text-green-500',
    titleColor: 'text-green-400',
  },
  error: {
    icon: AlertCircle,
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    iconColor: 'text-red-500',
    titleColor: 'text-red-400',
  },
  warning: {
    icon: AlertTriangle,
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/30',
    iconColor: 'text-yellow-500',
    titleColor: 'text-yellow-400',
  },
  info: {
    icon: Info,
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    iconColor: 'text-blue-500',
    titleColor: 'text-blue-400',
  },
}

export default function Toast({ type, title, message, onClose }: ToastProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [isLeaving, setIsLeaving] = useState(false)
  const config = toastConfig[type]
  const Icon = config.icon

  useEffect(() => {
    requestAnimationFrame(() => setIsVisible(true))
  }, [])

  const handleClose = () => {
    setIsLeaving(true)
    setTimeout(onClose, 300)
  }

  return (
    <div
      className={`pointer-events-auto w-full transform transition-all duration-300 ease-out ${
        isVisible && !isLeaving
          ? 'translate-x-0 opacity-100'
          : 'translate-x-full opacity-0'
      }`}
    >
      <div className={`${config.bg} backdrop-blur-sm border ${config.border} rounded-xl p-4 shadow-2xl`}>
        <div className="flex items-start gap-3">
          <div className={`flex-shrink-0 w-8 h-8 ${config.bg} rounded-lg flex items-center justify-center`}>
            <Icon className={`w-4 h-4 ${config.iconColor}`} />
          </div>
          <div className="flex-1 min-w-0">
            <p className={`text-sm font-semibold ${config.titleColor}`}>{title}</p>
            {message && (
              <p className="text-xs text-primary-400 mt-1 line-clamp-2">{message}</p>
            )}
          </div>
          <button
            onClick={handleClose}
            className="flex-shrink-0 text-primary-400 hover:text-primary-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
