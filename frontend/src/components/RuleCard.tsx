/** 규칙 카드 (전략 목록에서 사용) */
import type { Rule } from '../types/strategy'
import { parseDirection } from '../types/strategy'

interface Props {
  rule: Rule
  symbolName?: string
  engineRunning?: boolean
  onToggle: (id: number, enabled: boolean) => void
  onEdit: (id: number) => void
  onDelete: (id: number) => void
}

const DIRECTION_STYLE: Record<string, string> = {
  '매수': 'text-blue-400 bg-blue-900/30',
  '매도': 'text-red-400 bg-red-900/30',
  '양방향': 'text-purple-400 bg-purple-900/30',
}

export default function RuleCard({ rule, symbolName, engineRunning, onToggle, onEdit, onDelete }: Props) {
  const summary = rule.script
    ? rule.script.split('\n').filter(l => l.trim() && !l.trim().startsWith('--')).join(' | ')
    : rule.buy_conditions ? '매수 조건 (JSON)' : rule.sell_conditions ? '매도 조건 (JSON)' : '조건 없음'

  const direction = parseDirection(rule)
  const isRunning = engineRunning && rule.is_active

  return (
    <div className={`bg-white rounded-xl border p-4 transition-colors ${rule.is_active ? 'border-green-200' : 'border-gray-200'}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{rule.name}</h3>
          <p className="text-sm text-gray-500">
            {symbolName ? `${symbolName} ${rule.symbol}` : rule.symbol}
          </p>
          <div className="flex items-center gap-2 mt-1">
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
          </div>
        </div>
        {/* ON/OFF 토글 */}
        <button
          onClick={() => onToggle(rule.id, !rule.is_active)}
          className={`relative w-10 h-5 rounded-full transition-colors ${rule.is_active ? 'bg-green-400' : 'bg-gray-300'}`}
        >
          <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${rule.is_active ? 'translate-x-5' : 'translate-x-0.5'}`} />
        </button>
      </div>

      <div className="text-xs text-gray-500 mb-3 truncate">{summary}</div>

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
