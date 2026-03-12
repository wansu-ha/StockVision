/**
 * StockAnalysisCard — 종목별 AI 분석 카드
 * 매일 07:00 KST 생성된 기술적 지표 기반 분석 요약 표시
 */
import { useQuery } from '@tanstack/react-query'
import { cloudAI, type StockAnalysis } from '../services/cloudClient'

const SENTIMENT_COLOR: Record<StockAnalysis['sentiment'], string> = {
  bearish:          'text-red-400',
  slightly_bearish: 'text-orange-400',
  neutral:          'text-gray-400',
  slightly_bullish: 'text-emerald-400',
  bullish:          'text-green-400',
}

const SENTIMENT_LABEL: Record<StockAnalysis['sentiment'], string> = {
  bearish:          '약세',
  slightly_bearish: '약간 약세',
  neutral:          '중립',
  slightly_bullish: '약간 강세',
  bullish:          '강세',
}

function Skeleton() {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 animate-pulse">
      <div className="h-3 bg-gray-800 rounded w-20 mb-3" />
      <div className="h-3 bg-gray-800 rounded w-full mb-2" />
      <div className="h-3 bg-gray-800 rounded w-3/4" />
    </div>
  )
}

interface Props {
  symbol: string
}

export default function StockAnalysisCard({ symbol }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['stockAnalysis', symbol],
    queryFn: () => cloudAI.getStockAnalysis(symbol),
    staleTime: 30 * 60 * 1000,
    retry: 1,
  })

  if (isLoading) return <Skeleton />

  const isStub = !data || data.source === 'stub' || !data.summary

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">AI 분석</span>
        {data && !isStub && (
          <span className={`text-xs font-semibold ${SENTIMENT_COLOR[data.sentiment]}`}>
            {SENTIMENT_LABEL[data.sentiment]}
          </span>
        )}
      </div>

      {isStub ? (
        <p className="text-sm text-gray-500">분석을 불러오지 못했습니다.</p>
      ) : (
        <>
          <p className="text-sm text-gray-300 leading-relaxed mb-2">{data!.summary}</p>
          {data!.generated_at && (
            <p className="text-xs text-gray-600">
              {new Date(data!.generated_at).toLocaleString('ko-KR', {
                month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit',
              })} 기준
            </p>
          )}
        </>
      )}
    </div>
  )
}
