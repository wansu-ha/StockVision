import axios from 'axios'

const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'
const local = axios.create({ baseURL: LOCAL_URL, timeout: 3000 })

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
