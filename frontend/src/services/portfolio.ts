/**
 * 포트폴리오 서비스 — TODO stub
 * 레거시 백엔드(:8000) 제거. 클라우드 서버 마이그레이션 후 재구현 예정.
 */

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

const STUB_WARN = (name: string) => console.warn(`[stub] ${name}: 레거시 백엔드 제거됨`)

export const portfolioApi = {
  get: async (_accountId: number) => { STUB_WARN('portfolioApi.get'); return { success: true, data: {} as PortfolioData } },
  equityCurve: async (_accountId: number, _period = '30d') => { STUB_WARN('portfolioApi.equityCurve'); return { success: true, data: [] as EquityPoint[] } },
  sectorAllocation: async (_accountId: number) => { STUB_WARN('portfolioApi.sectorAllocation'); return { success: true, data: [] as SectorSlice[] } },
}
