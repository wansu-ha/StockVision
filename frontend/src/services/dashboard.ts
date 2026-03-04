import axios from 'axios'

const local = axios.create({ baseURL: 'http://127.0.0.1:8765', timeout: 3000 })

export interface DashboardData {
  bridge_connected: boolean
  kiwoom_mode: 'demo' | 'real' | 'none'
  kiwoom_connected: boolean
  active_rules: number
  today: { total: number; filled: number; failed: number }
  market_context: { kospi_rsi_14: number | null; trend: string | null }
  recent_logs: unknown[]
}

export const dashboardApi = {
  get: () =>
    local.get<{ success: boolean; data: DashboardData }>('/api/dashboard')
      .then(r => r.data),
}
