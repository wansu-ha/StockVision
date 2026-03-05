/** 시세 데이터 모니터링 */
import { useQuery } from '@tanstack/react-query'
import { adminApi } from '../../services/admin'

interface DataStatusInfo {
  status: 'ok' | 'warning' | 'error'
  last_quote_at: string
  subscribed_symbols: number
  daily_bars_collected: number
  sources: Record<string, string>
}

export default function AdminDataStatus() {
  const { data } = useQuery<DataStatusInfo>({
    queryKey: ['admin', 'data', 'status'],
    queryFn: () => adminApi.getDataStatus().then((r: { data: { data: DataStatusInfo } }) => r.data.data ?? r.data),
    refetchInterval: 10000,
  })

  const statusColors: Record<string, string> = {
    ok: 'text-green-600',
    warning: 'text-yellow-600',
    error: 'text-red-600',
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">시세 데이터 모니터링</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="클라우드 상태" value={data?.status ?? '-'} className={statusColors[data?.status ?? ''] ?? ''} />
        <StatCard label="마지막 시세" value={data?.last_quote_at ? new Date(data.last_quote_at).toLocaleTimeString('ko-KR') : '-'} />
        <StatCard label="구독 종목" value={String(data?.subscribed_symbols ?? '-')} />
        <StatCard label="일봉 수집 (건/일)" value={String(data?.daily_bars_collected ?? '-')} />
      </div>

      {data?.sources && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-sm font-medium text-gray-500 mb-4">데이터 소스별 상태</h2>
          <div className="space-y-2">
            {Object.entries(data.sources).map(([name, status]) => (
              <div key={name} className="flex items-center justify-between py-2 border-b border-gray-50">
                <span className="font-medium text-gray-900">{name}</span>
                <span className={`text-sm ${status === 'ok' ? 'text-green-600' : status === 'error' ? 'text-red-600' : 'text-yellow-600'}`}>
                  {status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, className = '' }: { label: string; value: string; className?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="text-sm text-gray-500">{label}</div>
      <div className={`text-xl font-bold mt-1 ${className || 'text-gray-900'}`}>{value}</div>
    </div>
  )
}
