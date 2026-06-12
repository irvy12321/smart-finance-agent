import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { ReactNode } from 'react'
import { AuthProvider, useAuth } from '../contexts/AuthContext'
import { authApi } from '../services/api'

vi.mock('../services/api', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    getMe: vi.fn(),
    refreshToken: vi.fn(),
  },
  taskApi: {},
  reportApi: {},
  systemApi: {},
  toolsApi: {},
  chatApi: {},
}))

const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('initializes with no auth when no token stored', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
    expect(result.current.token).toBeNull()
  })

  it('restores auth from localStorage on mount', async () => {
    const mockUser = { id: 1, username: 'test', email: 'test@test.com', role: 'viewer', is_active: true, created_at: '' }
    localStorage.setItem('auth_token', 'stored-token')
    localStorage.setItem('auth_user', JSON.stringify(mockUser))
    vi.mocked(authApi.getMe).mockResolvedValueOnce(mockUser)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user?.username).toBe('test')
  })

  it('logs in successfully', async () => {
    const mockResponse = {
      access_token: 'new-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer',
      expires_in: 86400,
      user: { id: 1, username: 'test', email: 'test@test.com', role: 'viewer', is_active: true, created_at: '' },
    }
    vi.mocked(authApi.login).mockResolvedValueOnce(mockResponse)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await act(async () => {
      await result.current.login('test', 'password123')
    })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.token).toBe('new-token')
    expect(localStorage.getItem('auth_token')).toBe('new-token')
  })

  it('registers successfully', async () => {
    const mockResponse = {
      access_token: 'reg-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer',
      expires_in: 86400,
      user: { id: 2, username: 'newuser', email: 'new@test.com', role: 'viewer', is_active: true, created_at: '' },
    }
    vi.mocked(authApi.register).mockResolvedValueOnce(mockResponse)

    const { result } = renderHook(() => useAuth(), { wrapper })

    await act(async () => {
      await result.current.register('newuser', 'new@test.com', 'password123')
    })

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.user?.username).toBe('newuser')
  })

  it('logs out successfully', async () => {
    localStorage.setItem('auth_token', 'token')
    localStorage.setItem('auth_user', '{"id":1}')

    const { result } = renderHook(() => useAuth(), { wrapper })

    act(() => {
      result.current.logout()
    })

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
    expect(localStorage.getItem('auth_token')).toBeNull()
  })

  it('handles failed token verification', async () => {
    localStorage.setItem('auth_token', 'invalid-token')
    localStorage.setItem('auth_user', '{"id":1}')
    vi.mocked(authApi.getMe).mockRejectedValueOnce(new Error('Unauthorized'))

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.isAuthenticated).toBe(false)
    expect(localStorage.getItem('auth_token')).toBeNull()
  })
})
