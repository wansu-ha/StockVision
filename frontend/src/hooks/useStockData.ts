/** useStockData — 규칙 + 관심종목 + 현재가 병합.
 *
 * cloudRules → 내 종목 (규칙이 있는 종목)
 * cloudWatchlist → 관심 종목
 * cloudQuote → 각 종목 현재가
 */
import { useQuery } from '@tanstack/react-query'
import { cloudRules, cloudWatchlist, cloudQuote } from '../services/cloudClient'
import type { Rule } from '../types/strategy'
import type { WatchlistItem, StockQuote } from '../services/cloudClient'
import type { Stock } from '../components/main/ListView'

/** 규칙 목록에서 고유 종목 심볼 추출 */
function uniqueSymbols(rules: Rule[]): string[] {
  return [...new Set(rules.map(r => r.symbol))]
}

/** 종목 배열 생성 — 규칙/관심종목 + 현재가 병합 */
function buildStocks(
  symbols: string[],
  quotes: Map<string, StockQuote>,
  ruleCountMap: Map<string, number>,
): Stock[] {
  return symbols.map(sym => {
    const q = quotes.get(sym)
    return {
      symbol: sym,
      name: q?.symbol ?? sym,
      price: q?.price ?? 0,
      change: q?.change_pct ?? 0,
      rules: ruleCountMap.get(sym) ?? 0,
      lastTrade: '',
    }
  })
}

export function useStockData() {
  const rulesQuery = useQuery<Rule[]>({
    queryKey: ['rules'],
    queryFn: () => cloudRules.list(),
    refetchInterval: 30_000,
    retry: 1,
  })

  const watchlistQuery = useQuery<WatchlistItem[]>({
    queryKey: ['watchlist'],
    queryFn: () => cloudWatchlist.list(),
    refetchInterval: 30_000,
    retry: 1,
  })

  const rules = rulesQuery.data ?? []
  const watchlist = watchlistQuery.data ?? []

  // 규칙별 종목 카운트
  const ruleCountMap = new Map<string, number>()
  rules.forEach(r => {
    ruleCountMap.set(r.symbol, (ruleCountMap.get(r.symbol) ?? 0) + 1)
  })

  const mySymbols = uniqueSymbols(rules)
  const watchSymbols = watchlist.map(w => w.symbol)
  const allSymbols = [...new Set([...mySymbols, ...watchSymbols])]

  // 각 종목 현재가 — allSymbols가 변할 때만 fetch
  const quotesQuery = useQuery<Map<string, StockQuote>>({
    queryKey: ['quotes', allSymbols.sort().join(',')],
    queryFn: async () => {
      const results = await Promise.allSettled(
        allSymbols.map(sym => cloudQuote.get(sym))
      )
      const map = new Map<string, StockQuote>()
      results.forEach((r, i) => {
        if (r.status === 'fulfilled' && r.value) {
          map.set(allSymbols[i], r.value)
        }
      })
      return map
    },
    refetchInterval: 15_000,
    enabled: allSymbols.length > 0,
    retry: 1,
  })

  const quotes = quotesQuery.data ?? new Map<string, StockQuote>()

  return {
    myStocks: buildStocks(mySymbols, quotes, ruleCountMap),
    watchStocks: buildStocks(watchSymbols, quotes, ruleCountMap),
    rules,
    isLoading: rulesQuery.isLoading || watchlistQuery.isLoading,
    error: rulesQuery.error || watchlistQuery.error,
  }
}
