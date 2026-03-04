import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000', timeout: 10000 })

export interface Position {
  symbol: string
  quantity: number
  avg_price: number
  current_price: number
  unrealized_pnl: number
  pnl_pct: number
  weight_pct: number
}

export interface PortfolioData {
  account_id: number
  account_name: string
  total_value: number
  cash_balance: number
  positions_value: number
  total_pnl: number
  total_pnl_pct: number
  positions: Position[]
}

export interface EquityPoint { date: string; equity: number }
export interface SectorSlice { sector: string; value: number; weight_pct: number }

export const portfolioApi = {
  get: (accountId: number) =>
    api.get<{ success: boolean; data: PortfolioData }>(`/api/v1/portfolio/${accountId}`)
      .then(r => r.data),

  equityCurve: (accountId: number, period = '30d') =>
    api.get<{ success: boolean; data: EquityPoint[] }>(
      `/api/v1/portfolio/${accountId}/equity-curve`,
      { params: { period } }
    ).then(r => r.data),

  sectorAllocation: (accountId: number) =>
    api.get<{ success: boolean; data: SectorSlice[] }>(
      `/api/v1/portfolio/${accountId}/sector-allocation`
    ).then(r => r.data),
}
