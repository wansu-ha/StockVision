import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { logsApi } from '../services/logs'
import type { LogEntry, TimelineEntry } from '../services/logs'
import ExecutionTimeline from '../components/main/ExecutionTimeline'

const LOG_TYPE_STYLE: Record<string, string> = {
  FILL:     'bg-green-900/50 text-green-400',
  ORDER:    'bg-blue-900/50 text-blue-400',
  STRATEGY: 'bg-purple-900/50 text-purple-400',
  ERROR:    'bg-red-900/50 text-red-400',
  SYSTEM:   'bg-gray-800 text-gray-400',
  ALERT:    'bg-yellow-900/50 text-yellow-400',
}

const LOG_TYPE_LABEL: Record<string, string> = {
  FILL:     '체결',
  ORDER:    '주문',
  STRATEGY: '전략',
  ERROR:    '오류',
  SYSTEM:   '시스템',
  ALERT:    '경고',
}

function MetaToggle({ meta }: { meta: Record<string, unknown> }) {
  const [open, setOpen] = useState(false)
  const keys = Object.keys(meta)
  if (keys.length === 0) return null
  return (
    <div className="mt-1">
      <button
        onClick={() => setOpen(o => !o)}
        className="text-xs text-blue-400 hover:underline"
      >
        {open ? '상세 접기' : '상세 보기'}
      </button>
      {open && (
        <div className="mt-1 p-2 bg-gray-800 rounded text-xs text-gray-400 font-mono">
          {keys.map(k => (
            <span key={k} className="mr-3">{k}={String(meta[k])}</span>
          ))}
        </div>
      )}
    </div>
  )
}

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString('ko-KR')
  } catch {
    return ts
  }
}

