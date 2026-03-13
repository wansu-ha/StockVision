/** 에러 로그 뷰어 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { adminApi } from '../../services/admin'

interface ErrorLog {
  id: number
  timestamp: string
  level: string
  message: string
  stack_trace?: string
}

export default function AdminErrorLogs() {
  const [level, setLevel] = useState<string>('')
  const [page, setPage] = useState(1)
  const [selectedLog, setSelectedLog] = useState<ErrorLog | null>(null)

  const { data: logs = [] } = useQuery<ErrorLog[]>({
    queryKey: ['admin', 'errors', level, page],
    queryFn: () =>
      adminApi.getErrors({ level: level || undefined, limit: 50, offset: (page - 1) * 50 })
        .then((r: { data: { data: ErrorLog[] } }) => r.data.data ?? r.data ?? []),
    refetchInterval: 10000,
  })

  const levelColors: Record<string, string> = {
    ERROR: 'bg-red-100 text-red-700',
    WARN: 'bg-yellow-100 text-yellow-700',
    INFO: 'bg-blue-100 text-blue-700',
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">에러 로그</h1>

      {/* 필터 */}
      <div className="flex gap-3 mb-4">
        {['', 'ERROR', 'WARN', 'INFO'].map((l) => (
          <button
            key={l}
            onClick={() => { setLevel(l); setPage(1) }}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium ${
              level === l ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-500'
            }`}
          >
            {l || '전체'}
          </button>
        ))}
      </div>

      {/* 테이블 */}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-gray-500">
            <th className="text-left py-2 px-3 w-40">시간</th>
            <th className="text-center py-2 px-3 w-20">레벨</th>
            <th className="text-left py-2 px-3">메시지</th>
          </tr>
        </thead>
        <tbody>
          {(Array.isArray(logs) ? logs : []).map((log) => (
            <tr
              key={log.id}
              className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
              onClick={() => setSelectedLog(log)}
            >
              <td className="py-2 px-3 text-gray-500 font-mono text-xs">
                {new Date(log.timestamp).toLocaleString('ko-KR')}
              </td>
              <td className="py-2 px-3 text-center">
                <span className={`text-xs px-2 py-0.5 rounded font-medium ${levelColors[log.level] ?? 'bg-gray-100'}`}>
                  {log.level}
                </span>
              </td>
              <td className="py-2 px-3 truncate max-w-md">{log.message}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="flex gap-2 mt-4">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} className="px-3 py-1 bg-gray-100 rounded text-sm">이전</button>
        <span className="px-3 py-1 text-sm text-gray-500">{page}</span>
        <button onClick={() => setPage((p) => p + 1)} className="px-3 py-1 bg-gray-100 rounded text-sm">다음</button>
      </div>

      {/* 상세 모달 */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30" onClick={() => setSelectedLog(null)} />
          <div className="relative bg-white rounded-2xl shadow-2xl p-6 max-w-lg w-full max-h-[80vh] overflow-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold">에러 상세</h3>
              <button onClick={() => setSelectedLog(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>
            <div className="space-y-3 text-sm">
              <div><span className="text-gray-500">시간:</span> {new Date(selectedLog.timestamp).toLocaleString('ko-KR')}</div>
              <div><span className="text-gray-500">레벨:</span> {selectedLog.level}</div>
              <div><span className="text-gray-500">메시지:</span> {selectedLog.message}</div>
              {selectedLog.stack_trace && (
                <div>
                  <span className="text-gray-500">스택 트레이스:</span>
                  <pre className="mt-1 bg-gray-50 p-3 rounded-lg text-xs overflow-x-auto">{selectedLog.stack_trace}</pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
