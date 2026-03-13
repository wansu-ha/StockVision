/** localhost HTTP 클라이언트 (로컬 서버 :4020).
 *
 * JWT 전달, 규칙 sync, 상태 조회, 로그 조회 등.
 */
import axios, { type AxiosInstance } from 'axios'
import type { LogFilter, ExecutionLog } from '../types/log'
import type { LastRuleResult } from '../types/rule-result'
import type { LocalConfig } from '../types/settings'

const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'

let localSecret: string | null = null

const client: AxiosInstance = axios.create({
  baseURL: `${LOCAL_URL}/api`,
  timeout: 5000,
})

// X-Local-Secret 자동 첨부
client.interceptors.request.use((config) => {
  if (localSecret) {
    config.headers['X-Local-Secret'] = localSecret
  }
  return config
})

/** 인증 — JWT를 로컬 서버에 전달 */
export const localAuth = {
  setAuthToken: async (accessToken: string, refreshToken: string) => {
    try {
      const res = await client.post('/auth/token', { access_token: accessToken, refresh_token: refreshToken })
      localSecret = res.data?.data?.local_secret ?? null
      return res.data
    } catch {
      return null
    }
  },
  logout: () => {
    const result = client.post('/auth/logout').then((r) => r.data).catch(() => null)
    localSecret = null
    return result
  },
  status: () => client.get('/auth/status').then((r) => r.data).catch(() => null),
  restore: async () => {
    try {
      const res = await client.post('/auth/restore')
      localSecret = res.data?.data?.local_secret ?? null
      return res.data
    } catch {
      return null
    }
  },
}

/** 상태 */
export const localStatus = {
  get: () =>
    client.get('/status').then((r) => r.data.data ?? r.data).catch(() => null),
}

/** 설정 */
export const localConfig = {
  get: () => client.get<{ data: LocalConfig }>('/config').then((r) => r.data.data ?? r.data).catch(() => null),
  update: (patch: Partial<LocalConfig>) =>
    client.patch('/config', { updates: patch }).then((r) => r.data).catch(() => null),
  setBrokerKeys: (brokerType: string, appKey: string, appSecret: string, accountNo?: string) =>
    client.post('/config/broker-keys', { broker_type: brokerType, app_key: appKey, app_secret: appSecret, account_no: accountNo }, { timeout: 30_000 }).then((r) => r.data),
}

/** 규칙 sync */
export const localRules = {
  sync: (rules: unknown[]) =>
    client.post('/rules/sync', { rules }).then((r) => r.data).catch(() => null),
  lastResults: () =>
    client.get<{ data: LastRuleResult[] }>('/rules/last-results')
      .then((r) => r.data.data ?? [])
      .catch(() => [] as LastRuleResult[]),
}

/** 로그 */
export interface LogSummary {
  date: string
  signals: number
  fills: number
  orders: number
  errors: number
}

export interface DailyPnL {
  date: string
  realized_pnl: number
  fill_count: number
  win_count: number
  loss_count: number
  win_rate: number
}

export const localLogs = {
  get: (filters?: LogFilter) =>
    client.get<{ data: ExecutionLog[] }>('/logs', { params: filters })
      .then((r) => r.data.data ?? r.data)
      .catch(() => []),
  summary: (date?: string) =>
    client.get<{ data: LogSummary }>('/logs/summary', { params: date ? { date } : undefined })
      .then((r) => r.data.data ?? null)
      .catch(() => null),
  dailyPnl: (date?: string) =>
    client.get<{ data: DailyPnL }>('/logs/daily-pnl', { params: date ? { date } : undefined })
      .then((r) => r.data.data ?? null)
      .catch(() => null),
}

/** 계좌 (잔고 + 미체결) */
export interface AccountBalance {
  cash: number
  total_eval: number
  positions: {
    symbol: string
    qty: number
    avg_price: number
    current_price: number
    eval_amount: number
    unrealized_pnl: number
    unrealized_pnl_rate: number
  }[]
}

export interface OpenOrder {
  order_id: string
  symbol: string
  side: string
  qty: number
  filled_qty: number
  status: string
  order_type: string | null
  limit_price: number | null
  created_at: string | null
}

export const localAccount = {
  balance: () =>
    client.get<{ data: AccountBalance }>('/account/balance')
      .then((r) => r.data.data ?? null)
      .catch(() => null),
  orders: () =>
    client.get<{ data: OpenOrder[] }>('/account/orders')
      .then((r) => r.data.data ?? [])
      .catch(() => []),
}

/** 전략 엔진 제어 (브로커 인증 포함하므로 타임아웃 여유) */
export const localEngine = {
  start: () => client.post('/strategy/start', null, { timeout: 30_000 }).then((r) => r.data),
  stop: () => client.post('/strategy/stop', null, { timeout: 15_000 }).then((r) => r.data),
}

/** 브로커 재연결 */
export const localBroker = {
  reconnect: () => client.post('/broker/reconnect', null, { timeout: 15_000 }).then((r) => r.data).catch(() => null),
}

/** 헬스 체크 (버전 포함) */
export const localHealth = {
  check: () =>
    axios.get<{ status: string; version: string }>(`${LOCAL_URL}/health`, { timeout: 3000 })
      .then((r) => r.data)
      .catch(() => null),
}

export default client
