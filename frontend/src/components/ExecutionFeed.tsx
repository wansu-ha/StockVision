/** 최근 체결 피드 */
import type { ExecutionEvent } from '../types/dashboard'

interface Props {
  events: ExecutionEvent[]
}

export default function ExecutionFeed({ events }: Props) {
  if (events.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8">
        체결 내역이 없습니다
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {events.slice(0, 10).map((ev, i) => (
        <div
          key={`${ev.timestamp}-${i}`}
          className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg"
        >
          <div className="flex items-center gap-3">
            <span className={`text-xs font-bold px-2 py-0.5 rounded ${ev.side.toUpperCase() === 'BUY' ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'}`}>
              {ev.side.toUpperCase() === 'BUY' ? '매수' : '매도'}
            </span>
            <span className="font-medium text-gray-900">{ev.symbol}</span>
            <span className="text-gray-500 text-sm">{ev.qty}주</span>
          </div>
          <div className="text-right">
            <div className="font-mono text-sm">{ev.price.toLocaleString()}원</div>
            <div className="text-xs text-gray-400">
              {new Date(ev.timestamp).toLocaleTimeString('ko-KR')}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
