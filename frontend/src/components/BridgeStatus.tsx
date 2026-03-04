import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { dashboardApi } from '../services/dashboard'
import type { DashboardData } from '../services/dashboard'

export default function BridgeStatus() {
  const { data, isError } = useQuery({
    queryKey: ['dashboard'],
    queryFn:  dashboardApi.get,
    refetchInterval: 10_000,
    retry: false,
  })

  const d: DashboardData | undefined = data?.data

  if (isError || !d) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-50 text-red-600 text-xs">
        <span className="w-2 h-2 rounded-full bg-red-500" />
        브릿지 미연결
      </div>
    )
  }

  const modeLabel = d.kiwoom_mode === 'demo' ? '모의투자' : d.kiwoom_mode === 'real' ? '실계좌' : '미연결'

  return (
    <div className="flex items-center gap-3 text-xs">
      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-50 text-green-700">
        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
        브릿지 연결 · {modeLabel}
      </div>
      <span className="text-gray-500">전략 {d.active_rules}개</span>
      <span className="text-gray-500">오늘 체결 {d.today.filled}건</span>
      <Link to="/logs" className="text-blue-600 hover:underline">로그</Link>
      <Link to="/strategy" className="text-blue-600 hover:underline">전략</Link>
    </div>
  )
}
