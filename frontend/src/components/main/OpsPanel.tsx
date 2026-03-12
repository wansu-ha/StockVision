/**
 * OpsPanel — 운영 요약 패널
 * 4개 상태 (로컬/브로커/클라우드/엔진) + 일일 P&L + 오늘의 요약 + 경고 배너
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { cloudHealth } from '../../services/cloudClient'
import { localLogs, localHealth, localStatus } from '../../services/localClient'
import type { LogSummary, DailyPnL } from '../../services/localClient'
import AlertsDropdown from '../AlertsDropdown'

interface OpsPanelProps {
  localConnected: boolean
  brokerConnected: boolean
  engineRunning: boolean
  isMock: boolean | null
  killSwitch?: boolean
  lossLock?: boolean
}

interface StatusItem {
  label: string
  ok: boolean
  text: string
  color: string
}

/** 금액 포맷 (1000 → +1,000원, -500 → -500원) */
function formatPnl(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toLocaleString('ko-KR')}원`
}

/** 상태 상세 팝오버 */
function StatusPopover({
  label,
  localHp,
  statusData,
  cloudOk,
}: {
  label: string
  localHp: { status: string; version: string } | null
  statusData: Record<string, unknown> | null
  cloudOk: boolean
}) {
  const broker = (statusData?.broker ?? {}) as Record<string, unknown>
  const engine = (statusData?.strategy_engine ?? {}) as Record<string, unknown>

  switch (label) {
    case '로컬':
      return (
        <div className="text-xs text-gray-300 space-y-1">
          <div>상태: {localHp?.status ?? 'N/A'}</div>
          <div>버전: {localHp?.version ?? 'N/A'}</div>
        </div>
      )
    case '브로커':
      return (
        <div className="text-xs text-gray-300 space-y-1">
          <div>증권사: {(broker.type as string) || 'N/A'}</div>
          <div>모드: {broker.is_mock ? '모의' : broker.connected ? '실전' : 'N/A'}</div>
        </div>
      )
    case '클라우드':
      return (
        <div className="text-xs text-gray-300 space-y-1">
          <div>상태: {cloudOk ? '정상' : '연결 불가'}</div>
        </div>
      )
    case '엔진':
      return (
        <div className="text-xs text-gray-300 space-y-1">
          <div>상태: {engine.running ? '실행 중' : '정지'}</div>
          <div>활성 규칙: {(engine.active_rules as number) ?? 'N/A'}</div>
        </div>
      )
    default:
      return null
  }
}

export default function OpsPanel({ localConnected, brokerConnected, engineRunning, isMock, killSwitch, lossLock }: OpsPanelProps) {
  const navigate = useNavigate()
  const [openPopover, setOpenPopover] = useState<string | null>(null)

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

  // 로컬 상태 상세 (브로커, 엔진 등)
  const { data: statusData } = useQuery({
    queryKey: ['localStatus'],
    queryFn: () => localStatus.get(),
    enabled: localConnected,
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

  // 일일 P&L (C1)
  const { data: dailyPnl } = useQuery<DailyPnL | null>({
    queryKey: ['dailyPnl'],
    queryFn: () => localLogs.dailyPnl(),
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

  // 경고 메시지 (C2: 복구 액션 포함)
  interface Warning {
    message: string
    action?: { label: string; onClick: () => void }
  }
  const warnings: Warning[] = []
  if (!isLocalUp) warnings.push({
    message: '로컬 서버 연결 불가 — 서버를 시작하세요',
    action: { label: '설정', onClick: () => navigate('/settings') },
  })
  if (isLocalUp && !brokerConnected) warnings.push({
    message: '브로커 미연결 — 설정에서 API 키를 확인하세요',
    action: { label: '설정', onClick: () => navigate('/settings') },
  })
  if (!cloudOk) warnings.push({
    message: '클라우드 연결 불가 — 네트워크를 확인하세요',
  })
  if (isLocalUp && brokerConnected && !engineRunning) warnings.push({
    message: '엔진 정지됨 — 전략 실행 버튼을 눌러 시작하세요',
  })

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 sm:p-4 mb-4 sm:mb-5">
      {/* 상태 + 요약 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 sm:gap-5 flex-wrap">
          {statuses.map((s) => (
            <div key={s.label} className="relative">
              <button
                onClick={() => setOpenPopover(openPopover === s.label ? null : s.label)}
                className="relative z-20 flex items-center gap-1.5 cursor-pointer hover:opacity-80 transition"
              >
                <div className={`w-2 h-2 rounded-full ${s.color} ${s.ok && s.label === '엔진' ? 'animate-pulse' : ''}`} />
                <span className="text-xs text-gray-400">{s.label}</span>
                <span className={`text-xs ${s.ok ? 'text-gray-300' : 'text-gray-500'}`}>{s.text}</span>
              </button>
              {/* C2: 상태 드롭다운 */}
              {openPopover === s.label && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setOpenPopover(null)} />
                  <div className="absolute top-full left-0 mt-1 z-20 bg-gray-800 border border-gray-700 rounded-lg p-3 shadow-lg min-w-[160px]">
                    <StatusPopover
                      label={s.label}
                      localHp={localHp ?? null}
                      statusData={statusData as Record<string, unknown> | null}
                      cloudOk={!!cloudOk}
                    />
                  </div>
                </>
              )}
            </div>
          ))}
        </div>

        {/* 오늘의 요약: P&L + 신호/체결/오류 + 경고 배지 */}
        <div className="flex items-center gap-3 text-xs text-gray-400 shrink-0">
          {/* C1: 일일 P&L */}
          {dailyPnl != null && (
            <span className={`font-medium ${
              dailyPnl.realized_pnl > 0 ? 'text-green-400' :
              dailyPnl.realized_pnl < 0 ? 'text-red-400' :
              'text-gray-400'
            }`}>
              오늘: {formatPnl(dailyPnl.realized_pnl)}
            </span>
          )}
          {summary && (
            <>
              <span>신호 <span className="font-mono text-gray-300">{summary.signals}</span></span>
              <span>체결 <span className="font-mono text-gray-300">{summary.fills}</span></span>
              <span className={summary.errors > 0 ? 'text-red-400' : ''}>
                오류 <span className="font-mono">{summary.errors}</span>
              </span>
            </>
          )}
          <AlertsDropdown />
        </div>
      </div>

      {/* 긴급 배너 — Kill Switch / 손실 락 */}
      {(killSwitch || lossLock) && (
        <div className="mt-2 pt-2 border-t border-red-800/50">
          {killSwitch && (
            <div className="flex items-center gap-1.5 text-xs text-red-400 font-medium">
              <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
              <span>Kill Switch 발동 — 신규 주문이 차단되었습니다</span>
            </div>
          )}
          {lossLock && (
            <div className="flex items-center gap-1.5 text-xs text-red-400 font-medium">
              <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
              <span>손실 한도 도달 — 자동 정지되었습니다</span>
            </div>
          )}
        </div>
      )}

      {/* 경고 배너 (C2: 복구 액션 버튼 포함) */}
      {warnings.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-800/50 space-y-1">
          {warnings.map((w, i) => (
            <div key={i} className="flex items-center justify-between gap-2 text-xs text-yellow-400/80">
              <div className="flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
                <span>{w.message}</span>
              </div>
              {w.action && (
                <button
                  onClick={w.action.onClick}
                  className="px-2 py-0.5 bg-yellow-900/30 hover:bg-yellow-900/50 rounded text-yellow-400 text-xs font-medium transition shrink-0"
                >
                  {w.action.label}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
