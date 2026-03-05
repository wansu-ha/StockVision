import axios from 'axios'

const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'
const local = axios.create({ baseURL: LOCAL_URL, timeout: 5000 })

export interface ExecutionLog {
  id: number
  rule_id: number
  rule_name: string
  symbol: string
  side: 'BUY' | 'SELL'
  quantity: number
  order_no: string | null
  filled_price: number | null
  filled_qty: number | null
  status: 'SENT' | 'FILLED' | 'FAILED' | 'SKIPPED'
  condition_snapshot: string | null
  message: string | null
  created_at: string
}

export interface LogSummary {
  total: number
  filled: number
  failed: number
}

export const logsApi = {
  getLogs: (params?: {
    rule_id?: number
    date_from?: string
    date_to?: string
    limit?: number
    offset?: number
  }) =>
    local.get<{ success: boolean; data: ExecutionLog[]; count: number }>('/api/logs', { params })
      .then(r => r.data),

  getSummary: () =>
    local.get<{ success: boolean; data: LogSummary }>('/api/logs/summary')
      .then(r => r.data),
}
