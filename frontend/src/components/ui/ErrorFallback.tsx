import { useTranslation } from 'react-i18next'
import { AlertCircle, RefreshCw, Home, ArrowLeft, Copy, CheckCircle } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

interface ErrorFallbackProps {
  error?: Error | null
  resetError?: () => void
  showHome?: boolean
  showBack?: boolean
  compact?: boolean
}

export function ErrorFallback({
  error,
  resetError,
  showHome = true,
  showBack = false,
  compact = false,
}: ErrorFallbackProps) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)

  const handleCopyError = () => {
    if (error) {
      navigator.clipboard.writeText(`${error.name}: ${error.message}\n${error.stack || ''}`)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  if (compact) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-3" />
          <p className="text-sm text-primary-400 mb-4">{t('error.unexpectedError')}</p>
          {resetError && (
            <button onClick={resetError} className="btn-primary text-sm">
              {t('error.tryAgain')}
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[400px] p-8">
      <div className="max-w-md w-full text-center">
        <div className="w-20 h-20 bg-red-500/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <AlertCircle className="w-10 h-10 text-red-500" />
        </div>

        <h2 className="text-xl font-bold text-primary-50 mb-2">
          {t('error.somethingWentWrong')}
        </h2>
        <p className="text-sm text-primary-400 mb-6">
          {t('error.unexpectedError')}
        </p>

        {error && (
          <div className="bg-dark-bg rounded-lg p-4 mb-6 text-left border border-dark-border">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-red-400 uppercase">Error Details</span>
              <button
                onClick={handleCopyError}
                className="flex items-center gap-1 text-xs text-primary-400 hover:text-primary-200"
              >
                {copied ? (
                  <>
                    <CheckCircle className="w-3 h-3 text-green-500" />
                    <span className="text-green-500">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <p className="text-xs text-red-400 font-mono break-all">{error.message}</p>
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          {resetError && (
            <button
              onClick={resetError}
              className="btn-primary flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              {t('error.tryAgain')}
            </button>
          )}
          {showBack && (
            <button
              onClick={() => window.history.back()}
              className="btn-secondary flex items-center justify-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              {t('common.back')}
            </button>
          )}
          {showHome && (
            <Link
              to="/"
              className="btn-secondary flex items-center justify-center gap-2"
            >
              <Home className="w-4 h-4" />
              {t('nav.dashboard')}
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}

export function NetworkError({ onRetry }: { onRetry?: () => void }) {
  const { t } = useTranslation()

  return (
    <div className="flex items-center justify-center p-8">
      <div className="text-center">
        <div className="w-16 h-16 bg-yellow-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="w-8 h-8 text-yellow-500" />
        </div>
        <h3 className="text-lg font-semibold text-primary-50 mb-2">{t('error.networkError')}</h3>
        <p className="text-sm text-primary-400 mb-4">{t('error.serverError')}</p>
        {onRetry && (
          <button onClick={onRetry} className="btn-primary text-sm">
            {t('error.tryAgain')}
          </button>
        )}
      </div>
    </div>
  )
}

export function NotFoundError({ resource }: { resource?: string }) {
  const { t } = useTranslation()

  return (
    <div className="flex items-center justify-center p-8">
      <div className="text-center">
        <div className="text-6xl font-bold text-primary-500/20 mb-4">404</div>
        <h3 className="text-lg font-semibold text-primary-50 mb-2">
          {resource || t('error.notFound')}
        </h3>
        <p className="text-sm text-primary-400 mb-4">{t('error.notFound')}</p>
        <Link to="/" className="btn-primary text-sm">
          {t('nav.dashboard')}
        </Link>
      </div>
    </div>
  )
}

export default ErrorFallback
