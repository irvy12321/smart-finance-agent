import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { TrendingUp, TrendingDown, ExternalLink, Loader2 } from 'lucide-react'
import { toolsApi } from '../../services/api'

interface Stock {
  symbol: string
  name: string
  price: number
  change: number
  changePercent: number
  volume: number
}

const stockSymbols = [
  { symbol: 'AAPL', name: 'Apple Inc.' },
  { symbol: 'NVDA', name: 'NVIDIA Corp.' },
  { symbol: 'TSLA', name: 'Tesla Inc.' },
  { symbol: 'MSFT', name: 'Microsoft Corp.' },
  { symbol: 'META', name: 'Meta Platforms' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.' },
  { symbol: 'AMZN', name: 'Amazon.com' },
  { symbol: 'JPM', name: 'JPMorgan Chase' },
]

export default function HotStocksList() {
  const { t } = useTranslation()
  const [stocks, setStocks] = useState<Stock[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStocks = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const results = await Promise.allSettled(
        stockSymbols.map(async (s) => {
          try {
            const data = await toolsApi.getStockPrice(s.symbol)
            return {
              symbol: s.symbol,
              name: s.name,
              price: data.price || 0,
              change: data.change || 0,
              changePercent: data.change_percent || 0,
              volume: data.volume || 0,
            }
          } catch {
            return {
              symbol: s.symbol,
              name: s.name,
              price: 0,
              change: 0,
              changePercent: 0,
              volume: 0,
            }
          }
        })
      )

      const validStocks = results
        .filter((r): r is PromiseFulfilledResult<Stock> => r.status === 'fulfilled')
        .map(r => r.value)

      setStocks(validStocks)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch stocks')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStocks()
  }, [fetchStocks])

  const formatVolume = (vol: number) => {
    if (vol >= 1000000) return `${(vol / 1000000).toFixed(0)}M`
    if (vol >= 1000) return `${(vol / 1000).toFixed(0)}K`
    return vol.toString()
  }

  if (loading) {
    return (
      <div className="h-full bg-dark-card border border-dark-border rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 border-b border-dark-border">
          <span className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('stock.popularStocks')}</span>
        </div>
        <div className="p-8 flex items-center justify-center">
          <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
        </div>
      </div>
    )
  }

  if (error || stocks.length === 0) {
    return (
      <div className="h-full bg-dark-card border border-dark-border rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 border-b border-dark-border">
          <span className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('stock.popularStocks')}</span>
        </div>
        <div className="p-4 text-center text-xs text-primary-500">
          {error || t('common.noData')}
        </div>
      </div>
    )
  }

  return (
    <div className="h-full bg-dark-card border border-dark-border rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-dark-border">
        <span className="text-xs font-semibold text-primary-300 uppercase tracking-wider">{t('stock.popularStocks')}</span>
        <button
          onClick={fetchStocks}
          className="text-xs text-primary-500 hover:text-primary-300 flex items-center gap-1"
        >
          {t('common.viewAll')} <ExternalLink className="w-3 h-3" />
        </button>
      </div>
      <div className="min-w-0 overflow-x-auto">
        <table className="w-full min-w-[560px]">
          <thead>
            <tr className="text-xs text-primary-500 border-b border-dark-border">
              <th className="text-left px-3 py-2 font-medium">{t('stock.symbol')}</th>
              <th className="text-right px-3 py-2 font-medium">{t('stock.price')}</th>
              <th className="text-right px-3 py-2 font-medium">{t('stock.change')}</th>
              <th className="text-right px-3 py-2 font-medium">{t('stock.volume')}</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((stock) => {
              const isPositive = stock.change >= 0
              return (
                <tr key={stock.symbol} className="border-b border-dark-border hover:bg-dark-bg/50 cursor-pointer transition-colors">
                  <td className="px-3 py-2">
                    <div>
                      <span className="text-xs font-bold text-primary-200">{stock.symbol}</span>
                      <span className="text-xs text-primary-500 ml-2 hidden lg:inline">{stock.name}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <span className="text-xs font-mono text-primary-200">
                      {stock.price > 0 ? `$${stock.price.toFixed(2)}` : '--'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {isPositive ? (
                        <TrendingUp className="w-3 h-3 text-green-400" />
                      ) : (
                        <TrendingDown className="w-3 h-3 text-red-400" />
                      )}
                      <span className={`text-xs font-mono ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                        {isPositive ? '+' : ''}{stock.changePercent.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <span className="text-xs font-mono text-primary-400">
                      {stock.volume > 0 ? formatVolume(stock.volume) : '--'}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
