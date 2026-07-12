import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../contexts/AuthContext'
import { UserPlus, Loader2, AlertCircle, Eye, EyeOff, CheckCircle } from 'lucide-react'
import AuthLayout from '../components/auth/AuthLayout'

export default function Register() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { register } = useAuth()

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const passwordValid = password.length >= 8
  const passwordsMatch = password === confirmPassword

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!username.trim() || !email.trim() || !password.trim()) {
      setError(t('auth.fillAllFields'))
      return
    }

    if (!passwordValid) {
      setError(t('auth.passwordTooShort'))
      return
    }

    if (!passwordsMatch) {
      setError(t('auth.passwordsNotMatch'))
      return
    }

    setLoading(true)
    setError(null)

    try {
      await register(username, email, password)
      navigate('/', { replace: true })
    } catch (err: unknown) {
      console.error('Registration error:', err)
      const axiosErr = err as { response?: { data?: { detail?: string | { msg: string }[] } } }
      const detail = axiosErr.response?.data?.detail

      if (typeof detail === 'string') {
        setError(detail)
      } else if (Array.isArray(detail)) {
        setError(detail.map((d: { msg: string }) => d.msg || String(d)).join(', '))
      } else {
        setError((err as { userMessage?: string }).userMessage || (err instanceof Error ? err.message : t('auth.registerError')))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      icon={<UserPlus className="w-6 h-6 sm:w-7 sm:h-7 lg:w-8 lg:h-8 2xl:w-9 2xl:h-9 text-accent" />}
      title={t('auth.createYourAccount')}
      subtitle={t('auth.joinSmartFinance')}
      footer={
        <p className="text-sm sm:text-base text-primary-400">
          {t('auth.hasAccount')}{' '}
          <Link to="/login" className="text-primary-500 hover:text-primary-400 font-medium">
            {t('auth.login')}
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
          <p className="text-xs sm:text-sm text-primary-500 mt-1.5 sm:mt-2">{t('auth.usernameHint')}</p>
        </div>

        <div>
          <label htmlFor="email" className="block text-sm sm:text-base font-medium text-primary-300 mb-1.5 sm:mb-2">
            {t('auth.email')}
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t('auth.enterEmail')}
            className="input h-11 sm:h-12 lg:h-14 text-sm sm:text-base sm:px-4 w-full"
            disabled={loading}
            autoComplete="email"
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
              placeholder={t('auth.createPassword')}
              className="input h-11 sm:h-12 lg:h-14 text-sm sm:text-base sm:px-4 w-full pr-11 sm:pr-12"
              disabled={loading}
              autoComplete="new-password"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 sm:right-4 top-1/2 -translate-y-1/2 text-primary-400 hover:text-primary-300"
            >
              {showPassword ? <EyeOff className="w-4 h-4 sm:w-5 sm:h-5" /> : <Eye className="w-4 h-4 sm:w-5 sm:h-5" />}
            </button>
          </div>
          {password && (
            <div className="flex items-center gap-1.5 mt-1.5 sm:mt-2">
              {passwordValid ? (
                <CheckCircle className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-green-500" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-yellow-500" />
              )}
              <span className={`text-xs sm:text-sm ${passwordValid ? 'text-green-500' : 'text-yellow-500'}`}>
                {passwordValid ? t('auth.passwordValid') : t('auth.passwordMinLength')}
              </span>
            </div>
          )}
        </div>

        <div>
          <label htmlFor="confirmPassword" className="block text-sm sm:text-base font-medium text-primary-300 mb-1.5 sm:mb-2">
            {t('auth.confirmPassword')}
          </label>
          <input
            id="confirmPassword"
            type={showPassword ? 'text' : 'password'}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder={t('auth.confirmYourPassword')}
            className="input h-11 sm:h-12 lg:h-14 text-sm sm:text-base sm:px-4 w-full"
            disabled={loading}
            autoComplete="new-password"
          />
          {confirmPassword && (
            <div className="flex items-center gap-1.5 mt-1.5 sm:mt-2">
              {passwordsMatch ? (
                <CheckCircle className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-green-500" />
              ) : (
                <AlertCircle className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-red-500" />
              )}
              <span className={`text-xs sm:text-sm ${passwordsMatch ? 'text-green-500' : 'text-red-500'}`}>
                {passwordsMatch ? t('auth.passwordsMatch') : t('auth.passwordsNotMatch')}
              </span>
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading || !username.trim() || !email.trim() || !passwordValid || !passwordsMatch}
          className="w-full h-11 sm:h-12 lg:h-14 flex items-center justify-center gap-2 px-5 sm:px-6 bg-accent hover:bg-[#74acff] disabled:bg-accent/40 disabled:cursor-not-allowed text-[#06121f] text-sm sm:text-base font-semibold rounded-lg transition-colors duration-150"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 sm:w-5 sm:h-5 animate-spin" />
              {t('auth.creatingAccount')}
            </>
          ) : (
            <>
              <UserPlus className="w-4 h-4 sm:w-5 sm:h-5" />
              {t('auth.register')}
            </>
          )}
        </button>
      </form>
    </AuthLayout>
  )
}
