import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../contexts/AuthContext'
import { LogIn, Loader2, AlertCircle, Eye, EyeOff } from 'lucide-react'
import AuthLayout from '../components/auth/AuthLayout'

export default function Login() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname || '/'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!username.trim() || !password.trim()) {
      setError(t('auth.fillAllFields'))
      return
    }

    setLoading(true)
    setError(null)

    try {
      await login(username, password)
      navigate(from, { replace: true })
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } }
      setError(axiosErr.response?.data?.detail || t('auth.loginError'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      icon={<LogIn className="w-6 h-6 sm:w-7 sm:h-7 lg:w-8 lg:h-8 2xl:w-9 2xl:h-9 text-accent" />}
      title={t('auth.welcomeBack')}
      subtitle={t('auth.signInTo')}
      footer={
        <p className="text-sm sm:text-base text-primary-400">
          {t('auth.noAccount')}{' '}
          <Link to="/register" className="text-primary-500 hover:text-primary-400 font-medium">
            {t('auth.register')}
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5 lg:space-y-6">
        {error && (
          <div className="p-3 sm:p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-2.5 sm:gap-3">
            <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm sm:text-base text-red-400">{error}</p>
          </div>
        )}

        <div>
          <label htmlFor="username" className="block text-sm sm:text-base font-medium text-primary-300 mb-1.5 sm:mb-2">
            {t('auth.username')}
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder={t('auth.enterUsername')}
            className="input h-11 sm:h-12 lg:h-14 text-sm sm:text-base sm:px-4 w-full"
            disabled={loading}
            autoComplete="username"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm sm:text-base font-medium text-primary-300 mb-1.5 sm:mb-2">
            {t('auth.password')}
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t('auth.enterPassword')}
              className="input h-11 sm:h-12 lg:h-14 text-sm sm:text-base sm:px-4 w-full pr-11 sm:pr-12"
              disabled={loading}
              autoComplete="current-password"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 sm:right-4 top-1/2 -translate-y-1/2 text-primary-400 hover:text-primary-300"
            >
              {showPassword ? <EyeOff className="w-4 h-4 sm:w-5 sm:h-5" /> : <Eye className="w-4 h-4 sm:w-5 sm:h-5" />}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !username.trim() || !password.trim()}
          className="w-full h-11 sm:h-12 lg:h-14 flex items-center justify-center gap-2 px-5 sm:px-6 bg-accent hover:bg-[#74acff] disabled:bg-accent/40 disabled:cursor-not-allowed text-[#06121f] text-sm sm:text-base font-semibold rounded-lg transition-colors duration-150"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
              {t('auth.signingIn')}
            </>
          ) : (
            <>
              <LogIn className="w-4 h-4 sm:w-5 sm:h-5" />
              {t('auth.login')}
            </>
          )}
        </button>
      </form>
    </AuthLayout>
  )
}
