/**
 * ConsentGate — 약관 재동의 강제 게이트.
 *
 * ProtectedRoute 내부에서 children을 감싸며,
 * terms/privacy 중 하나라도 up_to_date=false이면 강제 모달 표시.
 * 동의 전까지 서비스 접근 불가 (로그아웃만 가능).
 */
import { useState } from 'react'
import type { ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useConsentStatus } from '../hooks/useConsentStatus'
import type { ConsentItem } from '../hooks/useConsentStatus'
import { legalApi } from '../services/cloudClient'
import { useAuth } from '../context/AuthContext'

interface Props {
  children: ReactNode
}

export default function ConsentGate({ children }: Props) {
  const { data, isLoading, isError, refetch } = useConsentStatus()
  const { logout } = useAuth()
  const queryClient = useQueryClient()

  const [agreed, setAgreed] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  // 로딩 중 — 동의 확인 전 접근 차단
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400 text-sm">동의 상태 확인 중...</div>
      </div>
    )
  }

  // API 에러 — 차단 유지 + 재시도
  if (isError || !data) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="bg-gray-800 rounded-xl p-6 max-w-sm w-full mx-4 space-y-4 text-center">
          <p className="text-gray-300 text-sm">동의 상태를 확인할 수 없습니다.</p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 rounded-lg text-white"
          >
            다시 시도
          </button>
        </div>
      </div>
    )
  }

  // 재동의 필요 항목 수집
  const outdated: { type: string; label: string; item: ConsentItem }[] = []
  if (!data.terms.up_to_date) {
    outdated.push({ type: 'terms', label: '이용약관', item: data.terms })
  }
  if (!data.privacy.up_to_date) {
    outdated.push({ type: 'privacy', label: '개인정보처리방침', item: data.privacy })
  }

  // 모두 최신 → 통과
  if (outdated.length === 0) {
    return <>{children}</>
  }

  // 재동의 모달 (닫기 불가)
  const handleConsent = async () => {
    setSubmitting(true)
    setError('')
    try {
      for (const doc of outdated) {
        await legalApi.recordConsent(doc.type, doc.item.latest_version)
      }
      queryClient.invalidateQueries({ queryKey: ['consentStatus'] })
      setAgreed(false)
    } catch {
      setError('동의 처리에 실패했습니다. 다시 시도해 주세요.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 space-y-4">
        <h4 className="text-lg font-medium text-yellow-400">약관 변경 안내</h4>
        <p className="text-sm text-gray-300">
          서비스 약관이 변경되었습니다.<br />
          계속 이용하시려면 변경된 약관에 동의해 주세요.
        </p>

        {/* 변경된 약관 목록 */}
        <div className="space-y-2">
          {outdated.map(doc => (
            <div key={doc.type} className="flex items-center justify-between bg-gray-900 rounded-lg px-4 py-3">
              <span className="text-sm text-gray-200">
                {doc.label} ({doc.item.agreed_version ?? '없음'} → {doc.item.latest_version})
              </span>
              <a
                href={`/legal/${doc.type}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                변경 확인
              </a>
            </div>
          ))}
        </div>

        {/* 동의 체크박스 */}
        <label className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={agreed}
            onChange={e => setAgreed(e.target.checked)}
            className="mt-0.5 accent-blue-500"
          />
          <span className="text-sm text-gray-300">변경된 약관 내용을 확인하고 동의합니다</span>
        </label>

        {error && <p className="text-sm text-red-400">{error}</p>}

        {/* 버튼 */}
        <div className="flex gap-2">
          <button
            onClick={() => logout()}
            className="flex-1 px-3 py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg"
          >
            로그아웃
          </button>
          <button
            onClick={handleConsent}
            disabled={!agreed || submitting}
            className="flex-1 px-3 py-2 text-sm bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium disabled:opacity-50"
          >
            {submitting ? '처리 중...' : '동의하고 계속'}
          </button>
        </div>
      </div>
    </div>
  )
}
