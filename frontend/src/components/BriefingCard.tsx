/**
 * BriefingCard — 시장 브리핑 카드
 * 매일 06:00 KST 생성된 시황 요약 + 주요 지수 표시
 */
import { useQuery } from '@tanstack/react-query'
import { cloudAI, type MarketBriefing } from '../services/cloudClient'

const SENTIMENT_COLOR: Record<MarketBriefing['sentiment'], string> = {
  bearish:          'text-red-400',
  slightly_bearish: 'text-orange-400',
  neutral:          'text-gray-400',
  slightly_bullish: 'text-emerald-400',
  bullish:          'text-green-400',
}

const SENTIMENT_LABEL: Record<MarketBriefing['sentiment'], string> = {
  bearish:          '약세',
  slightly_bearish: '약간 약세',
  neutral:          '중립',
  slightly_bullish: '약간 강세',
  bullish:          '강세',
}

function IndexBadge({ label, close, changePct }: { label: string; close: number | null; changePct: number | null }) {
  if (close == null) return null
  const pos = (changePct ?? 0) >= 0
  return (
    <div className="flex items-center gap-1.5 text-xs">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-200 font-medium">{close.toLocaleString('ko-KR')}</span>
      {changePct != null && (
        <span className={pos ? 'text-emerald-400' : 'text-red-400'}>
          {pos ? '+' : ''}{changePct.toFixed(2)}%
        </span>
      )}
    </div>
  )
}

function Skeleton() {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-3 animate-pulse">
      <div className="h-3 bg-gray-800 rounded w-24 mb-3" />
      <div className="h-3 bg-gray-800 rounded w-full mb-2" />
      <div className="h-3 bg-gray-800 rounded w-3/4 mb-2" />
      <div className="h-3 bg-gray-800 rounded w-1/2" />
    </div>
  )
}

export default function BriefingCard() {
  const { data, isLoading } = useQuery({
    queryKey: ['marketBriefing'],
    queryFn: () => cloudAI.getBriefing(),
    staleTime: 30 * 60 * 1000,   // 30분
    retry: 1,
  })

  if (isLoading) return <Skeleton />

  const isStub = !data || data.source === 'stub'

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">시장 브리핑</span>
        {data && !isStub && (
          <span className={`text-xs font-semibold ${SENTIMENT_COLOR[data.sentiment]}`}>
            {SENTIMENT_LABEL[data.sentiment]}
          </span>
        )}
      </div>

      {isStub ? (
        <p className="text-sm text-gray-500">브리핑을 불러오지 못했습니다.</p>
      ) : (
        <>
          <p className="text-sm text-gray-300 leading-relaxed mb-3">{data!.summary}</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            <IndexBadge
              label="KOSPI"
              close={data!.indices.kospi?.close ?? null}
              changePct={data!.indices.kospi?.change_pct ?? null}
            />
            <IndexBadge
              label="KOSDAQ"
              close={data!.indices.kosdaq?.close ?? null}
              changePct={data!.indices.kosdaq?.change_pct ?? null}
            />
            {data!.indices.usd_krw != null && (
              <div className="flex items-center gap-1.5 text-xs">
                <span className="text-gray-500">USD/KRW</span>
                <span className="text-gray-200 font-medium">{data!.indices.usd_krw.toLocaleString('ko-KR')}</span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
