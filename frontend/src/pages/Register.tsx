import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../contexts/AuthContext'
import { UserPlus, Loader2, AlertCircle, Eye, EyeOff, CheckCircle } from 'lucide-react'

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
    <div className="min-h-screen flex items-center justify-center bg-dark-bg px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-primary-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <UserPlus className="w-8 h-8 text-primary-500" />
          </div>
          <h1 className="text-2xl font-bold text-primary-50">{t('auth.createYourAccount')}</h1>
          <p className="text-sm text-primary-400 mt-2">{t('auth.joinSmartFinance')}</p>
        </div>

        {/* Form */}
        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Error */}
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            {/* Username */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-primary-300 mb-1.5">
                {t('auth.username')}
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={t('auth.enterUsername')}
                className="input w-full"
                disabled={loading}
                autoComplete="username"
              />
              <p className="text-xs text-primary-500 mt-1">{t('auth.usernameHint')}</p>
            </div>

            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-primary-300 mb-1.5">
                {t('auth.email')}
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t('auth.enterEmail')}
                className="input w-full"
                disabled={loading}
                autoComplete="email"
              />
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-primary-300 mb-1.5">
                {t('auth.password')}
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={t('auth.createPassword')}
                  className="input w-full pr-10"
                  disabled={loading}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-primary-400 hover:text-primary-300"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {password && (
                <div className="flex items-center gap-1 mt-1">
                  {passwordValid ? (
                    <CheckCircle className="w-3 h-3 text-green-500" />
                  ) : (
                    <AlertCircle className="w-3 h-3 text-yellow-500" />
                  )}
                  <span className={`text-xs ${passwordValid ? 'text-green-500' : 'text-yellow-500'}`}>
                    {passwordValid ? t('auth.passwordValid') : t('auth.passwordMinLength')}
                  </span>
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-primary-300 mb-1.5">
                {t('auth.confirmPassword')}
              </label>
              <input
                id="confirmPassword"
                type={showPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder={t('auth.confirmYourPassword')}
                className="input w-full"
                disabled={loading}
                autoComplete="new-password"
              />
              {confirmPassword && (
                <div className="flex items-center gap-1 mt-1">
                  {passwordsMatch ? (
                    <CheckCircle className="w-3 h-3 text-green-500" />
                  ) : (
                    <AlertCircle className="w-3 h-3 text-red-500" />
                  )}
                  <span className={`text-xs ${passwordsMatch ? 'text-green-500' : 'text-red-500'}`}>
                    {passwordsMatch ? t('auth.passwordsMatch') : t('auth.passwordsNotMatch')}
                  </span>
                </div>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !username.trim() || !email.trim() || !passwordValid || !passwordsMatch}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 disabled:from-primary-500/50 disabled:to-primary-600/50 disabled:cursor-not-allowed text-white font-semibold rounded-xl shadow-lg shadow-primary-500/25 transition-all duration-200 hover:shadow-primary-500/40 hover:scale-[1.02] disabled:hover:scale-100"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {t('auth.creatingAccount')}
                </>
              ) : (
                <>
                  <UserPlus className="w-5 h-5" />
                  {t('auth.register')}
                </>
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="mt-6 pt-4 border-t border-dark-border text-center">
            <p className="text-sm text-primary-400">
              {t('auth.hasAccount')}{' '}
              <Link to="/login" className="text-primary-500 hover:text-primary-400 font-medium">
                {t('auth.login')}
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
