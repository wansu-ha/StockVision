/** 로그 관련 타입 */

export interface ExecutionLog {
  id: number
  timestamp: string
  symbol: string
  side: 'BUY' | 'SELL'
  qty: number
  price: number
  status: string
  rule_id: number
  reason?: string
  order_id?: string
}

export interface LogFilter {
  date_from?: string
  date_to?: string
  symbol?: string
  status?: string
  offset?: number
  limit?: number
}
