import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import { useAuth } from '../contexts/AuthContext'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

describe('Sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
      user: { id: 1, username: 'testuser', email: 'test@example.com', is_active: true, created_at: '' },
      token: 'test-token',
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn(),
    })
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
      isAuthenticated: true,
      isLoading: false,
      user: { id: 1, username: 'testuser', email: 'test@example.com', is_active: true, created_at: '' },
      token: 'test-token',
      login: vi.fn(),
      register: vi.fn(),
      logout: mockLogout,
      refreshToken: vi.fn(),
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
      isAuthenticated: false,
      isLoading: false,
      user: null,
      token: null,
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn(),
    })

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    )

    expect(screen.getByText('Username')).toBeInTheDocument()
  })
})