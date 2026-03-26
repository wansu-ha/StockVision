/** 백테스트 페이지. */
import { useState } from 'react'
import type { FormEvent } from 'react'
import { runBacktest, type BacktestResponse } from '../services/backtest'
import BacktestResultView from '../components/BacktestResult'

const TIMEFRAMES = [
  { value: '1m', label: '1분' },
  { value: '5m', label: '5분' },
  { value: '15m', label: '15분' },
  { value: '1h', label: '1시간' },
  { value: '1d', label: '일봉' },
]

const PERIODS = [
  { label: '3개월', days: 90 },
  { label: '6개월', days: 180 },
  { label: '1년', days: 365 },
  { label: '2년', days: 730 },
  { label: '5년', days: 1825 },
]

export default function Backtest() {
  const [symbol, setSymbol] = useState('')
  const [script, setScript] = useState('매수: RSI(14) <= 30\n매도: RSI(14) >= 70')
  const [timeframe, setTimeframe] = useState('1d')
  const [periodDays, setPeriodDays] = useState(365)
  const [initialCash, setInitialCash] = useState(10_000_000)

  // 고급 옵션
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [commissionRate, setCommissionRate] = useState(0.00015)
  const [taxRate, setTaxRate] = useState(0.0018)
  const [slippageRate, setSlippageRate] = useState(0.001)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<BacktestResponse['data'] | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!symbol || !script.trim()) {
      setError('종목과 규칙을 입력해주세요.')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)

    const end = new Date()
    const start = new Date(end.getTime() - periodDays * 86_400_000)

    try {
      const resp = await runBacktest({
        script,
        symbol,
        start_date: start.toISOString().slice(0, 10),
        end_date: end.toISOString().slice(0, 10),
        timeframe,
        initial_cash: initialCash,
        commission_rate: commissionRate,
        tax_rate: taxRate,
        slippage_rate: slippageRate,
      })
      if (resp.success) {
        setResult(resp.data)
      } else {
        setError('백테스트 실행에 실패했습니다.')
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '알 수 없는 오류'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-4 sm:p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">백테스트</h1>

      <form onSubmit={handleSubmit} className="space-y-4 mb-8">
        {/* 종목 */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">종목</label>
          <input
            data-testid="backtest-symbol"
            type="text"
            value={symbol}
            onChange={e => setSymbol(e.target.value)}
            placeholder="종목코드 (예: 005930)"
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm focus:border-indigo-500 focus:outline-none"
          />
        </div>

        {/* DSL 스크립트 */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">전략 규칙 (DSL)</label>
          <textarea
            data-testid="backtest-script"
            value={script}
            onChange={e => setScript(e.target.value)}
            rows={4}
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm font-mono focus:border-indigo-500 focus:outline-none resize-none"
            placeholder="매수: RSI(14) <= 30&#10;매도: RSI(14) >= 70"
          />
        </div>

        {/* 기간 + 타임프레임 */}
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="block text-sm text-gray-400 mb-1">기간</label>
            <select
              value={periodDays}
              onChange={e => setPeriodDays(Number(e.target.value))}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm focus:border-indigo-500 focus:outline-none"
            >
              {PERIODS.map(p => (
                <option key={p.days} value={p.days}>{p.label}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm text-gray-400 mb-1">타임프레임</label>
            <select
              value={timeframe}
              onChange={e => setTimeframe(e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm focus:border-indigo-500 focus:outline-none"
            >
              {TIMEFRAMES.map(tf => (
                <option key={tf.value} value={tf.value}>{tf.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 초기 자금 */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">초기 자금</label>
          <input
            type="number"
            value={initialCash}
            onChange={e => setInitialCash(Number(e.target.value))}
            className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm focus:border-indigo-500 focus:outline-none"
          />
        </div>

        {/* 고급 옵션 */}
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-xs text-gray-500 hover:text-gray-300 transition"
        >
          {showAdvanced ? '▾ 고급 옵션 접기' : '▸ 고급 옵션 (수수료, 세금, 슬리피지)'}
        </button>

        {showAdvanced && (
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">수수료 (%)</label>
              <input
                type="number"
                step="0.001"
                value={(commissionRate * 100).toFixed(3)}
                onChange={e => setCommissionRate(Number(e.target.value) / 100)}
                className="w-full px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-xs focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">매도 세금 (%)</label>
              <input
                type="number"
                step="0.01"
                value={(taxRate * 100).toFixed(2)}
                onChange={e => setTaxRate(Number(e.target.value) / 100)}
                className="w-full px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-xs focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">슬리피지 (%)</label>
              <input
                type="number"
                step="0.01"
                value={(slippageRate * 100).toFixed(2)}
                onChange={e => setSlippageRate(Number(e.target.value) / 100)}
                className="w-full px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-xs focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>
        )}

        {error && (
          <div className="p-3 rounded-lg bg-red-900/30 border border-red-800 text-red-400 text-sm">
            {error}
          </div>
        )}

        <button
          data-testid="backtest-submit"
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {loading ? '실행 중...' : '백테스트 실행'}
        </button>
      </form>

      {/* 결과 */}
      {result && (
        <BacktestResultView
          summary={result.summary}
          equityCurve={result.equity_curve}
          trades={result.trades}
        />
      )}
    </div>
  )
}
