import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import type { ReactNode } from 'react'
import { cloudAuth } from '../services/cloudClient'
import { localAuth } from '../services/localClient'
import { AUTH_EVENTS } from './authEvents'

interface AuthState {
  jwt: string | null
  refreshToken: string | null
  email: string | null
  isAuthenticated: boolean
  localReady: boolean
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string, keepLoggedIn?: boolean) => Promise<void>
  logout: () => Promise<void>
  loginWithTokens: (jwt: string, rt: string) => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

const STORAGE_KEY_JWT = 'sv_jwt'
const STORAGE_KEY_RT  = 'sv_rt'
const STORAGE_KEY_EMAIL = 'sv_email'
const STORAGE_KEY_KEEP = 'sv_keep_logged_in'

/** S3: RT 저장소 — keepLoggedIn이면 localStorage, 아니면 sessionStorage */
function getRtStorage(): Storage {
  return localStorage.getItem(STORAGE_KEY_KEEP) === '1' ? localStorage : sessionStorage
}

function saveRt(rt: string): void {
  getRtStorage().setItem(STORAGE_KEY_RT, rt)
}

function loadRt(): string | null {
  // 양쪽 모두 확인 (마이그레이션 + 호환)
  return localStorage.getItem(STORAGE_KEY_RT) ?? sessionStorage.getItem(STORAGE_KEY_RT)
}

function clearRt(): void {
  localStorage.removeItem(STORAGE_KEY_RT)
  sessionStorage.removeItem(STORAGE_KEY_RT)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(() => ({
    jwt:          sessionStorage.getItem(STORAGE_KEY_JWT),
    refreshToken: loadRt(),
    email:        localStorage.getItem(STORAGE_KEY_EMAIL),
    isAuthenticated: !!sessionStorage.getItem(STORAGE_KEY_JWT),
    localReady: false,
  }))

  // 마운트 시 로컬 서버에 토큰 동기화 + JWT 자동 갱신
  const initCalled = useRef(false)
  useEffect(() => {
    if (initCalled.current) return
    initCalled.current = true

    const jwt = sessionStorage.getItem(STORAGE_KEY_JWT)
    const rt = loadRt()

    if (jwt && rt) {
      // JWT 있음 → 로컬 서버에 토큰 전달 (set_active_user 트리거)
      // 로컬 서버 미실행 시에도 localReady=true로 전환 (원격 접속 허용)
      localAuth.setAuthToken(jwt, rt)
        .then(() => setState(prev => ({ ...prev, localReady: true })))
        .catch(() => setState(prev => ({ ...prev, localReady: true })))
    } else if (rt) {
      // JWT 만료, RT 있음 → 클라우드에서 갱신
      cloudAuth.refresh(rt)
        .then(async (res) => {
          const d = res.data
          sessionStorage.setItem(STORAGE_KEY_JWT, d.access_token)
          saveRt(d.refresh_token)
          await localAuth.setAuthToken(d.access_token, d.refresh_token).catch(() => {})
          setState(prev => ({
            ...prev,
            jwt: d.access_token,
            refreshToken: d.refresh_token,
            email: localStorage.getItem(STORAGE_KEY_EMAIL),
            isAuthenticated: true,
            localReady: true,
          }))
        })
        .catch(() => {
          clearRt()
          localStorage.removeItem(STORAGE_KEY_EMAIL)
          setState(prev => ({ ...prev, localReady: true }))
        })
    } else {
      // 브라우저에 토큰 없음 → 로컬 서버에서 복원
      localAuth.restore().then((res) => {
        const d = res?.data
        if (d?.access_token && d?.refresh_token) {
          sessionStorage.setItem(STORAGE_KEY_JWT, d.access_token)
          saveRt(d.refresh_token)
          if (d.email) localStorage.setItem(STORAGE_KEY_EMAIL, d.email)
          setState(prev => ({
            ...prev,
            jwt: d.access_token, refreshToken: d.refresh_token,
            email: d.email ?? null, isAuthenticated: true, localReady: true,
          }))
        } else {
          setState(prev => ({ ...prev, localReady: true }))
        }
      })
    }
  }, [])

  // 401 인터셉터에서 토큰 갱신/만료 시 상태 동기화
  useEffect(() => {
    const handleRefreshed = (e: Event) => {
      const { jwt, rt } = (e as CustomEvent).detail
      setState(prev => ({ ...prev, jwt, refreshToken: rt, isAuthenticated: true }))
    }
    const handleExpired = () => {
      sessionStorage.removeItem(STORAGE_KEY_JWT)
      clearRt()
      localStorage.removeItem(STORAGE_KEY_EMAIL)
      setState(prev => ({ ...prev, jwt: null, refreshToken: null, email: null, isAuthenticated: false }))
    }
    window.addEventListener(AUTH_EVENTS.TOKEN_REFRESHED, handleRefreshed)
    window.addEventListener(AUTH_EVENTS.AUTH_EXPIRED, handleExpired)
    return () => {
      window.removeEventListener(AUTH_EVENTS.TOKEN_REFRESHED, handleRefreshed)
      window.removeEventListener(AUTH_EVENTS.AUTH_EXPIRED, handleExpired)
    }
  }, [])

  const login = useCallback(async (email: string, password: string, keepLoggedIn = false) => {
    const res = await cloudAuth.login(email, password)
    const d = res.data
    // S3: keepLoggedIn 여부에 따라 RT 저장소 결정
    if (keepLoggedIn) {
      localStorage.setItem(STORAGE_KEY_KEEP, '1')
    } else {
      localStorage.removeItem(STORAGE_KEY_KEEP)
    }
    sessionStorage.setItem(STORAGE_KEY_JWT, d.access_token)
    saveRt(d.refresh_token)
    localStorage.setItem(STORAGE_KEY_EMAIL, email)
    await localAuth.setAuthToken(d.access_token, d.refresh_token)
    setState({
      jwt: d.access_token,
      refreshToken: d.refresh_token,
      email,
      isAuthenticated: true,
      localReady: true,
    })
  }, [])

  const loginWithTokens = useCallback(async (jwt: string, rt: string) => {
    sessionStorage.setItem(STORAGE_KEY_JWT, jwt)
    saveRt(rt)
    await localAuth.setAuthToken(jwt, rt)
    setState(prev => ({ ...prev, jwt, refreshToken: rt, isAuthenticated: true, localReady: true }))
  }, [])

  const logout = useCallback(async () => {
    // 즉시 스토리지 정리 + 상태 초기화 (서버 응답 안 기다림)
    const rt = loadRt()
    sessionStorage.removeItem(STORAGE_KEY_JWT)
    clearRt()
    localStorage.removeItem(STORAGE_KEY_EMAIL)
    localStorage.removeItem(STORAGE_KEY_KEEP)
    setState({ jwt: null, refreshToken: null, email: null, isAuthenticated: false, localReady: false })
    // 서버 측 정리는 fire-and-forget
    if (rt) cloudAuth.logout(rt).catch(() => {})
    localAuth.logout()
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, logout, loginWithTokens }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth는 AuthProvider 내부에서 사용하세요.')
  return ctx
}
