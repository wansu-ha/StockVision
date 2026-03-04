import { Condition, Variable } from '../services/rules'

function isMet(current: number, op: string, value: number): boolean {
  switch (op) {
    case '>':  return current > value
    case '<':  return current < value
    case '>=': return current >= value
    case '<=': return current <= value
    case '==': return current === value
    default:   return false
  }
}

interface Props {
  condition: Condition
  variables: Variable[]
  operators: string[]
  onChange: (c: Condition) => void
  onDelete: () => void
}

export default function ConditionRow({ condition, variables, operators, onChange, onDelete }: Props) {
  const current = variables.find(v => v.key === condition.variable)?.current

  return (
    <div className="flex items-center gap-2">
      <select
        value={condition.variable}
        onChange={e => onChange({ ...condition, variable: e.target.value })}
        className="border rounded px-2 py-1 text-sm flex-1"
      >
        <option value="">변수 선택</option>
        {variables.map(v => (
          <option key={v.key} value={v.key}>{v.label}</option>
        ))}
      </select>

      <select
        value={condition.operator}
        onChange={e => onChange({ ...condition, operator: e.target.value as Condition['operator'] })}
        className="border rounded px-2 py-1 text-sm w-16"
      >
        {operators.map(op => <option key={op} value={op}>{op}</option>)}
      </select>

      <input
        type="number"
        value={condition.value}
        onChange={e => onChange({ ...condition, value: Number(e.target.value) })}
        className="border rounded px-2 py-1 text-sm w-28"
      />

      {current !== null && current !== undefined && (
        <span className={`text-xs px-2 py-0.5 rounded ${
          isMet(current, condition.operator, condition.value)
            ? 'bg-green-100 text-green-700'
            : 'bg-gray-100 text-gray-500'
        }`}>
          현재 {typeof current === 'number' ? current.toFixed(1) : current}
        </span>
      )}

      <button
        onClick={onDelete}
        className="text-red-400 hover:text-red-600 text-sm px-1"
      >
        삭제
      </button>
    </div>
  )
}
