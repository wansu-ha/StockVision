import { useState, FormEvent } from 'react'
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
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-full max-w-md bg-white rounded-xl shadow p-8 text-center">
          <h2 className="text-xl font-bold mb-4">메일을 발송했습니다</h2>
          <p className="text-gray-600 mb-6">
            해당 이메일로 계정이 등록되어 있다면 비밀번호 재설정 링크를 발송했습니다.
          </p>
          <Link to="/login" className="text-blue-600 hover:underline">로그인으로 돌아가기</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md bg-white rounded-xl shadow p-8">
        <h1 className="text-2xl font-bold mb-2 text-center">비밀번호 찾기</h1>
        <p className="text-sm text-gray-500 mb-6 text-center">
          가입한 이메일을 입력하면 재설정 링크를 보내드립니다.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">이메일</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? '발송 중...' : '재설정 링크 발송'}
          </button>
        </form>

        <p className="mt-4 text-sm text-center">
          <Link to="/login" className="text-blue-600 hover:underline">로그인으로 돌아가기</Link>
        </p>
      </div>
    </div>
  )
}
