import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import StockPriceCard from '../components/StockPriceCard'
import { toolsApi } from '../services/api'

vi.mock('../services/api', () => ({
  toolsApi: {
    getStockPrice: vi.fn(),
  },
}))

describe('StockPriceCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders search input and popular stocks', () => {
    render(<StockPriceCard />)

    expect(screen.getByPlaceholderText('Enter stock symbol (e.g., AAPL)')).toBeInTheDocument()
    expect(screen.getByText('AAPL')).toBeInTheDocument()
    expect(screen.getByText('TSLA')).toBeInTheDocument()
    expect(screen.getByText('GOOGL')).toBeInTheDocument()
  })

  it('shows empty state initially', () => {
    render(<StockPriceCard />)

    expect(screen.getByText('Enter a stock symbol to get started')).toBeInTheDocument()
  })

  it('fetches and displays stock data', async () => {
    const mockStock = {
      symbol: 'AAPL',
      name: 'Apple Inc.',
      price: 170.59,
      change: 2.5,
      change_percent: 1.49,
      volume: 50000000,
      market_cap: 2800000000000,
      pe_ratio: 28.5,
      high_52w: 199.62,
      low_52w: 124.17,
      timestamp: '',
      source: '',
    }
    vi.mocked(toolsApi.getStockPrice).mockResolvedValueOnce(mockStock)

    const user = userEvent.setup()
    render(<StockPriceCard />)

    const input = screen.getByPlaceholderText('Enter stock symbol (e.g., AAPL)')
    await user.type(input, 'AAPL')
    await user.click(screen.getByRole('button', { name: '' }))

    await waitFor(() => {
      expect(screen.getByText('$170.59')).toBeInTheDocument()
    })
    expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
    expect(screen.getByText('+2.50 (1.49%)')).toBeInTheDocument()
  })

  it('displays error message on fetch failure', async () => {
    vi.mocked(toolsApi.getStockPrice).mockRejectedValueOnce(new Error('Network error'))

    const user = userEvent.setup()
    render(<StockPriceCard />)

    const input = screen.getByPlaceholderText('Enter stock symbol (e.g., AAPL)')
    await user.type(input, 'INVALID')
    await user.click(screen.getByRole('button', { name: '' }))

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })
  })

  it('calls onStockSelect when button clicked', async () => {
    const mockStock = {
      symbol: 'AAPL',
      name: 'Apple Inc.',
      price: 170.59,
      change: 0,
      change_percent: 0,
      volume: 0,
      market_cap: 0,
      pe_ratio: 0,
      high_52w: 0,
      low_52w: 0,
      timestamp: '',
      source: '',
    }
    vi.mocked(toolsApi.getStockPrice).mockResolvedValueOnce(mockStock)
    const onSelect = vi.fn()

    const user = userEvent.setup()
    render(<StockPriceCard onStockSelect={onSelect} />)

    const input = screen.getByPlaceholderText('Enter stock symbol (e.g., AAPL)')
    await user.type(input, 'AAPL')
    await user.click(screen.getByRole('button', { name: '' }))

    await waitFor(() => {
      expect(screen.getByText('$170.59')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Get Detailed Analysis'))
    expect(onSelect).toHaveBeenCalledWith('AAPL')
  })
})
