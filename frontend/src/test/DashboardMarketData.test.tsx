import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import MarketOverview from '../components/dashboard/MarketOverview'
import HotStocksList from '../components/dashboard/HotStocksList'
import { toolsApi } from '../services/api'

vi.mock('../services/api', () => ({
  toolsApi: {
    getStockPrice: vi.fn(),
  },
}))

const simulatedQuote = {
  symbol: 'AAPL',
  name: 'Demo Corp.',
  price: 182.52,
  change: 1.25,
  change_percent: 0.69,
  volume: 52_345_678,
  market_cap: 2_850_000_000_000,
  pe_ratio: 28.5,
  high_52w: 199.62,
  low_52w: 124.17,
  timestamp: '2026-07-27T12:00:00',
  source: 'mock',
  is_mock: true,
  warning: 'SIMULATED DATA - NOT FOR INVESTMENT',
}

describe('dashboard market data', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('labels every simulated market quote', async () => {
    vi.mocked(toolsApi.getStockPrice).mockResolvedValue(simulatedQuote)

    render(<MarketOverview />)

    expect(await screen.findAllByText('Simulated')).toHaveLength(4)
    expect(screen.getAllByText('182.52')).toHaveLength(4)
  })

  it('renders request failures as unavailable instead of positive zero changes', async () => {
    vi.mocked(toolsApi.getStockPrice).mockRejectedValue(new Error('rate limited'))

    render(<MarketOverview />)

    expect(await screen.findAllByText('Data unavailable')).toHaveLength(4)
    expect(screen.queryByText('+0.0%')).not.toBeInTheDocument()
  })

  it('refetches market data when the dashboard refresh key changes', async () => {
    vi.mocked(toolsApi.getStockPrice).mockResolvedValue(simulatedQuote)
    const { rerender } = render(<MarketOverview refreshKey={0} />)

    await waitFor(() => expect(toolsApi.getStockPrice).toHaveBeenCalledTimes(4))
    rerender(<MarketOverview refreshKey={1} />)
    await waitFor(() => expect(toolsApi.getStockPrice).toHaveBeenCalledTimes(8))
  })

  it('labels simulated stock rows', async () => {
    vi.mocked(toolsApi.getStockPrice).mockResolvedValue(simulatedQuote)

    render(<HotStocksList />)

    expect(await screen.findAllByText('Simulated')).toHaveLength(8)
  })
})
