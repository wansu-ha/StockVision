/**
 * OpsPanel — 운영 요약 패널
 * 4개 상태 (로컬/브로커/클라우드/엔진) + 오늘의 요약 + 경고 배너
 */
import { useQuery } from '@tanstack/react-query'
import { cloudHealth } from '../../services/cloudClient'
import { localLogs, localHealth } from '../../services/localClient'
import type { LogSummary } from '../../services/localClient'

interface OpsPanelProps {
  localConnected: boolean
  brokerConnected: boolean
  engineRunning: boolean
  isMock: boolean | null
}

interface StatusItem {
  label: string
  ok: boolean
  text: string
  color: string
}

export default function OpsPanel({ localConnected, brokerConnected, engineRunning, isMock }: OpsPanelProps) {
  // 클라우드 상태
  const { data: cloudOk } = useQuery({
    queryKey: ['cloudHealth'],
    queryFn: () => cloudHealth.check().then(Boolean),
    refetchInterval: 10_000,
    retry: false,
  })

  // 로컬 서버 상태 (버전 포함)
  const { data: localHp } = useQuery({
    queryKey: ['localHealth'],
    queryFn: () => localHealth.check(),
    refetchInterval: 10_000,
    retry: false,
  })

  // 오늘의 요약
  const { data: summary } = useQuery<LogSummary | null>({
    queryKey: ['logSummary'],
    queryFn: () => localLogs.summary(),
    enabled: localConnected,
    refetchInterval: 30_000,
    retry: false,
  })

  const isLocalUp = !!localHp || localConnected

  const statuses: StatusItem[] = [
    {
      label: '로컬',
      ok: isLocalUp,
      text: isLocalUp ? '연결됨' : '연결 불가',
      color: isLocalUp ? 'bg-green-400' : 'bg-red-400',
    },
    {
      label: '브로커',
      ok: brokerConnected,
      text: brokerConnected
        ? `연결${isMock !== null ? (isMock ? ' (모의)' : ' (실전)') : ''}`
        : '미연결',
      color: brokerConnected ? 'bg-green-400' : 'bg-yellow-400',
    },
    {
      label: '클라우드',
      ok: !!cloudOk,
      text: cloudOk ? '정상' : '연결 불가',
      color: cloudOk ? 'bg-green-400' : 'bg-red-400',
    },
    {
      label: '엔진',
      ok: engineRunning,
      text: engineRunning ? '실행 중' : '정지',
      color: engineRunning ? 'bg-green-400' : 'bg-gray-500',
    },
  ]

  // 경고 메시지
  const warnings: string[] = []
  if (!isLocalUp) warnings.push('로컬 서버 연결 불가 — 서버를 시작하세요')
  if (isLocalUp && !brokerConnected) warnings.push('브로커 미연결 — 설정에서 API 키를 확인하세요')
  if (!cloudOk) warnings.push('클라우드 연결 불가 — 네트워크를 확인하세요')
  if (isLocalUp && brokerConnected && !engineRunning) warnings.push('엔진 정지됨 — 전략 실행 버튼을 눌러 시작하세요')

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 sm:p-4 mb-4 sm:mb-5">
      {/* 상태 표시 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 sm:gap-5 flex-wrap">
          {statuses.map((s) => (
            <div key={s.label} className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${s.color} ${s.ok && s.label === '엔진' ? 'animate-pulse' : ''}`} />
              <span className="text-xs text-gray-400">{s.label}</span>
              <span className={`text-xs ${s.ok ? 'text-gray-300' : 'text-gray-500'}`}>{s.text}</span>
            </div>
          ))}
        </div>

        {/* 오늘의 요약 */}
        {summary && (
          <div className="flex items-center gap-3 text-xs text-gray-400 shrink-0">
            <span>신호 <span className="font-mono text-gray-300">{summary.signals}</span></span>
            <span>체결 <span className="font-mono text-gray-300">{summary.fills}</span></span>
            <span className={summary.errors > 0 ? 'text-red-400' : ''}>
              오류 <span className="font-mono">{summary.errors}</span>
            </span>
          </div>
        )}
      </div>

      {/* 경고 배너 */}
      {warnings.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-800/50">
          {warnings.map((w, i) => (
            <div key={i} className="flex items-center gap-1.5 text-xs text-yellow-400/80">
              <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
