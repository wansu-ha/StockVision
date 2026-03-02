import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useToastStore } from '../stores/toastStore'
import {
  Card, CardBody, CardHeader, Button, Input, Chip,
} from '@heroui/react'
import {
  BanknotesIcon,
  ChartBarIcon,
  ClockIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  CpuChipIcon,
  PlayIcon,
  PlusIcon,
  BeakerIcon,
  BoltIcon,
  ShoppingCartIcon,
} from '@heroicons/react/24/outline'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { tradingApi, stockApi } from '../services/api'
import type {
  AccountSummary, VirtualPosition, VirtualTrade,
  StockScore, BacktestResultSummary, AutoTradingRule,
  PlaceOrderRequest, CreateRuleRequest, BacktestResult,
} from '../types/trading'
import type { Stock } from '../types'

type TabKey = 'overview' | 'scores' | 'backtest' | 'rules'

const Trading = () => {
  const queryClient = useQueryClient()
  const showToast = useToastStore((s) => s.showToast)
  const [activeTab, setActiveTab] = useState<TabKey>('overview')
  const [selectedAccountId] = useState<number | null>(null)

  // 계좌 목록
  const { data: accountsData, isLoading: accountsLoading, isError: accountsError } = useQuery({
    queryKey: ['trading-accounts'],
    queryFn: tradingApi.getAccounts,
    staleTime: 30_000,
  })

  const accounts = accountsData?.data || []

  // 첫 계좌 자동 선택
  const accountId = selectedAccountId ?? accounts[0]?.id ?? null

  // 계좌 상세
  const { data: summaryData } = useQuery({
    queryKey: ['account-summary', accountId],
    queryFn: () => tradingApi.getAccountDetail(accountId!),
    enabled: !!accountId,
    staleTime: 10_000,
  })

  // 포지션
  const { data: positionsData } = useQuery({
    queryKey: ['positions', accountId],
    queryFn: () => tradingApi.getPositions(accountId!),
    enabled: !!accountId,
    staleTime: 10_000,
  })

  // 거래 내역
  const { data: tradesData } = useQuery({
    queryKey: ['trades', accountId],
    queryFn: () => tradingApi.getTradeHistory(accountId!, 20),
    enabled: !!accountId,
    staleTime: 10_000,
  })

  // 스코어
  const { data: scoresData } = useQuery({
    queryKey: ['scores'],
    queryFn: () => tradingApi.getScores(20),
    enabled: activeTab === 'scores',
    staleTime: 60_000,
  })

  // 백테스팅 결과 목록
  const { data: backtestData } = useQuery({
    queryKey: ['backtest-results'],
    queryFn: () => tradingApi.getBacktestResults(10),
    enabled: activeTab === 'backtest',
    staleTime: 60_000,
  })

  // 자동매매 규칙
  const { data: rulesData } = useQuery({
    queryKey: ['trading-rules'],
    queryFn: tradingApi.getRules,
    enabled: activeTab === 'rules',
    staleTime: 30_000,
  })

  // 계좌 생성
  const createAccountMutation = useMutation({
    mutationFn: tradingApi.createAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trading-accounts'] })
      showToast('계좌가 생성되었습니다.', 'success')
    },
    onError: () => showToast('계좌 생성에 실패했습니다.', 'error'),
  })

  // 스코어링 실행
  const calculateScoresMutation = useMutation({
    mutationFn: tradingApi.calculateScores,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['scores'] })
      const count = data?.data?.length ?? 0
      showToast(`스코어링 완료: ${count}개 종목`, 'success')
    },
    onError: () => showToast('스코어링 실행에 실패했습니다.', 'error'),
  })

  // 백테스팅 실행
  const [btStartDate, setBtStartDate] = useState('2025-01-01')
  const [btEndDate, setBtEndDate] = useState('2025-12-31')
  const runBacktestMutation = useMutation({
    mutationFn: tradingApi.runBacktest,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['backtest-results'] })
      const ret = data?.data?.total_return
      const msg = ret != null ? `백테스팅 완료: 수익률 ${ret}%` : '백테스팅이 완료되었습니다.'
      showToast(msg, 'success')
    },
    onError: () => showToast('백테스팅 실행에 실패했습니다.', 'error'),
  })

  // 규칙 토글
  const toggleRuleMutation = useMutation({
    mutationFn: ({ ruleId, isActive }: { ruleId: number; isActive: boolean }) =>
      tradingApi.updateRule(ruleId, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['trading-rules'] }),
  })

  // 종목 목록 (주문 폼용)
  const { data: stocksQueryData } = useQuery({
    queryKey: ['stocks'],
    queryFn: stockApi.getStocks,
    staleTime: 60_000,
  })

  // 주문 실행
  const placeOrderMutation = useMutation({
    mutationFn: tradingApi.placeOrder,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['positions', accountId] })
      queryClient.invalidateQueries({ queryKey: ['trades', accountId] })
      queryClient.invalidateQueries({ queryKey: ['account-summary', accountId] })
      const t = data?.data
      const msg = t ? `${t.symbol} ${t.trade_type === 'BUY' ? '매수' : '매도'} 주문 완료` : '주문이 완료되었습니다.'
      showToast(msg, 'success')
    },
    onError: () => showToast('주문 실행에 실패했습니다.', 'error'),
  })

  // 규칙 생성
  const createRuleMutation = useMutation({
    mutationFn: tradingApi.createRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trading-rules'] })
      showToast('자동매매 규칙이 생성되었습니다.', 'success')
    },
    onError: () => showToast('규칙 생성에 실패했습니다.', 'error'),
  })

  const summary: AccountSummary | null = summaryData?.data ?? null
  const positions: VirtualPosition[] = positionsData?.data ?? []
  const trades: VirtualTrade[] = tradesData?.data ?? []
  const scores: StockScore[] = scoresData?.data ?? []
  const backtestResults: BacktestResultSummary[] = backtestData?.data ?? []
  const rules: AutoTradingRule[] = rulesData?.data ?? []
  const allStocks: Stock[] = stocksQueryData?.data ?? []

  // 로딩 상태
  if (accountsLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 bg-blue-500 rounded-full mx-auto mb-6 flex items-center justify-center animate-pulse">
            <BanknotesIcon className="w-6 h-6 text-white" />
          </div>
          <p className="text-gray-700 text-xl font-medium">거래 데이터를 불러오는 중...</p>
        </div>
      </div>
    )
  }

  // 백엔드 연결 실패
  if (accountsError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-red-100 rounded-2xl mx-auto mb-6 flex items-center justify-center">
            <BanknotesIcon className="w-8 h-8 text-red-500" />
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">서버에 연결할 수 없습니다</h2>
          <p className="text-gray-500 text-sm">백엔드 서버가 실행 중인지 확인하세요. (http://localhost:8000)</p>
        </div>
      </div>
    )
  }

  // 계좌 없을 때
  if (accounts.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-3xl mx-auto px-6 py-20 text-center">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-3xl mx-auto mb-8 flex items-center justify-center">
            <BanknotesIcon className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-4">가상 거래 시작하기</h1>
          <p className="text-gray-500 mb-8">첫 가상 계좌를 만들어 AI 기반 자동매매를 시작하세요.</p>
          <Button
            color="primary"
            size="lg"
            startContent={<PlusIcon className="w-5 h-5" />}
            onPress={() => createAccountMutation.mutate({ name: '기본 계좌', initial_balance: 10_000_000 })}
            isLoading={createAccountMutation.isPending}
          >
            계좌 생성 (1,000만원)
          </Button>
        </div>
      </div>
    )
  }

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'overview', label: '계좌 총괄', icon: <BanknotesIcon className="w-4 h-4" /> },
    { key: 'scores', label: '스코어링', icon: <ChartBarIcon className="w-4 h-4" /> },
    { key: 'backtest', label: '백테스팅', icon: <BeakerIcon className="w-4 h-4" /> },
    { key: 'rules', label: '자동매매', icon: <BoltIcon className="w-4 h-4" /> },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* 헤더 */}
      <div className="bg-white shadow-lg border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">가상 거래</h1>
              <p className="text-gray-500 mt-1">AI 스코어링 기반 자동매매 시스템</p>
            </div>
            {summary && (
              <div className="text-right">
                <p className="text-sm text-gray-500">총 자산</p>
                <p className="text-2xl font-bold text-gray-900">
                  {summary.total_assets.toLocaleString()}원
                </p>
                <Chip
                  color={summary.total_return_rate >= 0 ? 'success' : 'danger'}
                  variant="flat"
                  size="sm"
                >
                  {summary.total_return_rate >= 0 ? '+' : ''}{summary.total_return_rate}%
                </Chip>
              </div>
            )}
          </div>

          {/* 탭 */}
          <div className="flex space-x-2 mt-6">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                  activeTab === tab.key
                    ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 컨텐츠 */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {activeTab === 'overview' && (
          <OverviewTab
            summary={summary}
            positions={positions}
            trades={trades}
            accountId={accountId}
            stocks={allStocks}
            onPlaceOrder={(req) => placeOrderMutation.mutate(req)}
            isOrdering={placeOrderMutation.isPending}
          />
        )}
        {activeTab === 'scores' && (
          <ScoresTab
            scores={scores}
            onCalculate={() => calculateScoresMutation.mutate()}
            isCalculating={calculateScoresMutation.isPending}
          />
        )}
        {activeTab === 'backtest' && (
          <BacktestTab
            results={backtestResults}
            startDate={btStartDate}
            endDate={btEndDate}
            onStartDateChange={setBtStartDate}
            onEndDateChange={setBtEndDate}
            onRun={() => runBacktestMutation.mutate({ start_date: btStartDate, end_date: btEndDate })}
            isRunning={runBacktestMutation.isPending}
            latestResult={runBacktestMutation.data?.data ?? null}
          />
        )}
        {activeTab === 'rules' && (
          <RulesTab
            rules={rules}
            onToggle={(ruleId, isActive) => toggleRuleMutation.mutate({ ruleId, isActive })}
            accountId={accountId}
            onCreateRule={(data) => createRuleMutation.mutate(data)}
            isCreating={createRuleMutation.isPending}
          />
        )}
      </div>
    </div>
  )
}

