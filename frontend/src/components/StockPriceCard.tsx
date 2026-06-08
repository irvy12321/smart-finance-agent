import { useState } from 'react'
import { 
  TrendingUp, 
  TrendingDown, 
  Loader2, 
  Search,
  DollarSign,
  BarChart3,
  Activity
} from 'lucide-react'
import { toolsApi } from '../services/api'
import type { StockPriceResponse } from '../types/api'

interface StockPriceCardProps {
  onStockSelect?: (symbol: string) => void
}

export default function StockPriceCard({ onStockSelect }: StockPriceCardProps) {
  const [symbol, setSymbol] = useState('')
  const [stockData, setStockData] = useState<StockPriceResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const popularStocks = ['AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN', 'NVDA', 'META']

  const handleSearch = async (searchSymbol?: string) => {
    const targetSymbol = searchSymbol || symbol
    if (!targetSymbol.trim()) return

    setLoading(true)
    setError(null)

    try {
      const data = await toolsApi.getStockPrice(targetSymbol.toUpperCase())
      setStockData(data)
      setSymbol(targetSymbol.toUpperCase())
    } catch (err: any) {
      setError(err.message || 'Failed to fetch stock data')
      setStockData(null)
    } finally {
      setLoading(false)
    }
  }

  const formatNumber = (num: number) => {
    if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`
    if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`
    if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`
    return `$${num.toLocaleString()}`
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center">
            <DollarSign className="w-5 h-5 text-green-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-primary-50">Stock Price</h3>
            <p className="text-xs text-primary-400">Real-time market data</p>
          </div>
        </div>
      </div>

      {/* Search Input */}
      <div className="flex gap-2 mb-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-primary-400" />
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Enter stock symbol (e.g., AAPL)"
            className="w-full pl-10 pr-4 py-2.5 bg-dark-bg border border-dark-border rounded-lg text-primary-200 placeholder-primary-400 focus:outline-none focus:border-primary-500"
          />
        </div>
        <button
          onClick={() => handleSearch()}
          disabled={loading || !symbol.trim()}
          className="px-4 py-2.5 bg-primary-500 hover:bg-primary-600 disabled:bg-primary-500/50 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-2"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Search className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Popular Stocks */}
      <div className="flex flex-wrap gap-2 mb-4">
        {popularStocks.map((s) => (
          <button
            key={s}
            onClick={() => {
              setSymbol(s)
              handleSearch(s)
            }}
            className="px-3 py-1.5 text-xs font-medium text-primary-300 bg-dark-bg border border-dark-border rounded-lg hover:border-primary-500/30 hover:text-primary-200 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg mb-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Stock Data */}
      {stockData && (
        <div className="space-y-4">
          {/* Price Header */}
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-2xl font-bold text-primary-50">${stockData.price.toFixed(2)}</h4>
              <p className="text-sm text-primary-400">{stockData.name}</p>
            </div>
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
              stockData.change >= 0 ? 'bg-green-500/10' : 'bg-red-500/10'
            }`}>
              {stockData.change >= 0 ? (
                <TrendingUp className="w-4 h-4 text-green-500" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-500" />
              )}
              <span className={`text-sm font-semibold ${
                stockData.change >= 0 ? 'text-green-500' : 'text-red-500'
              }`}>
                {stockData.change >= 0 ? '+' : ''}{stockData.change.toFixed(2)} ({stockData.change_percent.toFixed(2)}%)
              </span>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
              <div className="flex items-center gap-2 mb-1">
                <BarChart3 className="w-4 h-4 text-primary-400" />
                <p className="text-xs text-primary-400">Volume</p>
              </div>
              <p className="text-sm font-semibold text-primary-200">
                {stockData.volume.toLocaleString()}
              </p>
            </div>
            <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
              <div className="flex items-center gap-2 mb-1">
                <DollarSign className="w-4 h-4 text-primary-400" />
                <p className="text-xs text-primary-400">Market Cap</p>
              </div>
              <p className="text-sm font-semibold text-primary-200">
                {formatNumber(stockData.market_cap)}
              </p>
            </div>
            <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
              <div className="flex items-center gap-2 mb-1">
                <Activity className="w-4 h-4 text-primary-400" />
                <p className="text-xs text-primary-400">P/E Ratio</p>
              </div>
              <p className="text-sm font-semibold text-primary-200">
                {stockData.pe_ratio.toFixed(2)}
              </p>
            </div>
            <div className="p-3 bg-dark-bg rounded-lg border border-dark-border">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="w-4 h-4 text-primary-400" />
                <p className="text-xs text-primary-400">52W Range</p>
              </div>
              <p className="text-sm font-semibold text-primary-200">
                ${stockData.low_52w.toFixed(2)} - ${stockData.high_52w.toFixed(2)}
              </p>
            </div>
          </div>

          {/* Action Button */}
          {onStockSelect && (
            <button
              onClick={() => onStockSelect(stockData.symbol)}
              className="w-full py-2.5 text-sm font-medium text-primary-500 bg-primary-500/10 rounded-lg hover:bg-primary-500/20 transition-colors"
            >
              Get Detailed Analysis
            </button>
          )}
        </div>
      )}

      {/* Empty State */}
      {!stockData && !loading && !error && (
        <div className="text-center py-8">
          <DollarSign className="w-12 h-12 text-primary-400/30 mx-auto mb-3" />
          <p className="text-sm text-primary-400">Enter a stock symbol to get started</p>
        </div>
      )}
    </div>
  )
}