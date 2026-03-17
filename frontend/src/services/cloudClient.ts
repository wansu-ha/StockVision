/** 클라우드 서버 HTTP 클라이언트.
 *
 * JWT 인터셉터 자동 첨부, 401 시 refresh token 자동 갱신.
 */
import axios from 'axios'
import { localAuth } from './localClient'
import { AUTH_EVENTS } from '../context/authEvents'
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

// 401 시 로컬 서버 우선 refresh → 클라우드 폴백
client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true

      // 1단계: 로컬 서버에서 최신 토큰 요청
      try {
        const restored = await localAuth.restore()
        if (restored?.data?.access_token) {
          sessionStorage.setItem(JWT_KEY, restored.data.access_token)
          localStorage.setItem(RT_KEY, restored.data.refresh_token)
          window.dispatchEvent(new CustomEvent(AUTH_EVENTS.TOKEN_REFRESHED, { detail: { jwt: restored.data.access_token, rt: restored.data.refresh_token } }))
          original.headers.Authorization = `Bearer ${restored.data.access_token}`
          return client(original)
        }
      } catch { /* 로컬 서버 다운 — 폴백 진행 */ }

      // 2단계: 폴백 — 클라우드 직접 refresh
      const rt = localStorage.getItem(RT_KEY)
      if (rt) {
        try {
          const { data } = await axios.post(`${CLOUD_URL}/api/v1/auth/refresh`, { refresh_token: rt })
          const newJwt = data.data?.access_token ?? data.access_token
          const newRt = data.data?.refresh_token ?? data.refresh_token
          if (!newJwt || !newRt) throw new Error('Invalid refresh response')
          sessionStorage.setItem(JWT_KEY, newJwt)
          localStorage.setItem(RT_KEY, newRt)
          localAuth.setAuthToken(newJwt, newRt).catch(() => {})
          window.dispatchEvent(new CustomEvent(AUTH_EVENTS.TOKEN_REFRESHED, { detail: { jwt: newJwt, rt: newRt } }))
          original.headers.Authorization = `Bearer ${newJwt}`
          return client(original)
        } catch {
          sessionStorage.removeItem(JWT_KEY)
          localStorage.removeItem(RT_KEY)
          window.dispatchEvent(new CustomEvent(AUTH_EVENTS.AUTH_EXPIRED))
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
  get: (): Promise<MarketContextData> =>
    client.get('/api/v1/context').then((r) => {
      const d = r.data.data ?? r.data
      const m = d.market ?? {}
      return {
        kospi_rsi: m.kospi_rsi,
        kosdaq_rsi: m.kosdaq_rsi,
        volatility: m.volatility,
        trend: m.market_trend,
        updated_at: d.computed_at,
      }
    }),
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

/** 시세 데이터 — /api/v1/stocks/{symbol}/bars, /quote */
export interface DailyBar {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface StockQuote {
  symbol: string
  price: number
  change: number
  change_pct: number
  volume: number
  updated_at: string
}

export const cloudBars = {
  get: (symbol: string, start?: string, end?: string) =>
    client.get<{ data: DailyBar[] }>(`/api/v1/stocks/${symbol}/bars`, { params: { start, end } })
      .then((r) => r.data.data ?? []),
}

export const cloudQuote = {
  get: (symbol: string) =>
    client.get<{ data: StockQuote }>(`/api/v1/stocks/${symbol}/quote`)
      .then((r) => r.data.data ?? null),
}

/** 시장 브리핑 — /api/v1/ai/briefing */
export interface MarketBriefing {
  date: string
  summary: string
  sentiment: 'bearish' | 'slightly_bearish' | 'neutral' | 'slightly_bullish' | 'bullish'
  indices: {
    kospi:   { close: number; change_pct: number } | null
    kosdaq:  { close: number; change_pct: number } | null
    sp500:   { close: number; change_pct: number } | null
    nasdaq:  { close: number; change_pct: number } | null
    usd_krw: number | null
  }
  source: 'claude' | 'cache' | 'stub'
  generated_at: string
}

export const cloudAI = {
  getBriefing: (date?: string) =>
    client.get<{ success: boolean; data: MarketBriefing }>(
      '/api/v1/ai/briefing',
      date ? { params: { date } } : undefined,
    ).then((r) => r.data.data),

  getStockAnalysis: (symbol: string, date?: string) =>
    client.get<{ success: boolean; data: StockAnalysis }>(
      `/api/v1/ai/stock-analysis/${symbol}`,
      date ? { params: { date } } : undefined,
    ).then((r) => r.data.data),
}

/** 종목별 AI 분석 — /api/v1/ai/stock-analysis/{symbol} */
export interface StockAnalysis {
  symbol: string
  name: string | null
  date: string
  summary: string | null
  sentiment: 'bearish' | 'slightly_bearish' | 'neutral' | 'slightly_bullish' | 'bullish'
  source: 'claude' | 'cache' | 'stub'
  generated_at: string
}

/** OAuth2 — /api/v1/auth/oauth */
export const cloudOAuth = {
  getGoogleLoginUrl: (redirectUri: string) =>
    client.get<{ data: { auth_url: string } }>(
      '/api/v1/auth/oauth/google/login',
      { params: { redirect_uri: redirectUri } },
    ).then((r) => r.data.data.auth_url),

  googleCallback: (code: string, redirectUri: string) =>
    client.post<{ data: { access_token: string; refresh_token: string; expires_in: number } }>(
      '/api/v1/auth/oauth/google/callback',
      { code, redirect_uri: redirectUri },
    ).then((r) => r.data.data),

  getKakaoLoginUrl: (redirectUri: string) =>
    client.get<{ data: { auth_url: string } }>(
      '/api/v1/auth/oauth/kakao/login',
      { params: { redirect_uri: redirectUri } },
    ).then((r) => r.data.data.auth_url),

  kakaoCallback: (code: string, redirectUri: string) =>
    client.post<{ data: { access_token: string; refresh_token: string; expires_in: number } }>(
      '/api/v1/auth/oauth/kakao/callback',
      { code, redirect_uri: redirectUri },
    ).then((r) => r.data.data),
}

/** 디바이스 관리 — /api/v1/devices */
export interface DeviceInfo {
  id: string
  name: string | null
  platform: string | null
  registered_at: string | null
  last_seen_at: string | null
}

export const cloudDevices = {
  list: () =>
    client.get<{ data: DeviceInfo[]; count: number }>('/api/v1/devices')
      .then((r) => r.data.data),

  register: (deviceId: string, name?: string, platform?: string) =>
    client.post('/api/v1/devices/register', { device_id: deviceId, name, platform }),

  deactivate: (deviceId: string) =>
    client.delete(`/api/v1/devices/${deviceId}`),
}

/** 비밀번호 재검증 — /api/v1/auth/verify-password */
export const cloudVerifyPassword = {
  verify: (password: string) =>
    client.post<{ success: boolean }>('/api/v1/auth/verify-password', { password })
      .then((r) => r.data.success),
}

/** 헬스 체크 — /health */
export const cloudHealth = {
  check: () =>
    axios.get(`${CLOUD_URL}/health`, { timeout: 5000 }).then((r) => r.data).catch(() => null),
}

/** 약관 동의 — /api/v1/legal */
export const legalApi = {
  getConsentStatus: () =>
    client.get('/api/v1/legal/consent/status').then(r => r.data),
  recordConsent: (docType: string, docVersion: string) =>
    client.post('/api/v1/legal/consent', { doc_type: docType, doc_version: docVersion }).then(r => r.data),
}

export default client
