/** 어드민 대시보드 — 통계 카드, 클라우드 상태, AI 요약, 최근 에러 */
import { useQuery } from '@tanstack/react-query'
import { adminApi } from '../../services/admin'

export default function AdminDashboard() {
  const { data: stats } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: () => adminApi.getStats().then((r) => r.data.data ?? r.data),
    refetchInterval: 10000,
    staleTime: 5_000,
  })

  const { data: collector } = useQuery({
    queryKey: ['admin', 'collector'],
    queryFn: () => adminApi.getCollectorStatus().then((r) => r.data.data ?? r.data).catch(() => null),
    refetchInterval: 10000,
    staleTime: 5_000,
  })

  const { data: aiStats } = useQuery({
    queryKey: ['admin', 'ai', 'stats-summary'],
    queryFn: () => adminApi.getAiStats().then((r) => r.data.data ?? r.data).catch(() => null),
    refetchInterval: 30000,
    staleTime: 15_000,
  })

  const { data: errors = [] } = useQuery({
    queryKey: ['admin', 'errors-recent'],
    queryFn: () => adminApi.getErrors({ limit: 5 }).then((r) => r.data.data ?? r.data ?? []).catch(() => []),
    refetchInterval: 10000,
    staleTime: 5_000,
  })

  const cards = [
    { label: '전체 유저', value: stats?.user_count ?? stats?.total_users ?? '-' },
    { label: '활성 유저', value: stats?.active_users ?? stats?.online_users ?? '-' },
    { label: '활성 규칙', value: stats?.rules_count ?? stats?.active_rules ?? '-' },
    { label: '활성 클라이언트', value: stats?.active_clients ?? '-' },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">어드민 대시보드</h1>

      {/* 통계 카드 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map((c) => (
          <div key={c.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-sm text-gray-500">{c.label}</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">{c.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* 클라우드 서버 상태 */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">클라우드 서버</h2>
          {collector ? (
            <div className="space-y-2 text-sm">
              <Row label="상태" value={collector.status ?? 'ok'} className={collector.status === 'error' ? 'text-red-600' : 'text-green-600'} />
              <Row label="마지막 시세" value={collector.last_quote_time ? new Date(collector.last_quote_time).toLocaleTimeString('ko-KR') : '-'} />
              <Row label="총 시세 수집" value={`${collector.total_quotes ?? 0}건`} />
              {(collector.error_count ?? 0) > 0 && <Row label="에러" value={`${collector.error_count}건`} className="text-red-600" />}
            </div>
          ) : (
            <div className="text-gray-400 text-sm">연결 대기 중...</div>
          )}
        </div>

        {/* AI 분석 요약 */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">AI 분석</h2>
          {aiStats ? (
            <div className="space-y-2 text-sm">
              <Row label="오늘 분석" value={`${aiStats.today_count ?? 0}건`} />
              <Row label="토큰" value={`${((aiStats.token_input ?? 0) / 1000).toFixed(0)}K in / ${((aiStats.token_output ?? 0) / 1000).toFixed(0)}K out`} />
              <Row label="추정 비용" value={`$${(aiStats.estimated_cost ?? 0).toFixed(2)}`} />
            </div>
          ) : (
            <div className="text-gray-400 text-sm">데이터 없음</div>
          )}
        </div>
      </div>

      {/* 최근 에러 */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b">
          <span className="text-sm font-semibold text-gray-700">최근 에러</span>
        </div>
        {Array.isArray(errors) && errors.length > 0 ? (
          <table className="w-full text-xs">
            <tbody>
              {errors.slice(0, 5).map((e: { id?: number; timestamp: string; level: string; message: string }, i: number) => (
                <tr key={e.id ?? i} className="border-b border-gray-50">
                  <td className="py-2 px-3 text-gray-400 font-mono w-36">
                    {new Date(e.timestamp).toLocaleTimeString('ko-KR')}
                  </td>
                  <td className="py-2 px-3 w-16">
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                      e.level === 'ERROR' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                    }`}>{e.level}</span>
                  </td>
                  <td className="py-2 px-3 truncate max-w-md">{e.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="px-4 py-6 text-center text-gray-400 text-sm">에러 없음</div>
        )}
      </div>
    </div>
  )
}

function Row({ label, value, className = '' }: { label: string; value: string; className?: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className={`font-medium ${className}`}>{value}</span>
    </div>
  )
}
