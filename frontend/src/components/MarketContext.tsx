import { useQuery } from '@tanstack/react-query'
import { cloudContext } from '../services/cloudClient'

export default function MarketContext() {
  const { data: ctx } = useQuery({
    queryKey: ['market-context'],
    queryFn:  cloudContext.get,
    refetchInterval: 60_000,
    retry: false,
    staleTime: 60_000,
  })

  if (!ctx) return null

  const rsi = ctx.kospi_rsi ?? null
  const trend = ctx.trend ?? null

  const rsiLabel =
    rsi === null ? '—' :
    rsi < 30     ? `${rsi.toFixed(1)} (과매도)` :
    rsi > 70     ? `${rsi.toFixed(1)} (과매수)` :
    rsi.toFixed(1)

  const trendLabel: Record<string, string> = {
    bullish:  '상승 추세',
    bearish:  '하락 조정',
    neutral:  '중립',
  }

  return (
    <div className="bg-white rounded-xl shadow p-4">
      <h3 className="text-sm font-semibold text-gray-600 mb-3">시장 컨텍스트</h3>
      <dl className="space-y-1 text-sm">
        <div className="flex justify-between">
          <dt className="text-gray-500">KOSPI RSI(14)</dt>
          <dd className={`font-medium ${rsi !== null && rsi < 30 ? 'text-blue-600' : rsi !== null && rsi > 70 ? 'text-red-600' : ''}`}>
            {rsiLabel}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-500">시장 흐름</dt>
          <dd className="font-medium">{trend ? (trendLabel[trend] ?? trend) : '—'}</dd>
        </div>
      </dl>
    </div>
  )
}
