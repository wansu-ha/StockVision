/**
 * MainDashboard — 메인 화면 오케스트레이터
 * 훅 → Header/ListView/DetailView 조합
 * (E) 뷰 전환 fade+translateY 애니메이션
 */
import { useState, useMemo } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Header from '../components/main/Header'
import OpsPanel from '../components/main/OpsPanel'
import BriefingCard from '../components/BriefingCard'
import KillSwitchFAB from '../components/KillSwitchFAB'
import ArmDialog from '../components/ArmDialog'
import { useOnboarding } from '../hooks/useOnboarding'
import ListView from '../components/main/ListView'
import DetailView from '../components/main/DetailView'
import { useAuth } from '../context/AuthContext'
import { useStockData } from '../hooks/useStockData'
import { useWatchlistToggle } from '../hooks/useWatchlistToggle'
import { useAccountStatus } from '../hooks/useAccountStatus'
import { useAccountBalance } from '../hooks/useAccountBalance'
import { useMarketContext } from '../hooks/useMarketContext'
import { useRemoteMode } from '../hooks/useRemoteMode'
import { useRemoteControl } from '../hooks/useRemoteControl'
import { localLogs, localEngine, localAccount } from '../services/localClient'
import { useConsentStatus } from '../hooks/useConsentStatus'
import DisclaimerModal from '../components/DisclaimerModal'
import type { Stock, AccountInfo, Trade, PendingOrder, MarketStatus } from '../components/main/ListView'

