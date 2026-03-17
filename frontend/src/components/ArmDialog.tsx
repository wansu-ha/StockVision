/**
 * Arm(재개) 다이얼로그 — 비밀번호 재입력 확인.
 *
 * 재개 조건: 로컬 온라인 + 브로커 연결 + 비정상 상태 없음.
 * 조건 미충족 시 사유 표시, 버튼 비활성.
 */
import { useState } from 'react'
import { cloudVerifyPassword } from '../services/cloudClient'
import { getApiError } from '../utils/apiError'
import type { RemoteState } from '../types'

interface Props {
  state: RemoteState
  onArm: () => void
  onClose: () => void
}

export default function ArmDialog({ state, onArm, onClose }: Props) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // 재개 가능 조건 체크
  const conditions = [
    { ok: state.local_online, label: '로컬 서버 온라인', reason: '로컬 서버가 오프라인입니다' },
    { ok: state.broker_connected, label: '브로커 연결', reason: '브로커가 연결되지 않았습니다' },
    { ok: !state.loss_lock, label: '손실 락 없음', reason: '일일 손실 제한이 발동 중입니다' },
  ]
  const allOk = conditions.every(c => c.ok)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const ok = await cloudVerifyPassword.verify(password)
      if (ok) {
        onArm()
        onClose()
      } else {
        setError('비밀번호가 올바르지 않습니다.')
      }
    } catch (err: unknown) {
      setError(getApiError(err, '비밀번호 검증에 실패했습니다.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl p-6 max-w-sm w-full mx-4 space-y-4">
        <h4 className="text-lg font-medium text-green-400">엔진 재개</h4>

        {/* 조건 체크 */}
        <div className="space-y-1">
          {conditions.map((c, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <span className={c.ok ? 'text-green-400' : 'text-red-400'}>
                {c.ok ? '●' : '●'}
              </span>
              <span className={c.ok ? 'text-gray-300' : 'text-red-300'}>
                {c.ok ? c.label : c.reason}
              </span>
            </div>
          ))}
        </div>

        {allOk ? (
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">비밀번호 확인</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-green-500"
                autoFocus
                required
              />
            </div>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-3 py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg"
              >
                취소
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-3 py-2 text-sm bg-green-600 hover:bg-green-700 rounded-lg text-white font-medium disabled:opacity-50"
              >
                {loading ? '확인 중...' : '재개'}
              </button>
            </div>
          </form>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="flex-1 px-3 py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg"
            >
              닫기
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
