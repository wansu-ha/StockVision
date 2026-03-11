/** 위험고지 카드 — 온보딩 시 서버 연결 전 표시. */
import { useState } from 'react'

interface Props {
  onAccept: () => void
}

const ITEMS = [
  { icon: '🖥️', title: '로컬 실행', desc: '주문은 내 PC에서만 실행됩니다. 클라우드 서버가 주문하지 않습니다.' },
  { icon: '🔒', title: 'API 키 미전송', desc: '증권사 API 키는 이 PC에만 저장됩니다. 외부로 전송되지 않습니다.' },
  { icon: '⚠️', title: '사용자 책임', desc: '자동매매 결과에 대한 책임은 사용자에게 있습니다. 모의투자로 먼저 테스트하세요.' },
]

export default function RiskDisclosure({ onAccept }: Props) {
  const [checked, setChecked] = useState(false)

  return (
    <div className="space-y-5">
      <div className="space-y-3">
        {ITEMS.map((item) => (
          <div key={item.title} className="flex gap-3 bg-gray-800/50 border border-gray-700 rounded-lg p-4">
            <span className="text-xl shrink-0">{item.icon}</span>
            <div>
              <div className="text-sm font-medium text-gray-200">{item.title}</div>
              <div className="text-xs text-gray-400 mt-0.5">{item.desc}</div>
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
        <span className="text-sm text-gray-300">위 내용을 이해했습니다</span>
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
