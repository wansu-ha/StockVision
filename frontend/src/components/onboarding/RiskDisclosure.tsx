/** 위험고지 카드 — 온보딩 시 서버 연결 전 표시. */
import { useState } from 'react'

interface Props {
  onAccept: () => void
}

const ITEMS = [
  {
    icon: '🔒',
    title: '로컬 실행',
    desc: '주문은 이 PC에서만 실행됩니다. 증권사 비밀번호는 Windows 자격 증명에 안전하게 저장되며, 외부 서버로 전송되지 않습니다.',
    color: 'border-blue-800/50 bg-blue-900/10',
  },
  {
    icon: '⚖️',
    title: '사용자 책임',
    desc: '자동매매 결과에 대한 책임은 사용자에게 있습니다. 시스템 오류, 네트워크 장애 등으로 인한 손실이 발생할 수 있습니다.',
    color: 'border-yellow-800/50 bg-yellow-900/10',
  },
  {
    icon: '🧪',
    title: '모의투자 권장',
    desc: '실전 투자 전에 모의투자로 충분히 테스트하세요. 증권사 모의투자 계정으로 안전하게 전략을 검증할 수 있습니다.',
    color: 'border-green-800/50 bg-green-900/10',
  },
]

export default function RiskDisclosure({ onAccept }: Props) {
  const [checked, setChecked] = useState(false)

  return (
    <div className="space-y-5">
      <div className="grid gap-3">
        {ITEMS.map((item) => (
          <div key={item.title} className={`flex gap-3.5 border rounded-lg p-4 ${item.color}`}>
            <span className="text-2xl shrink-0 leading-none mt-0.5">{item.icon}</span>
            <div>
              <div className="text-sm font-semibold text-gray-200">{item.title}</div>
              <div className="text-xs text-gray-400 mt-1 leading-relaxed">{item.desc}</div>
            </div>
          </div>
        ))}
      </div>

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
          className="w-4 h-4 rounded bg-gray-800 border-gray-600 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-0"
        />
        <span className="text-sm text-gray-300">위 내용을 확인했습니다</span>
      </label>

      <button
        onClick={onAccept}
        disabled={!checked}
        className="w-full py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition"
      >
        다음
      </button>
    </div>
  )
}
