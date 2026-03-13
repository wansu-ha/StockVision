import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../services/auth'

export default function ForgotPassword() {
  const [email, setEmail]   = useState('')
  const [done, setDone]     = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await authApi.forgotPassword(email)
    } finally {
      setLoading(false)
      setDone(true)  // 이메일 존재 여부 무관 항상 완료 표시 (열거 방지)
    }
  }

  if (done) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-xl shadow p-8 text-center">
          <h2 className="text-xl font-bold mb-4 text-gray-100">메일을 발송했습니다</h2>
          <p className="text-gray-400 mb-6">
            해당 이메일로 계정이 등록되어 있다면 비밀번호 재설정 링크를 발송했습니다.
          </p>
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300 transition">로그인으로 돌아가기</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-xl shadow p-8">
        <h1 className="text-2xl font-bold mb-2 text-center text-gray-100">비밀번호 찾기</h1>
        <p className="text-sm text-gray-500 mb-6 text-center">
          가입한 이메일을 입력하면 재설정 링크를 보내드립니다.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-400">이메일</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 text-white py-2 rounded-xl hover:bg-indigo-500 disabled:opacity-50 transition"
          >
            {loading ? '발송 중...' : '재설정 링크 발송'}
          </button>
        </form>

        <p className="mt-4 text-sm text-center">
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300 transition">로그인으로 돌아가기</Link>
        </p>
      </div>
    </div>
  )
}
