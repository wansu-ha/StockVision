/** 클라우드 서버 HTTP 클라이언트.
 *
 * JWT 인터셉터 자동 첨부, 401 시 refresh token 자동 갱신.
 */
import axios from 'axios'
import type { Rule, CreateRulePayload, UpdateRulePayload } from '../types/strategy'
import type { MarketContextData } from '../types/dashboard'

const CLOUD_URL = import.meta.env.VITE_CLOUD_API_URL || 'http://localhost:4010'
const JWT_KEY = 'sv_jwt'
const RT_KEY = 'sv_rt'

const client = axios.create({
  baseURL: CLOUD_URL,
  timeout: 15000,
})

// JWT 자동 첨부
client.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(JWT_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 401 시 refresh 자동 갱신
client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const rt = localStorage.getItem(RT_KEY)
      if (rt) {
        try {
          const { data } = await axios.post(`${CLOUD_URL}/api/v1/auth/refresh`, { refresh_token: rt })
          const newJwt = data.data?.access_token ?? data.access_token
          const newRt = data.data?.refresh_token ?? data.refresh_token
          if (!newJwt || !newRt) throw new Error('Invalid refresh response')
          sessionStorage.setItem(JWT_KEY, newJwt)
          localStorage.setItem(RT_KEY, newRt)
          original.headers.Authorization = `Bearer ${newJwt}`
          return client(original)
        } catch {
          sessionStorage.removeItem(JWT_KEY)
          localStorage.removeItem(RT_KEY)
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  },
)

/** 인증 — /api/v1/auth/ */
export const cloudAuth = {
  register: (email: string, password: string, nickname?: string) =>
    client.post('/api/v1/auth/register', { email, password, nickname }).then((r) => r.data),
  login: (email: string, password: string) =>
    client.post('/api/v1/auth/login', { email, password }).then((r) => r.data),
  refresh: (refreshToken: string) =>
    client.post('/api/v1/auth/refresh', { refresh_token: refreshToken }).then((r) => r.data),
  logout: (refreshToken: string) =>
    client.post('/api/v1/auth/logout', { refresh_token: refreshToken }).then((r) => r.data),
  verifyEmail: (token: string) =>
    client.get('/api/v1/auth/verify-email', { params: { token } }).then((r) => r.data),
  updateProfile: (_nickname: string) => {
    // TODO: 서버에 /api/v1/auth/profile 엔드포인트 없음 — 클라우드 서버 구현 후 연결
    console.warn('cloudAuth.updateProfile: 서버 엔드포인트 미구현')
    return Promise.resolve({ success: false, message: 'not implemented' })
  },
}

/** 규칙 CRUD — /api/v1/rules */
export const cloudRules = {
  list: () =>
    client.get<{ data: Rule[] }>('/api/v1/rules').then((r) => r.data.data ?? r.data),
  create: (payload: CreateRulePayload) =>
    client.post<{ data: Rule }>('/api/v1/rules', payload).then((r) => r.data.data ?? r.data),
  update: (id: number, payload: UpdateRulePayload) =>
    client.put<{ data: Rule }>(`/api/v1/rules/${id}`, payload).then((r) => r.data.data ?? r.data),
  remove: (id: number) =>
    client.delete(`/api/v1/rules/${id}`).then((r) => r.data),
}

/** 시장 컨텍스트 — /api/v1/context */
export const cloudContext = {
  get: () =>
    client.get<{ data: MarketContextData }>('/api/v1/context').then((r) => r.data.data ?? r.data),
}

/** 종목 검색/조회 — /api/v1/stocks */
export interface StockMasterItem {
  symbol: string
  name: string
  market: string
  sector: string | null
  is_active: boolean
  updated_at: string | null
}

export const cloudStocks = {
  search: (q: string, limit = 20) =>
    client.get<{ data: StockMasterItem[] }>('/api/v1/stocks/search', { params: { q, limit } })
      .then((r) => r.data.data ?? []),
  get: (symbol: string) =>
    client.get<{ data: StockMasterItem }>(`/api/v1/stocks/${symbol}`)
      .then((r) => r.data.data ?? null),
}

/** 관심종목 — /api/v1/watchlist */
export interface WatchlistItem {
  id: number
  symbol: string
  added_at: string
}

export const cloudWatchlist = {
  list: () =>
    client.get<{ data: WatchlistItem[] }>('/api/v1/watchlist').then((r) => r.data.data ?? []),
  add: (symbol: string) =>
    client.post<{ data: WatchlistItem }>('/api/v1/watchlist', { symbol }).then((r) => r.data.data),
  remove: (symbol: string) =>
    client.delete(`/api/v1/watchlist/${symbol}`).then((r) => r.data),
}

/** 헬스 체크 — /health */
export const cloudHealth = {
  check: () =>
    axios.get(`${CLOUD_URL}/health`, { timeout: 5000 }).then((r) => r.data).catch(() => null),
}

export default client
