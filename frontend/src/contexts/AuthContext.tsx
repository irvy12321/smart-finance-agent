import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import { authApi } from '../services/api'
import type { UserResponse, Token } from '../types/api'

interface AuthState {
  user: UserResponse | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshAccessToken: () => Promise<boolean>
  hasRole: (role: string) => boolean
  hasAnyRole: (roles: string[]) => boolean
  isAdmin: () => boolean
  isAnalyst: () => boolean
  isViewer: () => boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

const TOKEN_KEY = 'auth_token'
const REFRESH_TOKEN_KEY = 'auth_refresh_token'
const USER_KEY = 'auth_user'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(() => {
    // Load from localStorage on init
    const token = localStorage.getItem(TOKEN_KEY)
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    const userStr = localStorage.getItem(USER_KEY)
    let user
    try {
      user = userStr ? JSON.parse(userStr) : null
    } catch {
      user = null
    }
    return {
      user,
      token,
      refreshToken,
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
        setState(prev => ({
          ...prev,
          user,
          isAuthenticated: true,
          isLoading: false,
        }))
        localStorage.setItem(USER_KEY, JSON.stringify(user))
      } catch {
        // Token invalid, try refresh
        const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
        if (refreshToken) {
          try {
            const response = await authApi.refreshToken({ refresh_token: refreshToken })
            handleTokenResponse(response)
          } catch {
            // Refresh also failed, clear everything
            clearAuth()
          }
        } else {
          clearAuth()
        }
      }
    }

    verifyToken()
  }, [])

  const clearAuth = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setState({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
    })
  }

  const handleTokenResponse = (response: Token) => {
    const { access_token, refresh_token, user } = response
    localStorage.setItem(TOKEN_KEY, access_token)
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token)
    localStorage.setItem(USER_KEY, JSON.stringify(user))
    setState({
      user,
      token: access_token,
      refreshToken: refresh_token,
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

  const logout = async () => {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)

    // Try to revoke refresh token on server
    if (refreshToken) {
      try {
        await authApi.logout({ refresh_token: refreshToken })
      } catch {
        // Ignore errors - we'll clear local storage anyway
      }
    }

    clearAuth()
  }

  const refreshAccessToken = useCallback(async (): Promise<boolean> => {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    if (!refreshToken) {
      return false
    }

    try {
      const response = await authApi.refreshToken({ refresh_token: refreshToken })
      handleTokenResponse(response)
      return true
    } catch {
      // Refresh failed, clear auth
      clearAuth()
      return false
    }
  }, [])

  // Role-based access control helpers
  const hasRole = useCallback((role: string): boolean => {
    return state.user?.role === role
  }, [state.user])

  const hasAnyRole = useCallback((roles: string[]): boolean => {
    return roles.includes(state.user?.role || '')
  }, [state.user])

  const isAdmin = useCallback((): boolean => {
    return state.user?.role === 'admin'
  }, [state.user])

  const isAnalyst = useCallback((): boolean => {
    return state.user?.role === 'analyst'
  }, [state.user])

  const isViewer = useCallback((): boolean => {
    return state.user?.role === 'viewer'
  }, [state.user])

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        register,
        logout,
        refreshAccessToken,
        hasRole,
        hasAnyRole,
        isAdmin,
        isAnalyst,
        isViewer,
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
