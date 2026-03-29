/** AI 크레딧 잔량 바 */
import { useCredit } from '../../hooks/useCredit'

export default function CreditBar() {
  const { data: credit, isLoading } = useCredit()

  if (isLoading || !credit) return null
  if (credit.has_byo_key) {
    return (
      <div className="px-3 py-1.5 text-xs text-gray-500">
        자체 API 키 사용 중
      </div>
    )
  }

  const pct = credit.remaining_percent
  const barColor = pct > 50 ? 'bg-green-500' : pct > 20 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="px-3 py-2 border-t border-gray-700">
      <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
        <span>AI 크레딧</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-[10px] text-gray-500 mt-1">
        약 {credit.estimate_turns}회 대화 가능 · 매일 자정 초기화
      </p>
    </div>
  )
}
