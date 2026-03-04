import { useState } from 'react'

interface Props {
  onAccept: () => void
  loading?: boolean
}

export default function RiskDisclosure({ onAccept, loading }: Props) {
  const [check1, setCheck1] = useState(false)
  const [check2, setCheck2] = useState(false)

  return (
    <div className="space-y-6">
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-5">
        <h3 className="text-base font-semibold text-yellow-800 mb-3">⚠️ 투자 위험 고지</h3>
        <p className="text-sm text-yellow-700 leading-relaxed">
          본 서비스는 사용자가 직접 정의한 자동매매 규칙을 실행하는 <strong>"시스템매매 도구"</strong>입니다.
          투자 추천이나 투자 일임 서비스가 아닙니다.
        </p>
        <ul className="mt-3 space-y-1 text-sm text-yellow-700 list-disc list-inside">
          <li>모든 투자 의사결정의 주체는 사용자입니다</li>
          <li>원금 손실이 발생할 수 있습니다</li>
          <li>과거 성과가 미래 수익을 보장하지 않습니다</li>
        </ul>
      </div>

      <div className="space-y-3">
        <label className="flex items-start gap-3 cursor-pointer">
          <input type="checkbox" checked={check1} onChange={e => setCheck1(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600" />
          <span className="text-sm text-gray-700">
            위 위험 고지 내용을 모두 읽었으며, 본 서비스가 투자 추천 서비스가 아님을 이해합니다.
          </span>
        </label>
        <label className="flex items-start gap-3 cursor-pointer">
          <input type="checkbox" checked={check2} onChange={e => setCheck2(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600" />
          <span className="text-sm text-gray-700">
            투자로 인한 손실에 대한 책임이 본인에게 있음을 동의합니다.
          </span>
        </label>
      </div>

      <button
        onClick={onAccept}
        disabled={!check1 || !check2 || loading}
        className="w-full py-2.5 px-4 rounded-lg bg-blue-600 text-white font-medium
                   disabled:opacity-40 disabled:cursor-not-allowed hover:bg-blue-700 transition"
      >
        {loading ? '처리 중...' : '동의하고 계속하기'}
      </button>
    </div>
  )
}