// ── 계좌 총괄 탭 ──

function OverviewTab({
  summary,
  positions,
  trades,
  accountId,
  stocks,
  onPlaceOrder,
  isOrdering,
}: {
  summary: AccountSummary | null
  positions: VirtualPosition[]
  trades: VirtualTrade[]
  accountId: number | null
  stocks: Stock[]
  onPlaceOrder: (req: PlaceOrderRequest) => void
  isOrdering: boolean
}) {
  const [orderSymbol, setOrderSymbol] = useState('')
  const [orderQty, setOrderQty] = useState('10')
  const [orderPrice, setOrderPrice] = useState('')

  const handleOrder = (type: 'BUY' | 'SELL') => {
    const selectedStock = stocks.find(s => s.symbol === orderSymbol)
    if (!selectedStock || !accountId || !orderQty || !orderPrice) return
    onPlaceOrder({
      account_id: accountId,
      stock_id: selectedStock.id,
      symbol: orderSymbol,
      trade_type: type,
      quantity: parseInt(orderQty),
      price: parseFloat(orderPrice),
    })
  }

  if (!summary) {
    return <p className="text-gray-500">계좌 데이터를 불러오는 중...</p>
  }

  return (
    <div className="space-y-8">
      {/* 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon={<BanknotesIcon className="w-6 h-6 text-blue-600" />}
          label="현금 잔고"
          value={`${summary.current_balance.toLocaleString()}원`}
          color="blue"
        />
        <StatCard
          icon={<ChartBarIcon className="w-6 h-6 text-purple-600" />}
          label="포지션 가치"
          value={`${summary.total_position_value.toLocaleString()}원`}
          color="purple"
        />
        <StatCard
          icon={
            summary.total_profit_loss >= 0
              ? <ArrowTrendingUpIcon className="w-6 h-6 text-green-600" />
              : <ArrowTrendingDownIcon className="w-6 h-6 text-red-600" />
          }
          label="실현 손익"
          value={`${summary.total_profit_loss >= 0 ? '+' : ''}${summary.total_profit_loss.toLocaleString()}원`}
          color={summary.total_profit_loss >= 0 ? 'green' : 'red'}
        />
        <StatCard
          icon={<CpuChipIcon className="w-6 h-6 text-amber-600" />}
          label="승률"
          value={`${summary.win_rate}% (${summary.win_trades}/${summary.total_trades})`}
          color="amber"
        />
      </div>

      {/* 주문 폼 */}
      <Card className="shadow-lg">
        <CardHeader className="p-6 pb-4">
          <div className="flex items-center gap-2">
            <ShoppingCartIcon className="w-5 h-5 text-gray-600" />
            <h2 className="text-lg font-bold text-gray-900">주문 실행</h2>
          </div>
        </CardHeader>
        <CardBody className="px-6 pb-6 pt-0">
          <div className="flex items-end gap-4 flex-wrap">
            <div>
              <label className="text-sm text-gray-600 mb-1 block">종목</label>
              <select
                value={orderSymbol}
                onChange={(e) => setOrderSymbol(e.target.value)}
                className="border border-gray-200 rounded-xl px-3 py-2 text-sm min-w-[160px] bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
              >
                <option value="">종목 선택</option>
                {stocks.map(s => (
                  <option key={s.id} value={s.symbol}>{s.symbol} - {s.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">가격 (원)</label>
              <Input
                type="number"
                value={orderPrice}
                onChange={(e) => setOrderPrice(e.target.value)}
                placeholder="0"
                size="sm"
                classNames={{ base: 'w-36' }}
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">수량</label>
              <Input
                type="number"
                value={orderQty}
                onChange={(e) => setOrderQty(e.target.value)}
                min="1"
                size="sm"
                classNames={{ base: 'w-24' }}
              />
            </div>
            <Button
              color="primary"
              onPress={() => handleOrder('BUY')}
              isLoading={isOrdering}
              isDisabled={!orderSymbol || !orderPrice || !orderQty}
            >
              매수
            </Button>
            <Button
              color="danger"
              variant="flat"
              onPress={() => handleOrder('SELL')}
              isLoading={isOrdering}
              isDisabled={!orderSymbol || !orderPrice || !orderQty}
            >
              매도
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* 보유 포지션 */}
      <Card className="shadow-lg">
        <CardHeader className="p-6 pb-4">
          <h2 className="text-lg font-bold text-gray-900">보유 포지션</h2>
        </CardHeader>
        <CardBody className="px-6 pb-6 pt-0">
          {positions.length === 0 ? (
            <p className="text-gray-400 text-center py-8">보유 포지션이 없습니다</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 font-semibold text-gray-600">종목</th>
                    <th className="text-right py-3 font-semibold text-gray-600">수량</th>
                    <th className="text-right py-3 font-semibold text-gray-600">평균가</th>
                    <th className="text-right py-3 font-semibold text-gray-600">현재가</th>
                    <th className="text-right py-3 font-semibold text-gray-600">평가손익</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((p) => (
                    <tr key={p.id} className="border-b border-gray-50">
                      <td className="py-3 font-medium">{p.symbol}</td>
                      <td className="py-3 text-right">{p.quantity}</td>
                      <td className="py-3 text-right">{p.avg_price.toLocaleString()}</td>
                      <td className="py-3 text-right">{(p.current_price ?? 0).toLocaleString()}</td>
                      <td className={`py-3 text-right font-medium ${p.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {p.unrealized_pnl >= 0 ? '+' : ''}{p.unrealized_pnl.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>

      {/* 거래 내역 */}
      <Card className="shadow-lg">
        <CardHeader className="p-6 pb-4">
          <div className="flex items-center gap-2">
            <ClockIcon className="w-5 h-5 text-gray-600" />
            <h2 className="text-lg font-bold text-gray-900">최근 거래 내역</h2>
          </div>
        </CardHeader>
        <CardBody className="px-6 pb-6 pt-0">
          {trades.length === 0 ? (
            <p className="text-gray-400 text-center py-8">거래 내역이 없습니다</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 font-semibold text-gray-600">시간</th>
                    <th className="text-left py-3 font-semibold text-gray-600">종목</th>
                    <th className="text-center py-3 font-semibold text-gray-600">구분</th>
                    <th className="text-right py-3 font-semibold text-gray-600">수량</th>
                    <th className="text-right py-3 font-semibold text-gray-600">가격</th>
                    <th className="text-right py-3 font-semibold text-gray-600">손익</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t) => (
                    <tr key={t.id} className="border-b border-gray-50">
                      <td className="py-3 text-gray-500">{t.timestamp.slice(0, 16)}</td>
                      <td className="py-3 font-medium">{t.symbol}</td>
                      <td className="py-3 text-center">
                        <Chip size="sm" color={t.trade_type === 'BUY' ? 'primary' : 'danger'} variant="flat">
                          {t.trade_type === 'BUY' ? '매수' : '매도'}
                        </Chip>
                      </td>
                      <td className="py-3 text-right">{t.quantity}</td>
                      <td className="py-3 text-right">{t.price.toLocaleString()}</td>
                      <td className={`py-3 text-right font-medium ${
                        t.realized_pnl === null ? 'text-gray-400' :
                        t.realized_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {t.realized_pnl !== null
                          ? `${t.realized_pnl >= 0 ? '+' : ''}${t.realized_pnl.toLocaleString()}`
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

// ── 스코어링 탭 ──

function ScoresTab({
  scores,
  onCalculate,
  isCalculating,
}: {
  scores: StockScore[]
  onCalculate: () => void
  isCalculating: boolean
}) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-gray-900">종목 스코어링 순위</h2>
        <Button
          color="primary"
          startContent={<PlayIcon className="w-4 h-4" />}
          onPress={onCalculate}
          isLoading={isCalculating}
        >
          스코어링 실행
        </Button>
      </div>

      {scores.length === 0 ? (
        <Card className="shadow-lg">
          <CardBody className="py-16 text-center">
            <ChartBarIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-400">스코어링 결과가 없습니다. 위 버튼을 눌러 실행하세요.</p>
          </CardBody>
        </Card>
      ) : (
        <Card className="shadow-lg">
          <CardBody className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 bg-gray-50">
                    <th className="text-left py-3 px-4 font-semibold text-gray-600">#</th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-600">종목</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-600">RSI</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-600">MACD</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-600">볼린저</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-600">EMA</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-600">예측</th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-600">통합</th>
                    <th className="text-center py-3 px-4 font-semibold text-gray-600">신호</th>
                  </tr>
                </thead>
                <tbody>
                  {scores.map((s, idx) => (
                    <tr key={s.id} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="py-3 px-4 text-gray-400">{idx + 1}</td>
                      <td className="py-3 px-4 font-medium">{s.symbol}</td>
                      <td className="py-3 px-4 text-right">{s.rsi_score.toFixed(1)}</td>
                      <td className="py-3 px-4 text-right">{s.macd_score.toFixed(1)}</td>
                      <td className="py-3 px-4 text-right">{s.bollinger_score.toFixed(1)}</td>
                      <td className="py-3 px-4 text-right">{s.ema_score.toFixed(1)}</td>
                      <td className="py-3 px-4 text-right">{s.prediction_score.toFixed(1)}</td>
                      <td className="py-3 px-4 text-right font-bold">{s.total_score.toFixed(1)}</td>
                      <td className="py-3 px-4 text-center">
                        <Chip
                          size="sm"
                          variant="flat"
                          color={s.signal === 'BUY' ? 'success' : s.signal === 'SELL' ? 'danger' : 'default'}
                        >
                          {s.signal === 'BUY' ? '매수' : s.signal === 'SELL' ? '매도' : '관망'}
                        </Chip>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  )
}

// ── 백테스팅 탭 ──

function BacktestTab({
  results,
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  onRun,
  isRunning,
  latestResult,
}: {
  results: BacktestResultSummary[]
  startDate: string
  endDate: string
  onStartDateChange: (v: string) => void
  onEndDateChange: (v: string) => void
  onRun: () => void
  isRunning: boolean
  latestResult: BacktestResult | null
}) {
  const equityCurve = (() => {
    if (!latestResult?.trade_details?.length) return []
    const sorted = [...latestResult.trade_details].sort((a, b) => a.date.localeCompare(b.date))
    let balance = latestResult.initial_balance
    const pts: { date: string; balance: number }[] = [
      { date: latestResult.start_date.slice(0, 10), balance },
    ]
    for (const t of sorted) {
      balance += (t.realized_pnl ?? 0)
      pts.push({ date: t.date.slice(0, 10), balance })
    }
    pts.push({ date: latestResult.end_date.slice(0, 10), balance: latestResult.final_balance })
    return pts
  })()

  return (
    <div className="space-y-6">
      {/* 실행 폼 */}
      <Card className="shadow-lg">
        <CardHeader className="p-6 pb-4">
          <h2 className="text-lg font-bold text-gray-900">백테스팅 실행</h2>
        </CardHeader>
        <CardBody className="px-6 pb-6 pt-0">
          <div className="flex items-end gap-4">
            <div>
              <label className="text-sm text-gray-600 mb-1 block">시작일</label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => onStartDateChange(e.target.value)}
                size="sm"
              />
            </div>
            <div>
              <label className="text-sm text-gray-600 mb-1 block">종료일</label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => onEndDateChange(e.target.value)}
                size="sm"
              />
            </div>
            <Button
              color="primary"
              startContent={<BeakerIcon className="w-4 h-4" />}
              onPress={onRun}
              isLoading={isRunning}
            >
              실행
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* 수익률 차트 */}
      {equityCurve.length > 1 && (
        <Card className="shadow-lg">
          <CardHeader className="p-6 pb-4">
            <div className="flex items-center justify-between w-full">
              <h2 className="text-lg font-bold text-gray-900">수익률 곡선</h2>
              <span className={`text-sm font-semibold ${latestResult!.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {latestResult!.total_return >= 0 ? '+' : ''}{latestResult!.total_return}%
              </span>
            </div>
          </CardHeader>
          <CardBody className="px-6 pb-6 pt-0">
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={equityCurve}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                <YAxis
                  tickFormatter={(v) => `${(v / 10000).toFixed(0)}만`}
                  tick={{ fontSize: 11 }}
                  width={60}
                />
                <Tooltip formatter={(value: number) => [`${value.toLocaleString('ko-KR')}원`, '자산']} />
                <Line type="monotone" dataKey="balance" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>
      )}

      {/* 결과 목록 */}
      <Card className="shadow-lg">
        <CardHeader className="p-6 pb-4">
          <h2 className="text-lg font-bold text-gray-900">백테스팅 결과</h2>
        </CardHeader>
        <CardBody className="px-6 pb-6 pt-0">
          {results.length === 0 ? (
            <p className="text-gray-400 text-center py-8">결과가 없습니다</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 font-semibold text-gray-600">전략</th>
                    <th className="text-left py-3 font-semibold text-gray-600">기간</th>
                    <th className="text-right py-3 font-semibold text-gray-600">수익률</th>
                    <th className="text-right py-3 font-semibold text-gray-600">승률</th>
                    <th className="text-right py-3 font-semibold text-gray-600">샤프</th>
                    <th className="text-right py-3 font-semibold text-gray-600">MDD</th>
                    <th className="text-right py-3 font-semibold text-gray-600">거래</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r) => (
                    <tr key={r.id} className="border-b border-gray-50">
                      <td className="py-3 font-medium">{r.strategy_name}</td>
                      <td className="py-3 text-gray-500">{r.start_date.slice(0, 10)} ~ {r.end_date.slice(0, 10)}</td>
                      <td className={`py-3 text-right font-bold ${r.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {r.total_return >= 0 ? '+' : ''}{r.total_return}%
                      </td>
                      <td className="py-3 text-right">{r.win_rate}%</td>
                      <td className="py-3 text-right">{r.sharpe_ratio.toFixed(2)}</td>
                      <td className="py-3 text-right text-red-500">{r.max_drawdown.toFixed(1)}%</td>
                      <td className="py-3 text-right">{r.total_trades}회</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

// ── 자동매매 규칙 탭 ──

function RulesTab({
  rules,
  onToggle,
  accountId,
  onCreateRule,
  isCreating,
}: {
  rules: AutoTradingRule[]
  onToggle: (ruleId: number, isActive: boolean) => void
  accountId: number | null
  onCreateRule: (data: CreateRuleRequest) => void
  isCreating: boolean
}) {
  const [showForm, setShowForm] = useState(false)
  const [ruleName, setRuleName] = useState('')
  const [buyThreshold, setBuyThreshold] = useState('70')
  const [maxPositions, setMaxPositions] = useState('5')
  const [budgetRatio, setBudgetRatio] = useState('20')

  const handleCreateRule = () => {
    if (!ruleName) return
    onCreateRule({
      name: ruleName,
      account_id: accountId ?? undefined,
      buy_score_threshold: parseFloat(buyThreshold),
      max_position_count: parseInt(maxPositions),
      budget_ratio: parseFloat(budgetRatio) / 100,
    })
    setRuleName('')
    setShowForm(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-gray-900">자동매매 규칙</h2>
        <Button
          color="primary"
          size="sm"
          startContent={<PlusIcon className="w-4 h-4" />}
          onPress={() => setShowForm(!showForm)}
        >
          규칙 추가
        </Button>
      </div>

      {showForm && (
        <Card className="shadow-lg border-2 border-blue-100">
          <CardHeader className="p-6 pb-4">
            <h3 className="text-base font-bold text-gray-900">새 규칙 생성</h3>
          </CardHeader>
          <CardBody className="px-6 pb-6 pt-0">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-gray-600 mb-1 block">규칙 이름</label>
                <Input
                  value={ruleName}
                  onChange={(e) => setRuleName(e.target.value)}
                  placeholder="예: 공격적 매수 전략"
                  size="sm"
                />
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">매수 기준점 (0~100)</label>
                <Input
                  type="number"
                  value={buyThreshold}
                  onChange={(e) => setBuyThreshold(e.target.value)}
                  min="0"
                  max="100"
                  size="sm"
                />
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">최대 종목 수</label>
                <Input
                  type="number"
                  value={maxPositions}
                  onChange={(e) => setMaxPositions(e.target.value)}
                  min="1"
                  size="sm"
                />
              </div>
              <div>
                <label className="text-sm text-gray-600 mb-1 block">예산 비율 (%)</label>
                <Input
                  type="number"
                  value={budgetRatio}
                  onChange={(e) => setBudgetRatio(e.target.value)}
                  min="1"
                  max="100"
                  size="sm"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <Button variant="flat" size="sm" onPress={() => setShowForm(false)}>
                취소
              </Button>
              <Button
                color="primary"
                size="sm"
                onPress={handleCreateRule}
                isLoading={isCreating}
                isDisabled={!ruleName}
              >
                생성
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {rules.length === 0 ? (
        <Card className="shadow-lg">
          <CardBody className="py-16 text-center">
            <BoltIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-400">등록된 규칙이 없습니다</p>
            <p className="text-gray-400 text-sm mt-1">위 버튼으로 첫 규칙을 추가하세요</p>
          </CardBody>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {rules.map((rule) => (
            <Card key={rule.id} className="shadow-lg">
              <CardBody className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="font-bold text-gray-900">{rule.name}</h3>
                    <p className="text-sm text-gray-500">{rule.strategy_type}</p>
                  </div>
                  <Button
                    size="sm"
                    color={rule.is_active ? 'success' : 'default'}
                    variant={rule.is_active ? 'flat' : 'bordered'}
                    onPress={() => onToggle(rule.id, !rule.is_active)}
                  >
                    {rule.is_active ? '활성' : '비활성'}
                  </Button>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-500">매수 기준</span>
                    <p className="font-medium">{rule.buy_score_threshold}점 이상</p>
                  </div>
                  <div>
                    <span className="text-gray-500">최대 종목</span>
                    <p className="font-medium">{rule.max_position_count}개</p>
                  </div>
                  <div>
                    <span className="text-gray-500">예산 비율</span>
                    <p className="font-medium">{(rule.budget_ratio * 100).toFixed(0)}%</p>
                  </div>
                  <div>
                    <span className="text-gray-500">마지막 실행</span>
                    <p className="font-medium">{rule.last_executed_at ? rule.last_executed_at.slice(0, 16) : '없음'}</p>
                  </div>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

// ── 통계 카드 ──

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode
  label: string
  value: string
  color: string
}) {
  const bgMap: Record<string, string> = {
    blue: 'bg-blue-50',
    purple: 'bg-purple-50',
    green: 'bg-green-50',
    red: 'bg-red-50',
    amber: 'bg-amber-50',
  }

  return (
    <Card className="shadow-lg hover:shadow-xl transition-shadow">
      <CardBody className="p-6">
        <div className={`w-12 h-12 ${bgMap[color] || 'bg-gray-50'} rounded-xl flex items-center justify-center mb-4`}>
          {icon}
        </div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-xl font-bold text-gray-900 mt-1">{value}</p>
      </CardBody>
    </Card>
  )
}

export default Trading