export default function MainDashboard() {
  const { completed: onboardingDone } = useOnboarding()
  const [view, setView] = useState<'list' | 'detail'>('list')
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null)
  const [tab, setTab] = useState<'my' | 'watch'>('my')
  const [strategyLoading, setStrategyLoading] = useState(false)
  const [showArmDialog, setShowArmDialog] = useState(false)
  const [showDisclaimer, setShowDisclaimer] = useState(false)

  const queryClient = useQueryClient()
  const { localReady } = useAuth()
  const { myStocks, watchStocks, watchlistSet, rules } = useStockData()
  const { mutate: toggleWatchlist } = useWatchlistToggle()
  const { engineRunning, brokerConnected, credentials, isMock, killSwitch, lossLock } = useAccountStatus()
  const { balance, openOrders } = useAccountBalance(brokerConnected)
  const { context } = useMarketContext()
  const { data: consentStatus } = useConsentStatus()

  // 원격 모드 감지
  const { isRemote } = useRemoteMode()
  const { state: remoteState, connected: remoteConnected, sendKill, sendArm } = useRemoteControl(isRemote)

  // 원격 모드일 때 remoteState 기반 값 오버라이드
  const effectiveEngine = isRemote ? (remoteState?.engine_state === 'running' || remoteState?.engine_state === 'armed') : engineRunning
  const effectiveBroker = isRemote ? (remoteState?.broker_connected ?? false) : brokerConnected
  const effectiveKill = isRemote ? (remoteState?.kill_switch ?? false) : killSwitch
  const effectiveLoss = isRemote ? (remoteState?.loss_lock ?? false) : lossLock

  // 체결 로그 (fill 타입만) — localSecret 준비 후 실행
  const { data: logData } = useQuery({
    queryKey: ['fillLogs'],
    queryFn: () => localLogs.get({ log_type: 'fill', limit: 50 } as never),
    enabled: localReady,
    refetchInterval: 15_000,
    staleTime: 10_000,
    retry: 1,
  })

  // 일일 P&L (C1)
  const { data: dailyPnl } = useQuery({
    queryKey: ['dailyPnl'],
    queryFn: () => localLogs.dailyPnl(),
    enabled: localReady,
    refetchInterval: 30_000,
    staleTime: 15_000,
    retry: false,
  })

  const stocks = tab === 'my' ? myStocks : watchStocks

  // 증권사 이름 — 등록된 키 기반
  const brokerName = credentials?.kiwoom?.app_key ? '키움증권'
    : credentials?.kis?.app_key ? '한국투자증권'
    : '미등록'

  // 계좌 정보
  const account: AccountInfo = useMemo(() => {
    return {
      broker: brokerName,
      accountNo: brokerConnected ? '연결됨' : '미연결',
      totalValue: balance?.total_eval ?? 0,
      availableCash: balance?.cash ?? 0,
      dailyReturn: (dailyPnl?.realized_pnl && balance?.total_eval)
        ? Math.round((dailyPnl.realized_pnl / balance.total_eval) * 10000) / 100
        : 0,
      dailyPnl: dailyPnl?.realized_pnl ?? 0,
      holdings: balance?.positions.map(p => ({
        symbol: p.symbol,
        name: p.symbol,
        qty: p.qty,
        avgPrice: p.avg_price,
        currentPrice: p.current_price,
      })) ?? [],
    }
  }, [balance, brokerName, brokerConnected, dailyPnl])

  // 체결 내역 변환
  const trades: Trade[] = useMemo(() => {
    const raw = logData as { items?: Record<string, unknown>[] } | Record<string, unknown>[] | undefined
    const items = Array.isArray(raw) ? raw : (raw?.items ?? [])
    return items
      .filter((l): l is Record<string, unknown> & { symbol: string; meta: Record<string, unknown> } =>
        typeof l.symbol === 'string' && !!l.meta)
      .map(l => ({
        time: typeof l.ts === 'string' ? l.ts.slice(11, 19) : '',
        symbol: l.symbol,
        side: ((l.meta as Record<string, unknown>).side === 'BUY' ? '매수' : '매도') as '매수' | '매도',
        qty: Number((l.meta as Record<string, unknown>).qty) || 0,
        price: 0,
        ok: (l.meta as Record<string, unknown>).status === 'FILLED',
      }))
  }, [logData])

  // 미체결 주문 변환
  const pendingOrders: PendingOrder[] = useMemo(() => {
    return openOrders.map(o => ({
      time: o.created_at?.slice(11, 19) ?? '',
      symbol: o.symbol,
      side: (o.side === 'BUY' ? '매수' : '매도') as '매수' | '매도',
      qty: o.qty - o.filled_qty,
      price: o.limit_price ?? 0,
      type: o.order_type === 'LIMIT' ? '지정가' : '시장가',
      orderId: o.order_id,
    }))
  }, [openOrders])

  // 장 상태 — 주말/공휴일 + 시간 기반 추정
  const now = new Date()
  const dayOfWeek = now.getDay()
  const isWeekend = dayOfWeek === 0 || dayOfWeek === 6
  const isHoliday = isWeekend || context?.is_holiday === true
  const hhmm = now.getHours() * 100 + now.getMinutes()
  const marketStatus: MarketStatus = {
    status: isHoliday ? '휴장' : hhmm >= 900 && hhmm < 1530 ? '장중' : hhmm < 900 ? '장전' : '장후',
    openTime: '09:00',
    closeTime: '15:30',
  }

  const handleStrategyToggle = async () => {
    // 엔진 시작 시: disclaimer 동의 여부 확인
    if (!engineRunning && consentStatus && !consentStatus.disclaimer.up_to_date) {
      setShowDisclaimer(true)
      return
    }
    await executeStrategyToggle()
  }

  const executeStrategyToggle = async () => {
    setStrategyLoading(true)
    try {
      if (engineRunning) {
        await localEngine.stop()
      } else {
        await localEngine.start()
      }
      queryClient.invalidateQueries({ queryKey: ['localStatus'] })
    } finally {
      setStrategyLoading(false)
    }
  }

  const handleCancelOrder = async (orderId: string) => {
    try {
      await localAccount.cancelOrder(orderId)
      queryClient.invalidateQueries({ queryKey: ['openOrders'] })
    } catch {
      // 취소 실패 시 조용히 무시 (UI에서 재시도 가능)
    }
  }

  const handleDetail = (stock: Stock) => {
    setSelectedStock(stock)
    setView('detail')
  }

  const handleBack = () => {
    setView('list')
    setSelectedStock(null)
  }

  if (!onboardingDone) return <Navigate to="/onboarding" replace />

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <Header
        onStockSelect={handleDetail}
        engineRunning={engineRunning}
        brokerConnected={brokerConnected}
      />

      <main className="w-full max-w-6xl mx-auto px-3 sm:px-4 py-4 sm:py-5">
        <div key={view} className="animate-[fadeSlideIn_200ms_ease-out]">
          {view === 'list' ? (
            <>
            <OpsPanel
              localConnected={isRemote ? (remoteState?.local_online ?? false) : localReady}
              brokerConnected={effectiveBroker}
              engineRunning={effectiveEngine}
              isMock={isRemote ? null : isMock}
              killSwitch={effectiveKill}
              lossLock={effectiveLoss}
              isRemote={isRemote}
              remoteConnected={remoteConnected}
            />
            <BriefingCard />
            <ListView
              tab={tab}
              setTab={setTab}
              stocks={stocks}
              account={account}
              isMock={isRemote ? null : isMock}
              marketStatus={marketStatus}
              trades={trades}
              pendingOrders={pendingOrders}
              onDetail={handleDetail}
              engineRunning={effectiveEngine}
              brokerConnected={effectiveBroker}
              onStrategyToggle={isRemote ? undefined : handleStrategyToggle}
              strategyLoading={strategyLoading}
              watchlistSet={watchlistSet}
              onToggleWatchlist={(sym, add) => toggleWatchlist({ symbol: sym, add })}
              onCancelOrder={isRemote ? undefined : handleCancelOrder}
            />
            </>
          ) : (
            <DetailView
              stock={selectedStock!}
              trades={trades}
              rules={rules.filter(r => r.symbol === selectedStock?.symbol)}
              context={context}
              onBack={handleBack}
              isWatchlisted={selectedStock ? watchlistSet.has(selectedStock.symbol) : false}
              onToggleWatchlist={(sym, add) => toggleWatchlist({ symbol: sym, add })}
            />
          )}
        </div>
      </main>

      {/* 면책 고지 모달 */}
      {showDisclaimer && consentStatus && (
        <DisclaimerModal
          latestVersion={consentStatus.disclaimer.latest_version}
          onAccepted={() => {
            setShowDisclaimer(false)
            executeStrategyToggle()
          }}
          onCancel={() => setShowDisclaimer(false)}
        />
      )}

      {/* 원격 모드: Kill Switch FAB + Arm 다이얼로그 */}
      {isRemote && remoteConnected && (
        <>
          <KillSwitchFAB
            onKill={sendKill}
            disabled={effectiveKill}
          />
          {showArmDialog && remoteState && (
            <ArmDialog
              state={remoteState}
              onArm={sendArm}
              onClose={() => setShowArmDialog(false)}
            />
          )}
        </>
      )}
    </div>
  )
}
