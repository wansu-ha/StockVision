/** 백테스트 결과 표시 컴포넌트. */
import type { BacktestSummary, BacktestTrade } from '../services/backtest'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'

interface Props {
  summary: BacktestSummary
  equityCurve: number[]
  trades: BacktestTrade[]
}

export default function BacktestResult({ summary, equityCurve, trades }: Props) {
  const chartData = equityCurve.map((v, i) => ({ idx: i, equity: Math.round(v) }))

  return (
    <div className="space-y-6">
      {/* 요약 카드 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <MetricCard label="총 수익률" value={`${summary.total_return_pct}%`}
          color={summary.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'} />
        <MetricCard label="MDD" value={`-${summary.max_drawdown_pct}%`} color="text-red-400" />
        <MetricCard label="승률" value={`${summary.win_rate}%`} color="text-gray-200" />
        <MetricCard label="손익비" value={`${summary.profit_factor}`} color="text-gray-200" />
        <MetricCard label="CAGR" value={`${summary.cagr}%`}
          color={summary.cagr >= 0 ? 'text-green-400' : 'text-red-400'} />
        <MetricCard label="거래 횟수" value={`${summary.trade_count}`} color="text-gray-200" />
        <MetricCard label="샤프 비율" value={`${summary.sharpe_ratio}`} color="text-gray-200" />
        <MetricCard label="평균 보유" value={`${summary.avg_hold_bars}봉`} color="text-gray-200" />
        <MetricCard label="총 수수료" value={`₩${summary.total_commission.toLocaleString()}`} color="text-gray-400" />
        <MetricCard label="총 세금" value={`₩${summary.total_tax.toLocaleString()}`} color="text-gray-400" />
      </div>

      {/* 수익 곡선 */}
      {chartData.length > 0 && (
        <div className="bg-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-3">수익 곡선</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="idx" hide />
              <YAxis
                tickFormatter={(v: number) => `${(v / 10000).toFixed(0)}만`}
                stroke="#6B7280"
                fontSize={12}
              />
              <Tooltip
                formatter={(v: number) => [`₩${v.toLocaleString()}`, '자산']}
                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }}
                labelStyle={{ color: '#9CA3AF' }}
              />
              <Line
                type="monotone"
                dataKey="equity"
                stroke="#6366F1"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* 거래 목록 */}
      {trades.length > 0 && (
        <div className="bg-gray-800 rounded-xl p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-3">
            거래 내역 ({trades.length}건)
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-gray-300">
              <thead>
                <tr className="text-gray-500 border-b border-gray-700">
                  <th className="text-left py-2 px-2">진입</th>
                  <th className="text-right py-2 px-2">매수가</th>
                  <th className="text-left py-2 px-2">청산</th>
                  <th className="text-right py-2 px-2">매도가</th>
                  <th className="text-right py-2 px-2">수량</th>
                  <th className="text-right py-2 px-2">손익</th>
                  <th className="text-right py-2 px-2">수익률</th>
                  <th className="text-right py-2 px-2">보유</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t, i) => (
                  <tr key={i} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                    <td className="py-2 px-2">{formatDate(t.entry_date)}</td>
                    <td className="text-right py-2 px-2">₩{t.entry_price.toLocaleString()}</td>
                    <td className="py-2 px-2">{formatDate(t.exit_date)}</td>
                    <td className="text-right py-2 px-2">₩{t.exit_price.toLocaleString()}</td>
                    <td className="text-right py-2 px-2">{t.qty}</td>
                    <td className={`text-right py-2 px-2 ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      ₩{t.pnl.toLocaleString()}
                    </td>
                    <td className={`text-right py-2 px-2 ${t.pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {t.pnl_pct}%
                    </td>
                    <td className="text-right py-2 px-2 text-gray-500">{t.hold_bars}봉</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-gray-800 rounded-lg p-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-lg font-semibold ${color}`}>{value}</div>
    </div>
  )
}

function formatDate(d: string): string {
  if (!d) return '-'
  // "2025-06-15" or "2025-06-15T09:30:00"
  return d.length > 10 ? d.slice(0, 16).replace('T', ' ') : d
}
