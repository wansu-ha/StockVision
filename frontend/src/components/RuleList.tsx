import type { Rule } from '../types/strategy'
import { parseDirection } from '../types/strategy'
import type { LastRuleResult } from '../types/rule-result'

interface Props {
  rules: Rule[]
  namesMap?: Map<string, string>
  engineRunning?: boolean
  lastResults?: Map<number, LastRuleResult>
  onToggle: (rule: Rule) => void
  onEdit: (rule: Rule) => void
  onDelete: (id: number) => void
}

const DIRECTION_STYLE: Record<string, string> = {
  '매수': 'text-blue-400 bg-blue-900/30',
  '매도': 'text-red-400 bg-red-900/30',
  '양방향': 'text-purple-400 bg-purple-900/30',
}

const RESULT_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  SUCCESS: { bg: 'bg-green-100', text: 'text-green-600', label: '성공' },
  BLOCKED: { bg: 'bg-orange-100', text: 'text-orange-600', label: '차단' },
  FAILED: { bg: 'bg-red-100', text: 'text-red-600', label: '실패' },
}

export default function RuleList({ rules, namesMap, engineRunning, lastResults, onToggle, onEdit, onDelete }: Props) {
  if (rules.length === 0) {
    return <p className="text-gray-400 text-sm py-4 text-center">저장된 전략이 없습니다.</p>
  }

  return (
    <ul className="divide-y">
      {rules.map(rule => {
        const direction = parseDirection(rule)
        const isRunning = engineRunning && rule.is_active
        const symbolName = namesMap?.get(rule.symbol)
        const result = lastResults?.get(rule.id)
        const badge = result ? RESULT_BADGE[result.status] : null

        return (
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
                  {symbolName ? `${symbolName} ${rule.symbol}` : rule.symbol}
                </span>
                {rule.priority > 0 && (
                  <span className="text-xs text-gray-400">P{rule.priority}</span>
                )}
                {direction !== '없음' && (
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${DIRECTION_STYLE[direction]}`}>
                    {direction}
                  </span>
                )}
                {isRunning ? (
                  <span className="flex items-center gap-1 text-xs text-green-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" />
                    실행 중
                  </span>
                ) : (
                  <span className="text-xs text-gray-500">OFF</span>
                )}
                {badge && (
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${badge.bg} ${badge.text}`}>
                    {badge.label}
                  </span>
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
        )
      })}
    </ul>
  )
}
