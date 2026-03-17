/**
 * DisclaimerModal — 투자 면책 고지 확인 모달.
 *
 * 전략 엔진 시작 시 disclaimer 미동의 상태이면 표시.
 * 동의 후 POST /consent 기록 → 엔진 시작 진행.
 */
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { legalApi } from '../services/cloudClient'

interface Props {
  latestVersion: string
  onAccepted: () => void
  onCancel: () => void
}

const RISK_ITEMS = [
  '모든 매매 규칙은 사용자가 직접 정의합니다.',
  'AI/LLM 정보는 참고용이며 투자 추천이 아닙니다.',
  '과거 성과는 미래 수익을 보장하지 않습니다.',
  '시스템 오류로 인한 손실이 발생할 수 있습니다.',
  '투자 손익은 사용자 본인에게 귀속됩니다.',
]

export default function DisclaimerModal({ latestVersion, onAccepted, onCancel }: Props) {
  const [agreed, setAgreed] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const queryClient = useQueryClient()

  const handleAccept = async () => {
    setSubmitting(true)
    setError('')
    try {
      await legalApi.recordConsent('disclaimer', latestVersion)
      queryClient.invalidateQueries({ queryKey: ['consentStatus'] })
    } catch {
      setError('동의 처리에 실패했습니다. 다시 시도해 주세요.')
      setSubmitting(false)
      return
    }
    // 성공 시 — 부모가 모달을 unmount하므로 setState 하지 않음
    onAccepted()
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl p-6 max-w-md w-full mx-4 space-y-4">
        <h4 className="text-lg font-medium text-yellow-400">투자 위험 고지</h4>
        <p className="text-sm text-gray-300">자동매매를 시작하기 전에 확인해 주세요.</p>

        <ul className="space-y-2">
          {RISK_ITEMS.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-200">
              <span className="text-yellow-500 mt-0.5">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>

        <a
          href="/legal/disclaimer"
          target="_blank"
          rel="noopener noreferrer"
          className="block text-xs text-blue-400 hover:text-blue-300"
        >
          투자 위험 고지 전문 보기
        </a>

        <label className="flex items-start gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={agreed}
            onChange={e => setAgreed(e.target.checked)}
            className="mt-0.5 accent-blue-500"
          />
          <span className="text-sm text-gray-300">위 내용을 확인하고 동의합니다</span>
        </label>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex gap-2">
          <button
            onClick={onCancel}
            className="flex-1 px-3 py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg"
          >
            취소
          </button>
          <button
            onClick={handleAccept}
            disabled={!agreed || submitting}
            className="flex-1 px-3 py-2 text-sm bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium disabled:opacity-50"
          >
            {submitting ? '처리 중...' : '동의하고 시작'}
          </button>
        </div>
      </div>
    </div>
  )
}
