import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import StockPool from '../components/research/StockPool'
import { toolsApi } from '../services/api'

vi.mock('../services/api', () => ({
  toolsApi: {
    getStockPrice: vi.fn(),
  },
}))

const simulatedQuote = {
  symbol: 'AAPL',
  name: 'Apple Inc.',
  price: 182.52,
  change: 1.25,
  change_percent: 0.69,
  volume: 50000000,
  market_cap: 2800000000000,
  pe_ratio: 28.5,
  high_52w: 199.62,
  low_52w: 124.17,
  timestamp: '',
  source: 'mock',
  is_mock: true,
  warning: 'SIMULATED DATA - NOT FOR INVESTMENT',
}

describe('StockPool market data states', () => {
  beforeEach(() => vi.clearAllMocks())

  it('labels every simulated quote', async () => {
    vi.mocked(toolsApi.getStockPrice).mockResolvedValue(simulatedQuote)
    render(<StockPool selectedSymbol={null} onSelect={vi.fn()} />)

    await waitFor(() => expect(toolsApi.getStockPrice).toHaveBeenCalledTimes(8))
    expect(await screen.findAllByText('Simulated')).toHaveLength(8)
  })

  it('shows unavailable instead of zero when quote requests fail', async () => {
    vi.mocked(toolsApi.getStockPrice).mockRejectedValue(new Error('rate limited'))
    render(<StockPool selectedSymbol={null} onSelect={vi.fn()} />)

    expect(await screen.findAllByText('Data unavailable')).toHaveLength(8)
    expect(screen.queryByText('$0.00')).not.toBeInTheDocument()
    expect(screen.queryByText('+0.0%')).not.toBeInTheDocument()
  })
})
