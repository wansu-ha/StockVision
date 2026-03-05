/** localhost HTTP 클라이언트 (로컬 서버 :8765).
 *
 * JWT 전달, 규칙 sync, 상태 조회, 로그 조회 등.
 */
import axios, { type AxiosInstance } from 'axios'
import type { LogFilter, ExecutionLog } from '../types/log'
import type { LocalConfig } from '../types/settings'

const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:8765'

const client: AxiosInstance = axios.create({
  baseURL: `${LOCAL_URL}/api`,
  timeout: 5000,
})

/** 인증 — JWT를 로컬 서버에 전달 */
export const localAuth = {
  setAuthToken: (accessToken: string, refreshToken: string) =>
    client.post('/auth/token', { access_token: accessToken, refresh_token: refreshToken })
      .then((r) => r.data)
      .catch(() => null),
  logout: () => client.post('/auth/logout').then((r) => r.data).catch(() => null),
  status: () => client.get('/auth/status').then((r) => r.data).catch(() => null),
}

/** 상태 */
export const localStatus = {
  get: () =>
    client.get('/status').then((r) => r.data).catch(() => null),
}

/** 설정 */
export const localConfig = {
  get: () => client.get<{ data: LocalConfig }>('/config').then((r) => r.data.data ?? r.data).catch(() => null),
  update: (patch: Partial<LocalConfig>) =>
    client.patch('/config', patch).then((r) => r.data).catch(() => null),
  setKiwoomKeys: (appKey: string, appSecret: string) =>
    client.post('/config/kiwoom', { app_key: appKey, app_secret: appSecret }).then((r) => r.data),
}

/** 규칙 sync */
export const localRules = {
  sync: (rules: unknown[]) =>
    client.post('/rules/sync', { rules }).then((r) => r.data).catch(() => null),
}

/** 로그 */
export const localLogs = {
  get: (filters?: LogFilter) =>
    client.get<{ data: ExecutionLog[] }>('/logs', { params: filters })
      .then((r) => r.data.data ?? r.data)
      .catch(() => []),
}

/** 전략 엔진 제어 */
export const localEngine = {
  start: () => client.post('/strategy/start').then((r) => r.data).catch(() => null),
  stop: () => client.post('/strategy/stop').then((r) => r.data).catch(() => null),
}

export default client
