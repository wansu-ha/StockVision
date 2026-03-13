/** 어드민 권한 가드. JWT payload에서 role=admin 확인. */
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
}

/** JWT payload를 디코딩하여 role을 추출한다. */
function getRoleFromJwt(jwt: string | null): string | null {
  if (!jwt) return null
  try {
    const payload = JSON.parse(atob(jwt.split('.')[1]))
    return payload.role ?? null
  } catch {
    return null
  }
}

export default function AdminGuard({ children }: Props) {
  const { isAuthenticated, jwt } = useAuth()

  // DEV: 서버 없이 UI 확인용 bypass
  if (import.meta.env.DEV && import.meta.env.VITE_AUTH_BYPASS === 'true') return <>{children}</>

  if (!isAuthenticated) return <Navigate to="/admin/login" replace />

  const role = getRoleFromJwt(jwt)
  if (role !== 'admin') return <Navigate to="/" replace />

  return <>{children}</>
}
