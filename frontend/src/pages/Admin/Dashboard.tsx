/** 어드민 대시보드 — 통계 카드, 클라우드 상태, 최근 에러 */
import { useQuery } from '@tanstack/react-query'
import { adminApi } from '../../services/admin'

interface StatsData {
  total_users: number
  online_users: number
  active_rules: number
  errors_1h: number
}

export default function AdminDashboard() {
  const { data: stats } = useQuery<StatsData>({
    queryKey: ['admin', 'stats'],
    queryFn: () => adminApi.getStats().then((r: { data: { data: StatsData } }) => r.data.data ?? r.data),
    refetchInterval: 10000,
  })

  const cards = [
    { label: '전체 유저', value: stats?.total_users ?? '-' },
    { label: '온라인 유저', value: stats?.online_users ?? '-' },
    { label: '활성 규칙', value: stats?.active_rules ?? '-' },
    { label: '1시간 내 에러', value: stats?.errors_1h ?? '-' },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">어드민 대시보드</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map((c) => (
          <div key={c.label} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-sm text-gray-500">{c.label}</div>
            <div className="text-2xl font-bold text-gray-900 mt-1">{c.value}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
