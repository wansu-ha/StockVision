import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import { portfolioApi } from '../services/portfolio'

const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#6b7280']
const ACCOUNT_ID = 1  // TODO: 계좌 선택 UI

const PERIODS = ['7d', '30d', '90d', '180d']

export default function Portfolio() {
  const [period, setPeriod] = useState('30d')

  const { data: portfolioData, isLoading } = useQuery({
    queryKey: ['portfolio', ACCOUNT_ID],
    queryFn:  () => portfolioApi.get(ACCOUNT_ID),
  })
  const { data: curveData } = useQuery({
    queryKey: ['equity-curve', ACCOUNT_ID, period],
    queryFn:  () => portfolioApi.equityCurve(ACCOUNT_ID, period),
  })
  const { data: sectorData } = useQuery({
    queryKey: ['sector', ACCOUNT_ID],
    queryFn:  () => portfolioApi.sectorAllocation(ACCOUNT_ID),
  })

  const p   = portfolioData?.data
  const curve = curveData?.data ?? []
  const sectors = sectorData?.data ?? []

  if (isLoading) return <div className="p-8 text-center text-gray-400">로딩 중...</div>
  if (!p) return <div className="p-8 text-center text-red-500">데이터 없음</div>

  const pnlColor = p.total_pnl >= 0 ? 'text-blue-600' : 'text-red-600'

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">포트폴리오 — {p.account_name}</h1>

      {/* 요약 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: '총 자산', value: `₩${p.total_value.toLocaleString()}` },
          { label: '예수금', value: `₩${p.cash_balance.toLocaleString()}` },
          { label: '평가금액', value: `₩${p.positions_value.toLocaleString()}` },
          { label: '총 손익', value: `${p.total_pnl >= 0 ? '+' : ''}₩${p.total_pnl.toLocaleString()} (${p.total_pnl_pct.toFixed(1)}%)`, color: pnlColor },
        ].map(c => (
          <div key={c.label} className="bg-white rounded-xl shadow p-4">
            <div className="text-xs text-gray-500 mb-1">{c.label}</div>
            <div className={`text-lg font-bold ${c.color ?? ''}`}>{c.value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* 수익률 차트 */}
        <div className="md:col-span-2 bg-white rounded-xl shadow p-4">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-sm font-semibold text-gray-600">수익률 추이</h2>
            <div className="flex gap-1">
              {PERIODS.map(p => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-2 py-0.5 text-xs rounded ${period === p ? 'bg-blue-600 text-white' : 'text-gray-500 hover:bg-gray-100'}`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          {curve.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={curve}>
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `${(v / 10000).toFixed(0)}만`} />
                <Tooltip formatter={(v: number) => `₩${v.toLocaleString()}`} />
                <Line type="monotone" dataKey="equity" dot={false} stroke="#3b82f6" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-44 flex items-center justify-center text-gray-300 text-sm">데이터 없음</div>
          )}
        </div>

        {/* 자산 배분 파이 */}
        <div className="bg-white rounded-xl shadow p-4">
          <h2 className="text-sm font-semibold text-gray-600 mb-3">자산 배분</h2>
          {sectors.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={sectors} dataKey="weight_pct" nameKey="sector" outerRadius={60} label={({ sector, weight_pct }) => `${sector} ${weight_pct.toFixed(0)}%`} labelLine={false} fontSize={10}>
                  {sectors.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Legend iconSize={8} wrapperStyle={{ fontSize: 10 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-44 flex items-center justify-center text-gray-300 text-sm">데이터 없음</div>
          )}
        </div>
      </div>

      {/* 보유 종목 */}
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              {['종목', '수량', '평균가', '현재가', '손익', '비중'].map(h => (
                <th key={h} className="px-4 py-3 text-left font-medium text-gray-600">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {p.positions.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-400">보유 종목 없음</td>
              </tr>
            ) : p.positions.map(pos => (
              <tr key={pos.symbol} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono">{pos.symbol}</td>
                <td className="px-4 py-3">{pos.quantity}주</td>
                <td className="px-4 py-3">₩{pos.avg_price.toLocaleString()}</td>
                <td className="px-4 py-3">₩{pos.current_price.toLocaleString()}</td>
                <td className={`px-4 py-3 ${pos.unrealized_pnl >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                  {pos.unrealized_pnl >= 0 ? '+' : ''}₩{pos.unrealized_pnl.toLocaleString()}
                  {' '}({pos.pnl_pct.toFixed(1)}%)
                </td>
                <td className="px-4 py-3">{pos.weight_pct.toFixed(1)}%</td>
              </tr>
            ))}
            {/* 현금 행 */}
            <tr className="bg-gray-50">
              <td className="px-4 py-3 text-gray-500">현금</td>
              <td colSpan={3} />
              <td />
              <td className="px-4 py-3 text-gray-500">
                {(p.cash_balance / p.total_value * 100).toFixed(1)}%
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
