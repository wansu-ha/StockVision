/** 접속 통계 차트 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { adminApi } from '../../services/admin'

type Period = '24h' | '7d' | '30d' | '90d'

interface DataPoint {
  timestamp: string
  online: number
  dau: number
}

export default function AdminStats() {
  const [period, setPeriod] = useState<Period>('7d')

  const { data = [] } = useQuery<DataPoint[]>({
    queryKey: ['admin', 'stats', 'connections', period],
    queryFn: () =>
      adminApi.getConnectionStats(period).then((r: { data: { data: DataPoint[] } }) => r.data.data ?? r.data ?? []),
    refetchInterval: 30000,
  })

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">접속 통계</h1>

      {/* 기간 선택 */}
      <div className="flex gap-2 mb-6">
        {(['24h', '7d', '30d', '90d'] as Period[]).map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              period === p ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {/* 차트 */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-sm font-medium text-gray-500 mb-4">온라인 유저 추이</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="timestamp" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="online" stroke="#6366f1" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="dau" stroke="#22c55e" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
