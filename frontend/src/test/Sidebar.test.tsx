import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import { useAuth } from '../contexts/AuthContext'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockAuthReturn = {
  isAuthenticated: true,
  isLoading: false,
  user: { id: 1, username: 'testuser', email: 'test@example.com', role: 'viewer' as const, is_active: true, created_at: '' },
  token: 'test-token',
  refreshToken: 'refresh-token',
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  refreshAccessToken: vi.fn(),
  hasRole: vi.fn(),
  hasAnyRole: vi.fn(),
  isAdmin: vi.fn(),
  isAnalyst: vi.fn(),
  isViewer: vi.fn(),
}

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuth).mockReturnValue(mockAuthReturn)
  })

  it('renders the logo and title', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    expect(screen.getByText('Smart Finance')).toBeInTheDocument()
    expect(screen.getByText('RESEARCH PLATFORM')).toBeInTheDocument()
  })

  it('renders navigation links', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Research')).toBeInTheDocument()
    expect(screen.getByText('Chat')).toBeInTheDocument()
    expect(screen.getByText('System')).toBeInTheDocument()
  })

  it('renders system status section', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    expect(screen.getByText('System Status')).toBeInTheDocument()
    expect(screen.getByText('Orchestrator Active')).toBeInTheDocument()
    expect(screen.getByText('API Connected')).toBeInTheDocument()
  })

  it('renders user info', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    expect(screen.getByText('testuser')).toBeInTheDocument()
    expect(screen.getByText('test@example.com')).toBeInTheDocument()
  })

  it('renders sign out button', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    expect(screen.getByText('Sign Out')).toBeInTheDocument()
  })

  it('calls logout when sign out clicked', () => {
    const mockLogout = vi.fn()
    vi.mocked(useAuth).mockReturnValue({
      ...mockAuthReturn,
      logout: mockLogout,
    })

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    screen.getByText('Sign Out').click()
    expect(mockLogout).toHaveBeenCalled()
  })

  it('highlights active navigation item', () => {
    render(
      <MemoryRouter initialEntries={['/research']}>
        <Sidebar />
      </MemoryRouter>
    )

    const researchLink = screen.getByText('Research').closest('a')
    expect(researchLink).toHaveClass('bg-primary-500/10', 'text-primary-500')
  })

  it('shows default user when no user logged in', () => {
    vi.mocked(useAuth).mockReturnValue({
      ...mockAuthReturn,
      isAuthenticated: false,
      user: null,
      token: null,
      refreshToken: null,
    })

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    expect(screen.getByText('Username')).toBeInTheDocument()
  })
})
