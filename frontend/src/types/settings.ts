/** 설정 관련 타입 */

export interface BrokerConfig {
  has_api_key: boolean
  mode: 'paper' | 'live'
  status: 'ok' | 'error' | 'not_configured'
}

export interface LocalConfig {
  mode: 'paper' | 'live'
  engine_running: boolean
  budget_ratio: number
  max_positions: number
  max_loss_pct: number
  max_orders_per_minute: number
}

export interface UserProfile {
  email: string
  nickname: string
  role: string
  created_at: string
}
