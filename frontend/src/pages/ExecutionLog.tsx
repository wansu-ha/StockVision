import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { logsApi } from '../services/logs'
import type { ExecutionLog as ExecutionLogEntry } from '../services/logs'

const STATUS_STYLE: Record<string, string> = {
  FILLED:  'bg-green-100 text-green-800',
  SENT:    'bg-blue-100 text-blue-800',
  SKIPPED: 'bg-gray-100 text-gray-600',
  FAILED:  'bg-red-100 text-red-800',
}

const STATUS_LABEL: Record<string, string> = {
  FILLED:  '체결',
  SENT:    '전송',
  SKIPPED: '스킵',
  FAILED:  '오류',
}

function SnapshotToggle({ snapshot }: { snapshot: string | null }) {
  const [open, setOpen] = useState(false)
  if (!snapshot) return null
  let parsed: Record<string, unknown> = {}
  try { parsed = JSON.parse(snapshot) } catch { return null }
  return (
    <div className="mt-1">
      <button
        onClick={() => setOpen(o => !o)}
        className="text-xs text-blue-600 hover:underline"
      >
        {open ? '조건 스냅샷 접기' : '조건 스냅샷 보기'}
      </button>
      {open && (
        <div className="mt-1 p-2 bg-gray-50 rounded text-xs text-gray-700 font-mono">
          {Object.entries(parsed).map(([k, v]) => (
            <span key={k} className="mr-3">{k}={String(v)}</span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function ExecutionLog() {
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo,   setDateTo]   = useState('')

  const { data, isLoading, error } = useQuery({
    queryKey: ['execution-logs', dateFrom, dateTo],
    queryFn: () => logsApi.getLogs({
      date_from: dateFrom || undefined,
      date_to:   dateTo   || undefined,
    }),
    refetchInterval: 10_000,
  })

  const { data: summary } = useQuery({
    queryKey: ['log-summary'],
    queryFn:  logsApi.getSummary,
    refetchInterval: 10_000,
  })

  const logs: ExecutionLogEntry[] = data?.data ?? []
  const sum = summary?.data

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">실행 로그</h1>

      {/* 요약 */}
      {sum && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-xl shadow p-4 text-center">
            <div className="text-2xl font-bold">{sum.total}</div>
            <div className="text-sm text-gray-500 mt-1">오늘 실행</div>
          </div>
          <div className="bg-white rounded-xl shadow p-4 text-center">
            <div className="text-2xl font-bold text-green-600">{sum.filled}</div>
            <div className="text-sm text-gray-500 mt-1">체결</div>
          </div>
          <div className="bg-white rounded-xl shadow p-4 text-center">
            <div className="text-2xl font-bold text-red-600">{sum.failed}</div>
            <div className="text-sm text-gray-500 mt-1">오류</div>
          </div>
        </div>
      )}

      {/* 필터 */}
      <div className="flex gap-3 mb-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">시작일</label>
          <input
            type="date"
            value={dateFrom}
            onChange={e => setDateFrom(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">종료일</label>
          <input
            type="date"
            value={dateTo}
            onChange={e => setDateTo(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          />
        </div>
        {(dateFrom || dateTo) && (
          <button
            onClick={() => { setDateFrom(''); setDateTo('') }}
            className="self-end text-sm text-gray-500 hover:text-gray-700"
          >
            초기화
          </button>
        )}
      </div>

      {/* 테이블 */}
      <div className="bg-white rounded-xl shadow overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">로딩 중...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">로컬 서버 연결 실패</div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-gray-400">실행 기록이 없습니다.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                {['시각', '규칙명', '종목', '수량', '상태', '체결가'].map(h => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-gray-600">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {logs.map(log => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {new Date(log.created_at + 'Z').toLocaleTimeString('ko-KR')}
                  </td>
                  <td className="px-4 py-3">
                    <div>{log.rule_name}</div>
                    <SnapshotToggle snapshot={log.condition_snapshot} />
                  </td>
                  <td className="px-4 py-3 font-mono">{log.symbol}</td>
                  <td className="px-4 py-3">
                    <span className={log.side === 'BUY' ? 'text-blue-600' : 'text-red-600'}>
                      {log.side === 'BUY' ? '매수' : '매도'}
                    </span>{' '}
                    {log.quantity}주
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLE[log.status] ?? ''}`}>
                      {STATUS_LABEL[log.status] ?? log.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {log.filled_price ? log.filled_price.toLocaleString() + '원' : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
