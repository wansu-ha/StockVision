/**
 * ExecutionTimeline — 실행 로그 타임라인 뷰
 * intent_id 기반 TimelineEntry를 카드로 표시한다.
 */
import { useState } from 'react'
import type { TimelineEntry } from '../../services/logs'

const STATE_DOT: Record<string, string> = {
  PROPOSED: 'bg-purple-400',
  SUBMITTED: 'bg-blue-400',
  FILLED: 'bg-green-400',
  BLOCKED: 'bg-yellow-400',
  FAILED: 'bg-red-400',
  CANCELLED: 'bg-gray-400',
}

const STATE_LABEL: Record<string, string> = {
  PROPOSED: '제안',
  SUBMITTED: '제출',
  FILLED: '체결',
  BLOCKED: '차단',
  FAILED: '실패',
  CANCELLED: '취소',
}

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ts
  }
}

function TimelineCard({ entry }: { entry: TimelineEntry }) {
  const [expanded, setExpanded] = useState(false)

  const borderMap: Record<string, string> = {
    FILLED: 'border-green-900/50',
    BLOCKED: 'border-yellow-900/50',
    FAILED: 'border-red-900/50',
  }
  const borderColor = borderMap[entry.state] || 'border-gray-800'

  const badgeMap: Record<string, string> = {
    FILLED: 'bg-green-900/50 text-green-400',
    BLOCKED: 'bg-yellow-900/50 text-yellow-400',
    FAILED: 'bg-red-900/50 text-red-400',
  }
  const badgeStyle = badgeMap[entry.state] || 'bg-gray-800 text-gray-400'

  // 슬리피지 계산
  const fillStep = entry.steps.find(s => s.state === 'FILLED')
  const fillPrice = fillStep?.meta?.fill_price as number | undefined
  const orderStep = entry.steps.find(s => s.state === 'SUBMITTED')
  const orderPrice = orderStep?.meta?.price as number | undefined
  const slippage = fillPrice && orderPrice && orderPrice > 0
    ? ((fillPrice - orderPrice) / orderPrice * 100).toFixed(2)
    : null

  return (
    <div className={`bg-gray-900 border ${borderColor} rounded-lg p-3 hover:border-gray-700 transition-colors`}>
      {/* 헤더 */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${STATE_DOT[entry.state] || 'bg-gray-400'}`} />
          <span className="font-mono text-sm text-gray-300">{entry.symbol}</span>
          <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
            entry.side === 'BUY' ? 'bg-blue-900/50 text-blue-400' : 'bg-red-900/50 text-red-400'
          }`}>
            {entry.side === 'BUY' ? '매수' : '매도'}
          </span>
          <span className={`text-xs px-1.5 py-0.5 rounded ${badgeStyle}`}>
            {STATE_LABEL[entry.state] || entry.state}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          {entry.duration_ms != null && <span>{entry.duration_ms}ms</span>}
          <span>{formatTime(entry.started_at)}</span>
          <span className="text-gray-600">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {/* 단계별 타임라인 */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-800/50">
          <div className="ml-1 border-l border-gray-800 pl-3 space-y-2">
            {entry.steps.map((step, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs">
                <div className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${STATE_DOT[step.state] || 'bg-gray-500'}`} />
                <span className="text-gray-600 shrink-0 w-16">{formatTime(step.ts)}</span>
                <span className="text-gray-500 shrink-0 w-12">{STATE_LABEL[step.state] || step.state}</span>
                <span className="text-gray-400 flex-1">{step.message}</span>
              </div>
            ))}
          </div>

          {/* 메타 정보 */}
          <div className="mt-3 flex gap-4 text-xs text-gray-500">
            <span>규칙 #{entry.rule_id}</span>
            {slippage && <span>슬리피지: {slippage}%</span>}
            {fillPrice && <span>체결가: {fillPrice.toLocaleString()}원</span>}
          </div>
        </div>
      )}
    </div>
  )
}

interface Props {
  items: TimelineEntry[]
  isLoading: boolean
  error: boolean
}

export default function ExecutionTimeline({ items, isLoading, error }: Props) {
  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">로딩 중...</div>
  }
  if (error) {
    return <div className="p-8 text-center text-red-500">로컬 서버 연결 실패</div>
  }
  if (items.length === 0) {
    return <div className="p-8 text-center text-gray-500">타임라인 기록이 없습니다.</div>
  }

  return (
    <div className="space-y-2">
      {items.map(entry => (
        <TimelineCard key={entry.intent_id} entry={entry} />
      ))}
    </div>
  )
}
