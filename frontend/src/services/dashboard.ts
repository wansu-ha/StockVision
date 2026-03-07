/**
 * 대시보드 서비스 — TODO stub
 * /api/dashboard 엔드포인트 제거됨. MarketContext는 cloudContext로 전환 완료.
 * 이 파일은 미사용 — 삭제 후보.
 */

export interface DashboardData {
  bridge_connected: boolean
  broker_mode: 'demo' | 'real' | 'none'
  broker_connected: boolean
  active_rules: number
  today: { total: number; filled: number; failed: number }
  market_context: { kospi_rsi_14: number | null; trend: string | null }
  recent_logs: unknown[]
}

export const dashboardApi = {
  get: async () => {
    console.warn('[stub] dashboardApi.get: /api/dashboard 제거됨')
    return { success: true, data: {} as DashboardData }
  },
}
