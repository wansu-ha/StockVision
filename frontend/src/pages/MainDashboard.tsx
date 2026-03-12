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
import { useOnboarding } from '../hooks/useOnboarding'
import ListView from '../components/main/ListView'
import DetailView from '../components/main/DetailView'
import { useAuth } from '../context/AuthContext'
import { useStockData } from '../hooks/useStockData'
import { useAccountStatus } from '../hooks/useAccountStatus'
import { useAccountBalance } from '../hooks/useAccountBalance'
import { useMarketContext } from '../hooks/useMarketContext'
import { localLogs, localEngine } from '../services/localClient'
import type { Stock, AccountInfo, Trade, PendingOrder, MarketStatus } from '../components/main/ListView'

export default function MainDashboard() {
  const { completed: onboardingDone } = useOnboarding()
  const [view, setView] = useState<'list' | 'detail'>('list')
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null)
  const [tab, setTab] = useState<'my' | 'watch'>('my')
  const [strategyLoading, setStrategyLoading] = useState(false)

  const queryClient = useQueryClient()
  const { localReady } = useAuth()
  const { myStocks, watchStocks, rules } = useStockData()
  const { engineRunning, brokerConnected, credentials, isMock, killSwitch, lossLock } = useAccountStatus()
  const { balance, openOrders } = useAccountBalance(brokerConnected)
  const { context } = useMarketContext()

  // 체결 로그 (fill 타입만) — localSecret 준비 후 실행
  const { data: logData } = useQuery({
    queryKey: ['fillLogs'],
    queryFn: () => localLogs.get({ log_type: 'fill', limit: 50 } as never),
    enabled: localReady,
    refetchInterval: 15_000,
    retry: 1,
  })

  // 일일 P&L (C1)
  const { data: dailyPnl } = useQuery({
    queryKey: ['dailyPnl'],
    queryFn: () => localLogs.dailyPnl(),
    enabled: localReady,
    refetchInterval: 30_000,
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

  // 장 상태 — 시간 기반 추정
  const now = new Date()
  const hhmm = now.getHours() * 100 + now.getMinutes()
  const marketStatus: MarketStatus = {
    status: hhmm >= 900 && hhmm < 1530 ? '장중' : hhmm < 900 ? '장전' : '장후',
    openTime: '09:00',
    closeTime: '15:30',
  }

  const handleStrategyToggle = async () => {
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
              localConnected={localReady}
              brokerConnected={brokerConnected}
              engineRunning={engineRunning}
              isMock={isMock}
              killSwitch={killSwitch}
              lossLock={lossLock}
            />
            <ListView
              tab={tab}
              setTab={setTab}
              stocks={stocks}
              account={account}
              isMock={isMock}
              marketStatus={marketStatus}
              trades={trades}
              pendingOrders={pendingOrders}
              onDetail={handleDetail}
              engineRunning={engineRunning}
              brokerConnected={brokerConnected}
              onStrategyToggle={handleStrategyToggle}
              strategyLoading={strategyLoading}
            />
            </>
          ) : (
            <DetailView
              stock={selectedStock!}
              trades={trades}
              rules={rules.filter(r => r.symbol === selectedStock?.symbol)}
              context={context}
              onBack={handleBack}
            />
          )}
        </div>
      </main>
    </div>
  )
}
