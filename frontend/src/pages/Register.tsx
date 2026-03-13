import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../services/auth'

export default function Register() {
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [error, setError]       = useState('')
  const [done, setDone]         = useState(false)
  const [loading, setLoading]   = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.register(email, password, nickname || undefined)
      setDone(true)
    } catch (err: any) {
      setError(err?.response?.data?.detail || '회원가입에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-xl shadow p-8 text-center">
          <h2 className="text-xl font-bold mb-4 text-gray-100">인증 메일을 발송했습니다</h2>
          <p className="text-gray-400 mb-6">
            <strong className="text-gray-200">{email}</strong>으로 인증 메일을 발송했습니다.
            받은 편지함을 확인하여 이메일 인증을 완료해주세요.
          </p>
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300 transition">로그인으로 이동</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-xl shadow p-8">
        <h1 className="text-2xl font-bold mb-6 text-center text-gray-100">회원가입</h1>

        {error && (
          <div className="mb-4 p-3 rounded bg-red-900/30 border border-red-800/50 text-red-400 text-sm">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-400">이메일</label>
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-400">비밀번호</label>
            <input
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
              required
              minLength={8}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-400">닉네임 (선택)</label>
            <input
              type="text"
              value={nickname}
              onChange={e => setNickname(e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 text-white py-2 rounded-xl hover:bg-indigo-500 disabled:opacity-50 transition"
          >
            {loading ? '처리 중...' : '회원가입'}
          </button>
        </form>

        <p className="mt-4 text-sm text-center text-gray-500">
          이미 계정이 있으신가요?{' '}
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300 transition">로그인</Link>
        </p>
      </div>
    </div>
  )
}
