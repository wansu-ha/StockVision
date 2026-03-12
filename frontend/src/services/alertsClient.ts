/** 경고 설정 API 클라이언트 */
import axios from 'axios'

const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'

export interface AlertRuleConfig {
  enabled: boolean
  threshold_pct?: number
  threshold_min?: number
}

export interface AlertSettings {
  master_enabled: boolean
  rules: {
    position_loss:        AlertRuleConfig
    volatility:           AlertRuleConfig
    stale_order:          AlertRuleConfig
    daily_loss_proximity: AlertRuleConfig
    market_close_orders:  AlertRuleConfig
    engine_health:        AlertRuleConfig
    broker_health:        AlertRuleConfig
    kill_switch:          AlertRuleConfig
    loss_lock:            AlertRuleConfig
  }
}

export const alertsClient = {
  async getSettings(): Promise<AlertSettings> {
    const res = await axios.get(`${LOCAL_URL}/api/settings/alerts`)
    return res.data.data as AlertSettings
  },

  async updateSettings(settings: Partial<AlertSettings>): Promise<AlertSettings> {
    const res = await axios.put(`${LOCAL_URL}/api/settings/alerts`, settings)
    return res.data.data as AlertSettings
  },
}
