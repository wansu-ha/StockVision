/**
 * ExecutionTimeline — 실행 로그 타임라인 뷰
 * cycle_id로 그룹핑하여 매매 사이클을 카드로 표시한다.
 */
import type { LogEntry } from '../../services/logs'

interface Props {
  logs: LogEntry[]
  isLoading: boolean
  error: boolean
}

interface CycleGroup {
  cycleId: string | null
  symbol: string | null
  side: string | null
  events: LogEntry[]
  finalStatus: string
  ts: string // 최신 이벤트 시각
}

const STATUS_DOT: Record<string, string> = {
  FILLED: 'bg-green-400',
  PARTIAL: 'bg-green-300',
  SUBMITTED: 'bg-blue-400',
  REJECTED: 'bg-red-400',
  FAILED: 'bg-red-400',
  SKIPPED: 'bg-gray-400',
}

const STATUS_LABEL: Record<string, string> = {
  FILLED: '체결',
  PARTIAL: '부분체결',
  SUBMITTED: '전송',
  REJECTED: '거부',
  FAILED: '오류',
  SKIPPED: '스킵',
}

function groupByCycle(logs: LogEntry[]): CycleGroup[] {
  const byId = new Map<string, LogEntry[]>()
  const orphans: LogEntry[] = []

  for (const log of logs) {
    const cycleId = log.meta?.cycle_id as string | undefined
    if (cycleId) {
      const arr = byId.get(cycleId) ?? []
      arr.push(log)
      byId.set(cycleId, arr)
    } else {
      orphans.push(log)
    }
  }

  const groups: CycleGroup[] = []

  // cycle_id가 있는 그룹
  for (const [cycleId, events] of byId) {
    const sorted = events.sort((a, b) => a.ts.localeCompare(b.ts))
    const last = sorted[sorted.length - 1]
    groups.push({
      cycleId,
      symbol: last.symbol,
      side: (last.meta?.side as string) ?? null,
      events: sorted,
      finalStatus: (last.meta?.status as string) ?? last.log_type,
      ts: last.ts,
    })
  }

  // cycle_id가 없는 개별 항목 (기존 로그 폴백)
  for (const log of orphans) {
    groups.push({
      cycleId: null,
      symbol: log.symbol,
      side: (log.meta?.side as string) ?? null,
      events: [log],
      finalStatus: (log.meta?.status as string) ?? log.log_type,
      ts: log.ts,
    })
  }

  // 최신순 정렬
  groups.sort((a, b) => b.ts.localeCompare(a.ts))
  return groups
}

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ts
  }
}

function CycleCard({ group }: { group: CycleGroup }) {
  const dotColor = STATUS_DOT[group.finalStatus] ?? 'bg-gray-400'
  const label = STATUS_LABEL[group.finalStatus] ?? group.finalStatus

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 hover:border-gray-700 transition-colors">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${dotColor}`} />
          <span className="font-mono text-sm text-gray-300">{group.symbol ?? '—'}</span>
          {group.side && (
            <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
              group.side === 'BUY' ? 'bg-blue-900/50 text-blue-400' : 'bg-red-900/50 text-red-400'
            }`}>
              {group.side === 'BUY' ? '매수' : '매도'}
            </span>
          )}
          <span className={`text-xs px-1.5 py-0.5 rounded ${
            group.finalStatus === 'FILLED' ? 'bg-green-900/50 text-green-400' :
            group.finalStatus === 'FAILED' || group.finalStatus === 'REJECTED' ? 'bg-red-900/50 text-red-400' :
            'bg-gray-800 text-gray-400'
          }`}>
            {label}
          </span>
        </div>
        <span className="text-xs text-gray-500">{formatTime(group.ts)}</span>
      </div>

      {/* 타임라인 이벤트 */}
      <div className="ml-1 border-l border-gray-800 pl-3 space-y-1">
        {group.events.map((evt) => (
          <div key={evt.id} className="flex items-start gap-2 text-xs">
            <span className="text-gray-600 shrink-0 w-16">{formatTime(evt.ts)}</span>
            <span className="text-gray-400">{evt.message}</span>
          </div>
        ))}
      </div>

      {/* 실현손익 표시 */}
      {group.events.some(e => e.meta?.realized_pnl) && (
        <div className="mt-2 pt-2 border-t border-gray-800/50 text-xs">
          {group.events
            .filter(e => e.meta?.realized_pnl)
            .map(e => {
              const pnl = Number(e.meta.realized_pnl)
              return (
                <span key={e.id} className={pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                  실현손익: {pnl >= 0 ? '+' : ''}{pnl.toLocaleString()}원
                </span>
              )
            })}
        </div>
      )}
    </div>
  )
}

export default function ExecutionTimeline({ logs, isLoading, error }: Props) {
  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">로딩 중...</div>
  }
  if (error) {
    return <div className="p-8 text-center text-red-500">로컬 서버 연결 실패</div>
  }

  const groups = groupByCycle(logs)

  if (groups.length === 0) {
    return <div className="p-8 text-center text-gray-500">실행 기록이 없습니다.</div>
  }

  return (
    <div className="space-y-2">
      {groups.map((g, i) => (
        <CycleCard key={g.cycleId ?? `orphan-${i}`} group={g} />
      ))}
    </div>
  )
}