export default function ExecutionLog() {
  const [searchParams] = useSearchParams()
  const [dateFrom, setDateFrom] = useState('')
  const initialTab = searchParams.get('tab')
  const [viewMode, setViewMode] = useState<'table' | 'timeline' | 'alerts'>(
    initialTab === 'alerts' ? 'alerts' : initialTab === 'timeline' ? 'timeline' : 'table'
  )
  const [stateFilter, setStateFilter] = useState<string | undefined>()

  const { data, isLoading, error } = useQuery({
    queryKey: ['execution-logs', dateFrom],
    queryFn: () => logsApi.getLogs({
      date_from: dateFrom || undefined,
      limit: 200,
    }),
    refetchInterval: 10_000,
  })

  const { data: summary } = useQuery({
    queryKey: ['log-summary'],
    queryFn: () => logsApi.getSummary(),
    refetchInterval: 10_000,
  })

  // 타임라인 데이터 (별도 쿼리)
  const today = new Date().toISOString().split('T')[0]
  const { data: timelineData, isLoading: timelineLoading, error: timelineError } = useQuery({
    queryKey: ['execution-timeline', dateFrom || today, stateFilter],
    queryFn: () => logsApi.getTimeline({
      date_from: dateFrom || today,
      limit: 50,
      state: stateFilter,
    }),
    enabled: viewMode === 'timeline',
    refetchInterval: 10_000,
  })

  // 경고 탭 데이터
  const { data: alertsData, isLoading: alertsLoading } = useQuery({
    queryKey: ['alert-logs', dateFrom],
    queryFn: () => logsApi.getLogs({ log_type: 'ALERT', date_from: dateFrom || undefined, limit: 200 }),
    enabled: viewMode === 'alerts',
    refetchInterval: 10_000,
  })

  const logs: LogEntry[] = data?.data?.items ?? []
  const timeline: TimelineEntry[] = timelineData?.data?.items ?? []
  const alertLogs: LogEntry[] = alertsData?.data?.items ?? []
  const sum = summary?.data

  return (
    <div className="max-w-5xl mx-auto p-4 sm:p-6">
      <h1 className="text-xl font-bold text-gray-100 mb-4">실행 로그</h1>

      {/* 요약 */}
      {sum && (
        <div className="grid grid-cols-4 gap-3 mb-5">
          {[
            { label: '신호', value: sum.signals, color: 'text-purple-400' },
            { label: '체결', value: sum.fills, color: 'text-green-400' },
            { label: '주문', value: sum.orders, color: 'text-blue-400' },
            { label: '오류', value: sum.errors, color: sum.errors > 0 ? 'text-red-400' : 'text-gray-500' },
          ].map(s => (
            <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center">
              <div className={`text-xl font-bold ${s.color}`}>{s.value}</div>
              <div className="text-xs text-gray-500 mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* 필터 + 뷰 토글 */}
      <div className="flex items-end justify-between gap-3 mb-4">
        <div className="flex gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">시작일</label>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm text-gray-300"
            />
          </div>
          {dateFrom && (
            <button
              onClick={() => setDateFrom('')}
              className="self-end text-sm text-gray-500 hover:text-gray-300"
            >
              초기화
            </button>
          )}
          {/* 타임라인 전용 필터 */}
          {viewMode === 'timeline' && (
            <div>
              <label className="block text-xs text-gray-500 mb-1">상태</label>
              <select
                value={stateFilter || ''}
                onChange={e => setStateFilter(e.target.value || undefined)}
                className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm text-gray-300"
              >
                <option value="">전체</option>
                <option value="FILLED">체결</option>
                <option value="BLOCKED">차단</option>
                <option value="FAILED">실패</option>
              </select>
            </div>
          )}
        </div>

        {/* 뷰 토글 */}
        <div className="flex bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
          <button
            onClick={() => setViewMode('table')}
            className={`px-3 py-1.5 text-xs ${viewMode === 'table' ? 'bg-gray-700 text-gray-200' : 'text-gray-500 hover:text-gray-300'}`}
          >
            테이블
          </button>
          <button
            onClick={() => setViewMode('timeline')}
            className={`px-3 py-1.5 text-xs ${viewMode === 'timeline' ? 'bg-gray-700 text-gray-200' : 'text-gray-500 hover:text-gray-300'}`}
          >
            타임라인
          </button>
          <button
            onClick={() => setViewMode('alerts')}
            className={`px-3 py-1.5 text-xs ${viewMode === 'alerts' ? 'bg-gray-700 text-yellow-400' : 'text-gray-500 hover:text-gray-300'}`}
          >
            경고
          </button>
        </div>
      </div>

      {/* 뷰 */}
      {viewMode === 'timeline' ? (
        <ExecutionTimeline items={timeline} isLoading={timelineLoading} error={!!timelineError} />
      ) : viewMode === 'alerts' ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          {alertsLoading ? (
            <div className="p-8 text-center text-gray-500">로딩 중...</div>
          ) : alertLogs.length === 0 ? (
            <div className="p-8 text-center text-gray-500">경고 기록이 없습니다.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-800">
                <tr>
                  {['시각', '심각도', '종목', '메시지'].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {alertLogs.map(log => {
                  const severity = (log.meta as Record<string, unknown>)?.severity as string | undefined
                  return (
                    <tr key={log.id} className="hover:bg-gray-800/30">
                      <td className="px-4 py-3 text-gray-500 whitespace-nowrap text-xs">{formatTime(log.ts)}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium
                          ${severity === 'critical' ? 'bg-red-900/50 text-red-400' : 'bg-yellow-900/50 text-yellow-400'}`}>
                          {severity === 'critical' ? '심각' : '경고'}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-gray-400 text-xs">{log.symbol ?? '—'}</td>
                      <td className="px-4 py-3 text-gray-300 text-xs">
                        <div>{log.message}</div>
                        <MetaToggle meta={log.meta} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">로딩 중...</div>
          ) : error ? (
            <div className="p-8 text-center text-red-500">로컬 서버 연결 실패</div>
          ) : logs.length === 0 ? (
            <div className="p-8 text-center text-gray-500">실행 기록이 없습니다.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-gray-800">
                <tr>
                  {['시각', '유형', '종목', '메시지'].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-medium text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {logs.map(log => (
                  <tr key={log.id} className="hover:bg-gray-800/30">
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap text-xs">
                      {formatTime(log.ts)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${LOG_TYPE_STYLE[log.log_type] ?? 'bg-gray-800 text-gray-400'}`}>
                        {LOG_TYPE_LABEL[log.log_type] ?? log.log_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-400 text-xs">{log.symbol ?? '—'}</td>
                    <td className="px-4 py-3 text-gray-300 text-xs">
                      <div>{log.message}</div>
                      <MetaToggle meta={log.meta} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
