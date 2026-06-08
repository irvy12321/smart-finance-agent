import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authApi } from '../services/api'
import type { UserResponse, Token } from '../types/api'

interface AuthState {
  user: UserResponse | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(() => {
    // Load from localStorage on init
    const token = localStorage.getItem(TOKEN_KEY)
    const userStr = localStorage.getItem(USER_KEY)
    let user = null
    try {
      user = userStr ? JSON.parse(userStr) : null
    } catch {
      user = null
    }
    return {
      user,
      token,
      isAuthenticated: !!token,
      isLoading: true,
    }
  })

  // Verify token on mount
  useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem(TOKEN_KEY)
      if (!token) {
        setState(prev => ({ ...prev, isLoading: false }))
        return
      }

      try {
        const user = await authApi.getMe()
        setState({
          user,
          token,
          isAuthenticated: true,
          isLoading: false,
        })
        localStorage.setItem(USER_KEY, JSON.stringify(user))
      } catch {
        // Token invalid or expired
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_KEY)
        setState({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
        })
      }
    }

    verifyToken()
  }, [])

  const handleTokenResponse = (response: Token) => {
    const { access_token, user } = response
    localStorage.setItem(TOKEN_KEY, access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(user))
    setState({
      user,
      token: access_token,
      isAuthenticated: true,
      isLoading: false,
    })
  }

  const login = async (username: string, password: string) => {
    const response = await authApi.login({ username, password })
    handleTokenResponse(response)
  }

  const register = async (username: string, email: string, password: string) => {
    const response = await authApi.register({ username, email, password })
    handleTokenResponse(response)
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
    })
  }

  const refreshToken = async () => {
    try {
      const response = await authApi.refreshToken()
      handleTokenResponse(response)
    } catch {
      logout()
    }
  }

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        register,
        logout,
        refreshToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
