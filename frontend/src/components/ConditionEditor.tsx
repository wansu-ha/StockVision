/** 조건 편집기 (AND/OR, 지표 드롭다운, 추가/삭제) */
import type { Condition } from '../types/strategy'
import { AVAILABLE_INDICATORS, CONTEXT_FIELDS } from '../types/strategy'

interface Props {
  conditions: Condition[]
  operator: 'AND' | 'OR'
  onChange: (conditions: Condition[]) => void
  onOperatorChange: (op: 'AND' | 'OR') => void
}

const OPERATORS = ['>', '>=', '<', '<=', '==', '!='] as const

function emptyCondition(): Condition {
  return { type: 'indicator', field: 'rsi_14', operator: '>', value: 0 }
}

export default function ConditionEditor({ conditions, operator, onChange, onOperatorChange }: Props) {
  const update = (idx: number, patch: Partial<Condition>) => {
    const next = conditions.map((c, i) => (i === idx ? { ...c, ...patch } : c))
    onChange(next)
  }

  const add = () => onChange([...conditions, emptyCondition()])
  const remove = (idx: number) => onChange(conditions.filter((_, i) => i !== idx))

  return (
    <div className="space-y-3">
      {/* AND/OR 토글 */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-600">논리:</span>
        {(['AND', 'OR'] as const).map((op) => (
          <button
            key={op}
            type="button"
            onClick={() => onOperatorChange(op)}
            className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${
              operator === op
                ? 'bg-indigo-100 text-indigo-700'
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
          >
            {op}
          </button>
        ))}
      </div>

      {/* 조건 행 */}
      {conditions.map((cond, i) => {
        const fields = cond.type === 'context' ? CONTEXT_FIELDS : AVAILABLE_INDICATORS
        return (
        <div key={i} className="flex items-center gap-2 bg-gray-50 p-2 rounded-lg">
          {/* 타입 */}
          <select
            value={cond.type}
            onChange={(e) => {
              const newType = e.target.value as Condition['type']
              const defaultField = newType === 'context' ? CONTEXT_FIELDS[0].key : AVAILABLE_INDICATORS[0].key
              update(i, { type: newType, field: defaultField })
            }}
            className="w-24 px-2 py-1.5 border border-gray-200 rounded-lg text-sm"
          >
            <option value="indicator">지표</option>
            <option value="price">가격</option>
            <option value="volume">거래량</option>
            <option value="context">컨텍스트</option>
          </select>

          {/* 필드 */}
          <select
            value={cond.field}
            onChange={(e) => update(i, { field: e.target.value })}
            className="flex-1 px-2 py-1.5 border border-gray-200 rounded-lg text-sm"
          >
            {fields.map((ind) => (
              <option key={ind.key} value={ind.key}>{ind.name}</option>
            ))}
          </select>

          {/* 연산자 */}
          <select
            value={cond.operator}
            onChange={(e) => update(i, { operator: e.target.value as Condition['operator'] })}
            className="w-16 px-2 py-1.5 border border-gray-200 rounded-lg text-sm text-center"
          >
            {OPERATORS.map((op) => (
              <option key={op} value={op}>{op}</option>
            ))}
          </select>

          {/* 값 */}
          <input
            type="number"
            value={cond.value}
            onChange={(e) => update(i, { value: parseFloat(e.target.value) || 0 })}
            className="w-24 px-2 py-1.5 border border-gray-200 rounded-lg text-sm text-right"
          />

          {/* 삭제 */}
          <button
            type="button"
            onClick={() => remove(i)}
            className="text-gray-400 hover:text-red-500 transition-colors px-1"
          >
            &times;
          </button>
        </div>
        )
      })}

      <button
        type="button"
        onClick={add}
        className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
      >
        + 조건 추가
      </button>
    </div>
  )
}
