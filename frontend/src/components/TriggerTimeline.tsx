import type { TriggerEntry } from '../types/condition-status'

export default function TriggerTimeline({ history }: { history: TriggerEntry[] }) {
  const recent = history.slice(-5).reverse()
  if (!recent.length) return null

  return (
    <div className="px-3 py-2">
      <div className="text-xs font-semibold text-default-500 mb-1">최근 트리거</div>
      {recent.map((e, i) => (
        <div key={i} className="flex gap-2 text-xs text-default-400 py-0.5">
          <span className="font-mono w-12">{e.at.slice(11, 16)}</span>
          <span>{e.action}</span>
        </div>
      ))}
    </div>
  )
}
