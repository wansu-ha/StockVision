/** 대시보드 관련 타입 */

export interface PriceQuote {
  symbol: string
  name: string
  price: number
  changePercent: number
  volume: number
}

export interface ExecutionEvent {
  timestamp: string
  symbol: string
  side: 'buy' | 'sell'
  qty: number
  price: number
  status: 'pending' | 'filled' | 'cancelled' | 'failed'
  rule_id?: number
}

export interface MarketContextData {
  kospi_rsi?: number
  kosdaq_rsi?: number
  volatility?: number
  trend?: string
  updated_at?: string
  is_holiday?: boolean
}
