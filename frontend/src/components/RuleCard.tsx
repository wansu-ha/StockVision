/** 규칙 카드 (전략 목록에서 사용) */
import type { Rule } from '../types/strategy'

interface Props {
  rule: Rule
  onToggle: (id: number, enabled: boolean) => void
  onEdit: (id: number) => void
  onDelete: (id: number) => void
}

export default function RuleCard({ rule, onToggle, onEdit, onDelete }: Props) {
  const conditionSummary = rule.conditions.length > 0
    ? `${rule.conditions.length}개 조건 (${rule.operator})`
    : '조건 없음'

  return (
    <div className={`bg-white rounded-xl border p-4 transition-colors ${rule.is_active ? 'border-green-200' : 'border-gray-200'}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{rule.name}</h3>
          <p className="text-sm text-gray-500">{rule.symbol} / {rule.side === 'BUY' ? '매수' : '매도'}</p>
        </div>
        {/* ON/OFF 토글 */}
        <button
          onClick={() => onToggle(rule.id, !rule.is_active)}
          className={`relative w-10 h-5 rounded-full transition-colors ${rule.is_active ? 'bg-green-400' : 'bg-gray-300'}`}
        >
          <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${rule.is_active ? 'translate-x-5' : 'translate-x-0.5'}`} />
        </button>
      </div>

      <div className="text-xs text-gray-500 mb-3">{conditionSummary}</div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => onEdit(rule.id)}
          className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
        >
          수정
        </button>
        <button
          onClick={() => onDelete(rule.id)}
          className="text-xs text-red-500 hover:text-red-700 font-medium"
        >
          삭제
        </button>
      </div>
    </div>
  )
}
