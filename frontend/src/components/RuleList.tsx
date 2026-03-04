import { TradingRule } from '../services/rules'

interface Props {
  rules: TradingRule[]
  onToggle: (id: number) => void
  onEdit: (rule: TradingRule) => void
  onDelete: (id: number) => void
}

export default function RuleList({ rules, onToggle, onEdit, onDelete }: Props) {
  if (rules.length === 0) {
    return <p className="text-gray-400 text-sm py-4 text-center">저장된 전략이 없습니다.</p>
  }

  return (
    <ul className="divide-y">
      {rules.map(rule => (
        <li key={rule.id} className="flex items-center gap-3 py-3">
          {/* ON/OFF 토글 */}
          <button
            onClick={() => onToggle(rule.id)}
            className={`w-10 h-5 rounded-full transition-colors ${
              rule.is_active ? 'bg-blue-500' : 'bg-gray-300'
            }`}
          >
            <span
              className={`block w-4 h-4 rounded-full bg-white shadow transition-transform mx-0.5 ${
                rule.is_active ? 'translate-x-5' : ''
              }`}
            />
          </button>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm truncate">{rule.name}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded ${
                rule.side === 'BUY' ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'
              }`}>
                {rule.side === 'BUY' ? '매수' : '매도'}
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {rule.stock_code} · {rule.quantity}주 ·{' '}
              {rule.conditions.map((c, i) => (
                <span key={i}>{c.variable} {c.operator} {c.value}{i < rule.conditions.length - 1 ? ' AND ' : ''}</span>
              ))}
            </div>
          </div>

          <button onClick={() => onEdit(rule)} className="text-sm text-blue-600 hover:underline">수정</button>
          <button onClick={() => onDelete(rule.id)} className="text-sm text-red-500 hover:underline">삭제</button>
        </li>
      ))}
    </ul>
  )
}
