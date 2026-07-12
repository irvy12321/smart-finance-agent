import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { TrendingUp, TrendingDown, Loader2 } from 'lucide-react'
import { toolsApi } from '../../services/api'

interface MarketIndex {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
}

const marketSymbols = [
  { symbol: 'SPY', name: 'S&P 500' },
  { symbol: 'QQQ', name: 'NASDAQ' },
  { symbol: 'DIA', name: 'DOW JONES' },
  { symbol: 'VIX', name: 'VIX' },
]

export default function MarketOverview() {
  const { t } = useTranslation()
  const [data, setData] = useState<MarketIndex[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchMarketData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const results = await Promise.allSettled(
        marketSymbols.map(async (s) => {
          try {
            const stock = await toolsApi.getStockPrice(s.symbol)
            return {
              symbol: s.symbol,
              name: s.name,
              price: stock.price || 0,
              change: stock.change || 0,
              changePercent: stock.change_percent || 0,
            }
          } catch {
            return {
              symbol: s.symbol,
              name: s.name,
              price: 0,
              change: 0,
              changePercent: 0,
            }
          }
        })
      )

      const validData = results
        .filter((r): r is PromiseFulfilledResult<MarketIndex> => r.status === 'fulfilled')
        .map(r => r.value)

      setData(validData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch market data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMarketData()
  }, [fetchMarketData])

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {marketSymbols.map((s) => (
          <div key={s.symbol} className="min-h-28 bg-dark-card border border-dark-border rounded-lg p-4 flex items-center justify-center">
            <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />
          </div>
        ))}
      </div>
    )
  }

  if (error || data.length === 0) {
    return (
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
        {marketSymbols.map((s) => (
          <div key={s.symbol} className="min-h-28 bg-dark-card border border-dark-border rounded-lg p-4">
            <div className="text-sm text-primary-400 font-medium">{s.name}</div>
            <div className="text-sm text-primary-500 mt-2">{t('common.noData')}</div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
      {data.map((index) => {
        const isPositive = index.change >= 0
        return (
          <div key={index.symbol} className="min-h-28 bg-dark-card border border-dark-border rounded-lg p-4">
            <div className="flex items-center justify-between gap-4 mb-2">
              <span className="text-sm text-primary-400 font-medium">{index.name}</span>
              <div className="w-8 h-8 rounded-lg bg-dark-bg border border-dark-border flex items-center justify-center">
                {isPositive ? (
                  <TrendingUp className="w-4 h-4 text-green-400" />
                ) : (
                  <TrendingDown className="w-4 h-4 text-red-400" />
                )}
              </div>
            </div>
            <div className="text-2xl font-bold text-primary-50 font-mono">
              {index.price > 0 ? index.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '--'}
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span className={`text-sm font-mono ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                {isPositive ? '+' : ''}{index.change.toFixed(2)}
              </span>
              <span className={`text-sm font-mono px-2 py-0.5 rounded ${
                isPositive ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
              }`}>
                {isPositive ? '+' : ''}{index.changePercent.toFixed(1)}%
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
