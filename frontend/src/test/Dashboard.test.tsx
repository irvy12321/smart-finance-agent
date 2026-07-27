import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import Dashboard from '../pages/Dashboard'

vi.mock('../components/layout', () => ({
  PageHeader: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}))

vi.mock('../components/dashboard', () => ({
  MarketOverview: ({ refreshKey }: { refreshKey: number }) => (
    <div data-testid="market-refresh-key">{refreshKey}</div>
  ),
  HotStocksList: ({ refreshKey }: { refreshKey: number }) => (
    <div data-testid="stocks-refresh-key">{refreshKey}</div>
  ),
  AIMarketInsight: () => <div />,
  RiskMetrics: () => <div />,
  RecentTasks: () => <div />,
}))

describe('Dashboard', () => {
  it('refreshes both market sections from the header button', async () => {
    const user = userEvent.setup()
    render(<Dashboard />)

    expect(screen.getByTestId('market-refresh-key')).toHaveTextContent('0')
    expect(screen.getByTestId('stocks-refresh-key')).toHaveTextContent('0')

    await user.click(screen.getByRole('button', { name: 'Refresh' }))

    expect(screen.getByTestId('market-refresh-key')).toHaveTextContent('1')
    expect(screen.getByTestId('stocks-refresh-key')).toHaveTextContent('1')
  })
})
