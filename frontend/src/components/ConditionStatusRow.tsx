import type { ConditionDetail } from '../types/condition-status'

export default function ConditionStatusRow({ condition }: { condition: ConditionDetail }) {
  const entries = Object.entries(condition.details)
  const detailStr = entries
    .map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toLocaleString() : v}`)
    .join('  ')

  return (
    <div className="flex items-center justify-between px-3 py-2 border-b border-default-100 last:border-b-0">
      <div className="flex-1 min-w-0">
        <div className="text-sm font-mono truncate">{condition.expr}</div>
        {detailStr && <div className="text-xs text-default-400 truncate">{detailStr}</div>}
      </div>
      <div className={`ml-2 text-lg flex-shrink-0 ${condition.result ? 'text-success' : 'text-default-300'}`}>
        {condition.result ? '●' : '○'}
      </div>
    </div>
  )
}
