import type { Rule } from '../types/strategy'

interface Props {
  rules: Rule[]
  onToggle: (rule: Rule) => void
  onEdit: (rule: Rule) => void
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
            onClick={() => onToggle(rule)}
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
              <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">
                {rule.symbol}
              </span>
              {rule.priority > 0 && (
                <span className="text-xs text-gray-400">P{rule.priority}</span>
              )}
            </div>
            <div className="text-xs text-gray-500 mt-0.5 truncate">
              {rule.script
                ? rule.script.split('\n').filter(l => l.trim() && !l.trim().startsWith('--')).join(' | ')
                : '(JSON 조건)'
              }
            </div>
          </div>

          <button onClick={() => onEdit(rule)} className="text-sm text-blue-600 hover:underline">수정</button>
          <button onClick={() => onDelete(rule.id)} className="text-sm text-red-500 hover:underline">삭제</button>
        </li>
      ))}
    </ul>
  )
}
