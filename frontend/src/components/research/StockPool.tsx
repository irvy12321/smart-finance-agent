import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Search, Star, TrendingUp, TrendingDown, Loader2 } from 'lucide-react'
import { toolsApi } from '../../services/api'

interface Stock {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  isFavorite: boolean
}

const defaultStocks = [
  { symbol: 'AAPL', name: 'Apple Inc.', isFavorite: true },
  { symbol: 'TSLA', name: 'Tesla Inc.', isFavorite: true },
  { symbol: 'NVDA', name: 'NVIDIA Corp.', isFavorite: true },
  { symbol: 'MSFT', name: 'Microsoft Corp.', isFavorite: false },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', isFavorite: false },
  { symbol: 'META', name: 'Meta Platforms', isFavorite: false },
  { symbol: 'AMZN', name: 'Amazon.com', isFavorite: false },
  { symbol: 'JPM', name: 'JPMorgan Chase', isFavorite: false },
]

interface StockPoolProps {
  selectedSymbol: string | null
  onSelect: (symbol: string) => void
}

export default function StockPool({ selectedSymbol, onSelect }: StockPoolProps) {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const [showFavorites, setShowFavorites] = useState(false)
  const [stocks, setStocks] = useState<Stock[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStockPrices = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const stockData = await Promise.allSettled(
        defaultStocks.map(async (s) => {
          try {
            const data = await toolsApi.getStockPrice(s.symbol)
            return {
              symbol: s.symbol,
              name: s.name,
              price: data.price || 0,
              change: data.change || 0,
              changePercent: data.change_percent || 0,
              isFavorite: s.isFavorite,
            }
          } catch {
            return {
              symbol: s.symbol,
              name: s.name,
              price: 0,
              change: 0,
              changePercent: 0,
              isFavorite: s.isFavorite,
            }
          }
        })
      )

      const validStocks = stockData
        .filter((r): r is PromiseFulfilledResult<Stock> => r.status === 'fulfilled')
        .map(r => r.value)

      setStocks(validStocks)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch stock data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStockPrices()
  }, [fetchStockPrices])

  const filteredStocks = stocks.filter(s => {
    const matchesSearch = s.symbol.toLowerCase().includes(search.toLowerCase()) ||
                         s.name.toLowerCase().includes(search.toLowerCase())
    const matchesFilter = !showFavorites || s.isFavorite
    return matchesSearch && matchesFilter
  })

  if (loading) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg h-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-6 h-6 text-primary-500 animate-spin mx-auto mb-2" />
          <p className="text-xs text-primary-400">{t('common.loading')}</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-dark-card border border-dark-border rounded-lg h-full flex items-center justify-center">
        <div className="text-center text-red-400">
          <p className="text-xs">{error}</p>
          <button
            onClick={fetchStockPrices}
            className="mt-2 text-xs text-primary-500 hover:text-primary-300"
          >
            {t('common.refresh')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-dark-card border border-dark-border rounded-lg overflow-hidden h-full flex flex-col">
      {/* Header */}
      <div className="px-3 py-2 border-b border-dark-border">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('stock.popularStocks')}</span>
          <button
            onClick={() => setShowFavorites(!showFavorites)}
            className={`text-xs px-2 py-0.5 rounded transition-colors ${
              showFavorites ? 'bg-yellow-500/10 text-yellow-400' : 'text-primary-500 hover:text-primary-300'
            }`}
          >
            <Star className="w-3 h-3 inline mr-1" />
            Favorites
          </button>
        </div>
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-primary-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('stock.searchPlaceholder')}
            className="w-full h-7 pl-8 pr-3 bg-dark-bg border border-dark-border rounded text-xs text-primary-200 placeholder:text-primary-500 focus:outline-none focus:border-primary-500"
          />
        </div>
      </div>

      {/* Stock List */}
      <div className="flex-1 overflow-auto divide-y divide-dark-border">
        {filteredStocks.length === 0 ? (
          <div className="p-4 text-center text-xs text-primary-500">
            {t('common.noData')}
          </div>
        ) : (
          filteredStocks.map((stock) => {
            const isPositive = stock.change >= 0
            const isSelected = selectedSymbol === stock.symbol
            return (
              <button
                key={stock.symbol}
                onClick={() => onSelect(stock.symbol)}
                className={`w-full flex items-center justify-between px-3 py-2 transition-colors ${
                  isSelected ? 'bg-primary-500/10 border-l-2 border-primary-500' : 'hover:bg-dark-bg/50 border-l-2 border-transparent'
                }`}
              >
                <div className="flex items-center gap-2">
                  {stock.isFavorite && <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />}
                  <div className="text-left">
                    <div className="text-xs font-bold text-primary-200">{stock.symbol}</div>
                    <div className="text-xs text-primary-500 truncate max-w-[100px]">{stock.name}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-mono text-primary-200">${stock.price.toFixed(2)}</div>
                  <div className={`text-xs font-mono flex items-center justify-end gap-0.5 ${
                    isPositive ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                    {isPositive ? '+' : ''}{stock.changePercent.toFixed(1)}%
                  </div>
                </div>
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
