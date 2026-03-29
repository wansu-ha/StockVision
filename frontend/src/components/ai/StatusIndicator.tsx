/** AI SSE 단계 표시 */

const STEP_ICONS: Record<string, string> = {
  analyzing: '🔍',
  generating: '✍️',
  validating: '✅',
  retrying: '⟳',
}

interface Props {
  status: string
}

export default function StatusIndicator({ status }: Props) {
  if (!status) return null

  // status 메시지에서 step 추출 시도
  const step = Object.keys(STEP_ICONS).find(k => status.includes(k)) ?? ''
  const icon = STEP_ICONS[step] ?? '⏳'

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/50 rounded text-xs text-gray-400 animate-pulse">
      <span>{icon}</span>
      <span>{status}</span>
    </div>
  )
}
