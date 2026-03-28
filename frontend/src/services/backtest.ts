/** 백테스트 API 클라이언트. */
import axios from 'axios'

const CLOUD_URL = import.meta.env.VITE_CLOUD_API_URL || 'http://localhost:4010'
const JWT_KEY = 'sv_jwt'

export interface BacktestRequest {
  rule_id?: number
  script?: string
  symbol: string
  start_date?: string
  end_date?: string
  timeframe: string
  initial_cash?: number
  commission_rate?: number
  tax_rate?: number
  slippage_rate?: number
}

export interface BacktestTrade {
  entry_date: string
  entry_price: number
  exit_date: string
  exit_price: number
  qty: number
  pnl: number
  pnl_pct: number
  commission: number
  tax: number
  hold_bars: number
}

export interface BacktestSummary {
  total_return_pct: number
  cagr: number
  max_drawdown_pct: number
  win_rate: number
  profit_factor: number
  sharpe_ratio: number
  avg_hold_bars: number
  trade_count: number
  total_commission: number
  total_tax: number
  total_slippage: number
}

export interface BacktestResponse {
  success: boolean
  data: {
    id: number
    summary: BacktestSummary
    equity_curve: number[]
    trades: BacktestTrade[]
  }
}

export interface BacktestHistoryItem {
  id: number
  rule_id: number | null
  symbol: string
  start_date: string
  end_date: string
  timeframe: string
  summary: BacktestSummary
  trade_count: number
  executed_at: string
}

function authHeaders() {
  const jwt = sessionStorage.getItem(JWT_KEY)
  return { Authorization: `Bearer ${jwt}` }
}

export async function runBacktest(req: BacktestRequest): Promise<BacktestResponse> {
  const resp = await axios.post<BacktestResponse>(
    `${CLOUD_URL}/api/v1/backtest/run`,
    req,
    { headers: authHeaders(), timeout: 60_000 },
  )
  return resp.data
}

export async function getBacktestHistory(ruleId?: number): Promise<BacktestHistoryItem[]> {
  const params: Record<string, string> = {}
  if (ruleId !== undefined) params.rule_id = String(ruleId)
  const resp = await axios.get<{ success: boolean; data: BacktestHistoryItem[] }>(
    `${CLOUD_URL}/api/v1/backtest/history`,
    { headers: authHeaders(), params },
  )
  return resp.data.data
}

export async function getLatestBacktest(ruleId: number): Promise<BacktestHistoryItem | null> {
  const items = await getBacktestHistory(ruleId)
  return items.length > 0 ? items[0] : null
}
