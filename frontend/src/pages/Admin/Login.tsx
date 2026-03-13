/** 어드민 전용 로그인 페이지 — 흰색 테마, role!=admin 거부 */
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

/** JWT payload에서 role 추출 */
function getRoleFromJwt(jwt: string | null): string | null {
  if (!jwt) return null
  try {
    return JSON.parse(atob(jwt.split('.')[1])).role ?? null
  } catch {
    return null
  }
}

export default function AdminLogin() {
  const { login, logout } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      // login()이 sessionStorage에 JWT를 저장하므로 직접 읽는다
      const jwt = sessionStorage.getItem('sv_jwt')
      const role = getRoleFromJwt(jwt)
      if (role === 'admin') {
        navigate('/admin', { replace: true })
      } else {
        setError('관리자 권한이 없습니다.')
        await logout()
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail
      setError(msg || '로그인에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm bg-white border border-gray-200 rounded-2xl shadow-sm p-8">
        <h1 className="text-xl font-bold mb-1 text-center text-gray-900">StockVision</h1>
        <p className="text-sm text-gray-400 text-center mb-6">Admin</p>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-600">이메일</label>
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-indigo-400 transition"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-600">비밀번호</label>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-indigo-400 transition"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-gray-900 text-white rounded-xl text-sm font-medium hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {loading ? '로그인 중...' : '로그인'}
          </button>
        </form>
      </div>
    </div>
  )
}
