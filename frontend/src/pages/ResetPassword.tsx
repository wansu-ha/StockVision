import { useState, useEffect } from 'react'
import type { FormEvent } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { authApi } from '../services/auth'

export default function ResetPassword() {
  const [params]  = useSearchParams()
  const navigate  = useNavigate()
  // S8: fragment 우선, 쿼리스트링 폴백 (하위 호환)
  const [token] = useState(() => {
    const hash = window.location.hash
    if (hash) {
      const fragParams = new URLSearchParams(hash.slice(1))
      return fragParams.get('token') ?? params.get('token') ?? ''
    }
    return params.get('token') ?? ''
  })

  // S8: fragment에서 토큰 추출 후 URL에서 제거 (히스토리 노출 방지)
  useEffect(() => {
    if (window.location.hash) {
      window.history.replaceState(null, '', window.location.pathname)
    }
  }, [])

  const [password, setPassword]   = useState('')
  const [confirm, setConfirm]     = useState('')
  const [error, setError]         = useState('')
  const [loading, setLoading]     = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (password !== confirm) {
      setError('비밀번호가 일치하지 않습니다.')
      return
    }
    setError('')
    setLoading(true)
    try {
      await authApi.resetPassword(token, password)
      navigate('/login', { state: { message: '비밀번호가 재설정되었습니다. 다시 로그인해주세요.' } })
    } catch (err: any) {
      setError(err?.response?.data?.detail || '비밀번호 재설정에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center text-red-400">유효하지 않은 링크입니다.</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-xl shadow p-8">
        <h1 className="text-2xl font-bold mb-6 text-center text-gray-100">새 비밀번호 설정</h1>

        {error && (
          <div className="mb-4 p-3 rounded bg-red-900/30 border border-red-800/50 text-red-400 text-sm">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-400">새 비밀번호</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
              required
              minLength={8}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-400">비밀번호 확인</label>
            <input
              type="password"
              value={confirm}
              onChange={e => setConfirm(e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 text-white py-2 rounded-xl hover:bg-indigo-500 disabled:opacity-50 transition"
          >
            {loading ? '처리 중...' : '비밀번호 재설정'}
          </button>
        </form>
      </div>
    </div>
  )
}
