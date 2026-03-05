import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import { cloudAuth } from '../services/cloudClient'

interface AuthState {
  jwt: string | null
  refreshToken: string | null
  email: string | null
  isAuthenticated: boolean
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
  }))

  // 마운트 시 Refresh Token으로 JWT 자동 갱신
  useEffect(() => {
    const rt = localStorage.getItem(STORAGE_KEY_RT)
    if (rt && !sessionStorage.getItem(STORAGE_KEY_JWT)) {
      cloudAuth.refresh(rt)
        .then((res) => {
          const d = res.data
          sessionStorage.setItem(STORAGE_KEY_JWT, d.access_token)
          localStorage.setItem(STORAGE_KEY_RT, d.refresh_token)
          setState({
            jwt: d.access_token,
            refreshToken: d.refresh_token,
            email: localStorage.getItem(STORAGE_KEY_EMAIL),
            isAuthenticated: true,
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
    setState({
      jwt: d.access_token,
      refreshToken: d.refresh_token,
      email,
      isAuthenticated: true,
    })
  }, [])

  const logout = useCallback(async () => {
    const rt = localStorage.getItem(STORAGE_KEY_RT)
    if (rt) await cloudAuth.logout(rt).catch(() => {})
    sessionStorage.removeItem(STORAGE_KEY_JWT)
    localStorage.removeItem(STORAGE_KEY_RT)
    localStorage.removeItem(STORAGE_KEY_EMAIL)
    setState({ jwt: null, refreshToken: null, email: null, isAuthenticated: false })
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
