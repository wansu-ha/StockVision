/** AI 분석 모니터링 — 토큰/비용 추적, 최근 분석 결과 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { adminApi } from '../../services/admin'

interface AiStatsData {
  today_count: number
  month_count: number
  token_input: number
  token_output: number
  estimated_cost: number
  error_rate: number
  daily_trend: { date: string; count: number; cost: number }[]
}

interface AiAnalysis {
  id: number
  symbol: string
  type: string
  score: number | null
  text: string
  model: string
  token_input: number
  token_output: number
  created_at: string
}

export default function AdminAiMonitor() {
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const { data: stats } = useQuery<AiStatsData>({
    queryKey: ['admin', 'ai', 'stats'],
    queryFn: () => adminApi.getAiStats().then((r: { data: { data: AiStatsData } }) => r.data.data ?? r.data),
    refetchInterval: 30000,
    staleTime: 15_000,
  })

  const { data: recent = [] } = useQuery<AiAnalysis[]>({
    queryKey: ['admin', 'ai', 'recent'],
    queryFn: () => adminApi.getAiRecent(20).then((r: { data: { data: AiAnalysis[] } }) => r.data.data ?? r.data ?? []),
    refetchInterval: 30000,
    staleTime: 15_000,
  })

  const cards = [
    { label: '오늘 분석', value: stats?.today_count ?? '-' },
    { label: '이번 달', value: stats?.month_count ?? '-' },
    { label: '토큰 (in/out)', value: stats ? `${(stats.token_input / 1000).toFixed(0)}K / ${(stats.token_output / 1000).toFixed(0)}K` : '-' },
    { label: '추정 비용', value: stats ? `$${stats.estimated_cost.toFixed(2)}` : '-' },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">AI 분석 모니터링</h1>

      {/* 통계 카드 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map((c) => (
          <div key={c.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-sm text-gray-500">{c.label}</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">{c.value}</div>
          </div>
        ))}
      </div>

      {/* 최근 분석 결과 */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b">
          <span className="text-sm font-semibold text-gray-700">최근 분석 결과</span>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-gray-500 bg-gray-50">
              <th className="text-left py-2 px-3">시간</th>
              <th className="text-left py-2 px-3">종목</th>
              <th className="text-left py-2 px-3">타입</th>
              <th className="text-right py-2 px-3">점수</th>
              <th className="text-right py-2 px-3">토큰</th>
            </tr>
          </thead>
          <tbody>
            {(Array.isArray(recent) ? recent : []).map((a) => (
              <tr
                key={a.id}
                className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
                onClick={() => setExpandedId(expandedId === a.id ? null : a.id)}
              >
                <td className="py-2 px-3 text-gray-500 font-mono text-xs">
                  {new Date(a.created_at).toLocaleString('ko-KR')}
                </td>
                <td className="py-2 px-3 font-medium">{a.symbol}</td>
                <td className="py-2 px-3">{a.type}</td>
                <td className="py-2 px-3 text-right">{a.score?.toFixed(1) ?? '-'}</td>
                <td className="py-2 px-3 text-right text-gray-400 text-xs">{a.token_input + a.token_output}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 펼치기 모달 */}
      {expandedId && (() => {
        const item = (Array.isArray(recent) ? recent : []).find((a) => a.id === expandedId)
        if (!item) return null
        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/30" onClick={() => setExpandedId(null)} />
            <div className="relative bg-white rounded-2xl shadow-2xl p-6 max-w-lg w-full max-h-[80vh] overflow-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold">{item.symbol} — {item.type}</h3>
                <button onClick={() => setExpandedId(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
              </div>
              <div className="space-y-3 text-sm">
                <div><span className="text-gray-500">모델:</span> {item.model}</div>
                <div><span className="text-gray-500">점수:</span> {item.score?.toFixed(2) ?? 'N/A'}</div>
                <div><span className="text-gray-500">토큰:</span> {item.token_input} in / {item.token_output} out</div>
                <div>
                  <span className="text-gray-500">결과:</span>
                  <p className="mt-1 bg-gray-50 p-3 rounded-lg text-xs whitespace-pre-wrap">{item.text}</p>
                </div>
              </div>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
