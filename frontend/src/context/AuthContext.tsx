import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { ReactNode } from 'react'
import { cloudAuth } from '../services/cloudClient'
import { localAuth } from '../services/localClient'

interface AuthState {
  jwt: string | null
  refreshToken: string | null
  email: string | null
  isAuthenticated: boolean
  localReady: boolean
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

const STORAGE_KEY_JWT = 'sv_jwt'
const STORAGE_KEY_RT  = 'sv_rt'
const STORAGE_KEY_EMAIL = 'sv_email'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(() => ({
    jwt:          sessionStorage.getItem(STORAGE_KEY_JWT),
    refreshToken: localStorage.getItem(STORAGE_KEY_RT),
    email:        localStorage.getItem(STORAGE_KEY_EMAIL),
    isAuthenticated: !!sessionStorage.getItem(STORAGE_KEY_JWT),
    localReady: false,
  }))

  // 마운트 시 로컬 서버에 토큰 동기화 + JWT 자동 갱신
  useEffect(() => {
    const jwt = sessionStorage.getItem(STORAGE_KEY_JWT)
    const rt = localStorage.getItem(STORAGE_KEY_RT)

    if (jwt && rt) {
      // JWT 있음 → 로컬 서버에 토큰 전달 (set_active_user 트리거)
      localAuth.setAuthToken(jwt, rt).then(() => {
        setState(prev => ({ ...prev, localReady: true }))
      })
    } else if (rt) {
      // JWT 만료, RT 있음 → 클라우드에서 갱신
      cloudAuth.refresh(rt)
        .then((res) => {
          const d = res.data
          sessionStorage.setItem(STORAGE_KEY_JWT, d.access_token)
          localStorage.setItem(STORAGE_KEY_RT, d.refresh_token)
          localAuth.setAuthToken(d.access_token, d.refresh_token).then(() => {
            setState(prev => ({ ...prev, localReady: true }))
          })
          setState({
            jwt: d.access_token,
            refreshToken: d.refresh_token,
            email: localStorage.getItem(STORAGE_KEY_EMAIL),
            isAuthenticated: true,
            localReady: false,
          })
        })
        .catch(() => {
          localStorage.removeItem(STORAGE_KEY_RT)
          localStorage.removeItem(STORAGE_KEY_EMAIL)
        })
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await cloudAuth.login(email, password)
    const d = res.data
    sessionStorage.setItem(STORAGE_KEY_JWT, d.access_token)
    localStorage.setItem(STORAGE_KEY_RT, d.refresh_token)
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

  const logout = useCallback(async () => {
    // 즉시 스토리지 정리 + 상태 초기화 (서버 응답 안 기다림)
    const rt = localStorage.getItem(STORAGE_KEY_RT)
    sessionStorage.removeItem(STORAGE_KEY_JWT)
    localStorage.removeItem(STORAGE_KEY_RT)
    localStorage.removeItem(STORAGE_KEY_EMAIL)
    setState({ jwt: null, refreshToken: null, email: null, isAuthenticated: false, localReady: false })
    // 서버 측 정리는 fire-and-forget
    if (rt) cloudAuth.logout(rt).catch(() => {})
    localAuth.logout()
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth는 AuthProvider 내부에서 사용하세요.')
  return ctx
}
