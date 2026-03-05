/** 로그 상세 패널 (사이드 패널) */
import type { ExecutionLog } from '../types/log'

interface Props {
  log: ExecutionLog | null
  onClose: () => void
}

export default function LogDetailPanel({ log, onClose }: Props) {
  if (!log) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* 배경 오버레이 */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      {/* 패널 */}
      <div className="relative w-96 bg-white h-full shadow-2xl overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold">실행 상세</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>

        <div className="space-y-4">
          <Field label="ID" value={String(log.id)} />
          <Field label="시간" value={new Date(log.timestamp).toLocaleString('ko-KR')} />
          <Field label="종목" value={log.symbol} />
          <Field label="방향" value={log.side === 'BUY' ? '매수' : '매도'} />
          <Field label="수량" value={`${log.qty}주`} />
          <Field label="가격" value={`${log.price.toLocaleString()}원`} />
          <Field label="상태" value={log.status} />
          {log.rule_id && <Field label="규칙 ID" value={String(log.rule_id)} />}
          {log.order_id && <Field label="주문 ID" value={log.order_id} />}
          {log.reason && <Field label="사유" value={log.reason} />}
        </div>
      </div>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-sm text-gray-900 font-medium">{value}</div>
    </div>
  )
}
