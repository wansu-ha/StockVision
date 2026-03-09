/**
 * Proto C — 종목 중심 싱글뷰 (A+B 장점 조합)
 *
 * 구조:
 *   max-w-6xl 중앙 정렬
 *   목록 뷰: 탭(내 종목|관심 종목) + 종목 리스트 + 체결 내역
 *   상세 뷰: 목록 사라지고 종목 상세가 꽉 참
 *   헤더: 로고 · 검색 · 알림 · ⚙️(엔진/설정/유저)
 */
import { useState, useRef, useEffect } from 'react'
import { createChart, ColorType, CandlestickSeries, HistogramSeries } from 'lightweight-charts'
import type { IChartApi } from 'lightweight-charts'

// ─── Mock Data ───────────────────────────────────────────

const MOCK_MY_STOCKS = [
  { symbol: '005930', name: '삼성전자', price: 72400, change: 1.2, rules: 3, lastTrade: '매수 @72,400' },
  { symbol: '000660', name: 'SK하이닉스', price: 185000, change: -0.5, rules: 1, lastTrade: '' },
  { symbol: '035420', name: 'NAVER', price: 215000, change: 0.8, rules: 2, lastTrade: '매도 @215,500' },
]

const MOCK_WATCHLIST = [
  { symbol: '005380', name: '현대차', price: 245000, change: -1.1, rules: 0, lastTrade: '' },
  { symbol: '051910', name: 'LG화학', price: 320000, change: 2.3, rules: 1, lastTrade: '매수 @318,000' },
  { symbol: '006400', name: '삼성SDI', price: 412000, change: 0.3, rules: 0, lastTrade: '' },
]

const MOCK_TRADES = [
  { time: '10:30:15', symbol: '삼성전자', side: '매수' as const, qty: 10, price: 72400, ok: true },
  { time: '10:15:02', symbol: 'SK하이닉스', side: '매도' as const, qty: 5, price: 185000, ok: true },
  { time: '09:45:33', symbol: '삼성전자', side: '매수' as const, qty: 10, price: 72800, ok: false },
  { time: '09:30:00', symbol: 'NAVER', side: '매도' as const, qty: 3, price: 215500, ok: true },
]

const MOCK_INDICATORS = [
  { label: 'RSI(14)', value: '34', status: 'low' },
  { label: 'RSI(21)', value: '38', status: 'low' },
  { label: 'MACD', value: '-0.5', status: 'neg' },
  { label: 'MACD Signal', value: '-0.3', status: 'neg' },
  { label: '볼린저 상단', value: '74,200', status: '' },
  { label: '볼린저 하단', value: '70,600', status: '' },
  { label: '변동성', value: '0.28', status: 'high' },
  { label: '거래량배수', value: '1.8x', status: '' },
]

const MOCK_RULES = [
  { id: 1, desc: 'RSI ≤ 30 → 매수 10주 (시장가)', active: true },
  { id: 2, desc: 'RSI ≥ 70 → 매도 전량 (시장가)', active: true },
  { id: 3, desc: '거래량 급증 → 매수 5주', active: false },
]

const MOCK_CONTEXT = [
  { label: 'KOSPI RSI', value: '52.1' },
  { label: 'KOSDAQ RSI', value: '48.3' },
  { label: '시장 추세', value: '중립' },
  { label: '변동성', value: '0.18' },
]

const MOCK_ACCOUNT = {
  broker: '키움증권',
  accountNo: '****-1234',
  totalValue: 15_650_000,
  availableCash: 3_200_000,
  dailyReturn: 1.2,
  holdings: [
    { symbol: '005930', name: '삼성전자', qty: 10, avgPrice: 71_500, currentPrice: 72_400 },
    { symbol: '035420', name: 'NAVER', qty: 5, avgPrice: 213_000, currentPrice: 215_000 },
  ],
}

const MOCK_PENDING_ORDERS = [
  { time: '10:45:00', symbol: '삼성전자', side: '매수' as const, qty: 5, price: 71_000, type: '지정가' },
]

const MOCK_MARKET_STATUS = {
  status: '장중' as const,
  openTime: '09:00',
  closeTime: '15:30',
}

const MOCK_NOTIFICATIONS = [
  { id: 1, type: 'trade', message: '삼성전자 매수 10주 체결', time: '10:30', read: false },
  { id: 2, type: 'alert', message: 'SK하이닉스 RSI(14) 30 이하 도달', time: '10:15', read: true },
]

// 1년치 mock 캔들 데이터 생성 (영업일만)
function generateCandles() {
  const candles: { time: string; open: number; high: number; low: number; close: number; volume: number }[] = []
  let price = 62000
  const end = new Date('2026-03-09')
  const start = new Date('2025-03-10')
  for (const d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    if (d.getDay() === 0 || d.getDay() === 6) continue
    const drift = (Math.random() - 0.48) * 1200
    const open = Math.round(price + (Math.random() - 0.5) * 400)
    const close = Math.round(price + drift)
    const high = Math.round(Math.max(open, close) + Math.random() * 800)
    const low = Math.round(Math.min(open, close) - Math.random() * 800)
    const volume = Math.round(10000 + Math.random() * 15000)
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    candles.push({ time: `${d.getFullYear()}-${mm}-${dd}`, open, high, low, close, volume })
    price = close
  }
  return candles
}
const MOCK_CANDLES = generateCandles()

const PERIOD_OPTIONS = [
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
] as const

type Stock = typeof MOCK_MY_STOCKS[0]

// ─── Component ───────────────────────────────────────────

export default function ProtoC() {
  const [view, setView] = useState<'list' | 'detail'>('list')
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null)
  const [tab, setTab] = useState<'my' | 'watch'>('my')
  const [expandedRow, setExpandedRow] = useState<string | null>(null)
  const [gearOpen, setGearOpen] = useState(false)
  const [notiOpen, setNotiOpen] = useState(false)

  const stocks = tab === 'my' ? MOCK_MY_STOCKS : MOCK_WATCHLIST

  const handleRowClick = (stock: Stock) => {
    setExpandedRow(expandedRow === stock.symbol ? null : stock.symbol)
  }

  const handleDetail = (stock: Stock) => {
    setSelectedStock(stock)
    setView('detail')
    setExpandedRow(null)
  }

  const handleBack = () => {
    setView('list')
    setSelectedStock(null)
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* ── 헤더 ── */}
      <header className="sticky top-0 z-40 bg-gray-900 border-b border-gray-800">
        <div className="max-w-6xl mx-auto h-12 flex items-center px-4 gap-4">
          <div className="flex items-center gap-2 shrink-0">
            <span className="font-bold text-blue-400">StockVision</span>
            <span className="w-2.5 h-2.5 rounded-full bg-green-400" title="전체 정상" />
          </div>

          <div className="flex-1 max-w-md mx-auto">
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
              placeholder="종목 검색..."
            />
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {/* 알림 */}
            <div className="relative">
              <button onClick={() => { setNotiOpen(!notiOpen); setGearOpen(false) }} className="relative text-gray-400 hover:text-white transition">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
                </svg>
                {MOCK_NOTIFICATIONS.filter(n => !n.read).length > 0 && (
                  <span className="absolute -top-1 -right-1.5 bg-red-500 text-[10px] text-white rounded-full w-4 h-4 flex items-center justify-center">
                    {MOCK_NOTIFICATIONS.filter(n => !n.read).length}
                  </span>
                )}
              </button>
              {notiOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setNotiOpen(false)} />
                  <div className="absolute right-0 top-full mt-2 w-80 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl z-50 overflow-hidden">
                    <div className="px-4 py-2.5 border-b border-gray-700 flex justify-between items-center">
                      <span className="text-sm font-medium">알림</span>
                      <button className="text-xs text-gray-500 hover:text-gray-300 transition">모두 읽음</button>
                    </div>
                    {MOCK_NOTIFICATIONS.map(n => (
                      <div key={n.id} className={`px-4 py-3 border-b border-gray-700/50 ${!n.read ? 'bg-blue-500/5' : ''}`}>
                        <div className="flex justify-between items-start">
                          <span className={`text-sm ${!n.read ? 'text-white' : 'text-gray-400'}`}>{n.message}</span>
                          {!n.read && <span className="w-2 h-2 rounded-full bg-blue-400 shrink-0 mt-1.5 ml-2" />}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">{n.time}</div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* 톱니바퀴 + 상태 신호등 */}
            <div className="relative">
              <button
                onClick={() => { setGearOpen(!gearOpen); setNotiOpen(false) }}
                className="text-gray-400 hover:text-white transition"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>

              {/* 톱니바퀴 드롭다운 */}
              {gearOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setGearOpen(false)} />
                  <div className="absolute right-0 top-full mt-2 w-72 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl z-50 overflow-hidden">
                    {/* 사용자 */}
                    <div className="px-4 py-3 border-b border-gray-700">
                      <div className="text-sm font-medium">홍길동</div>
                      <div className="text-xs text-gray-500">hong@example.com</div>
                      <div className="text-xs text-gray-500 mt-1">{MOCK_ACCOUNT.broker} {MOCK_ACCOUNT.accountNo}</div>
                    </div>

                    {/* 엔진 상태 */}
                    <div className="px-4 py-3 border-b border-gray-700">
                      <div className="text-xs text-gray-500 font-medium mb-2">엔진</div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                          <span className="text-sm text-green-400">실행 중</span>
                        </div>
                        <div className="flex gap-1.5">
                          <button className="px-2 py-1 text-xs bg-red-900/50 text-red-400 rounded border border-red-800 hover:bg-red-900 transition">중지</button>
                          <button className="px-2 py-1 text-xs bg-gray-700 text-gray-400 rounded border border-gray-600 hover:bg-gray-600 transition">Kill</button>
                        </div>
                      </div>
                      <div className="mt-1.5 text-xs text-gray-500">오늘 체결: <span className="text-white">5건</span></div>
                    </div>

                    {/* 연결 상태 */}
                    <div className="px-4 py-3 border-b border-gray-700">
                      <div className="text-xs text-gray-500 font-medium mb-2">연결 상태</div>
                      <div className="space-y-1">
                        {[
                          ['클라우드', true],
                          ['로컬 브리지', true],
                          ['브로커', true],
                        ].map(([label, ok]) => (
                          <div key={String(label)} className="flex justify-between text-xs">
                            <span className="text-gray-400">{String(label)}</span>
                            <span className={ok ? 'text-green-400' : 'text-red-400'}>{ok ? '연결됨' : '끊김'}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* 메뉴 */}
                    <div className="py-1">
                      <button className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700/50 transition">설정</button>
                      <button className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-gray-700/50 transition">로그아웃</button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* ── 메인 콘텐츠 ── */}
      <main className="max-w-6xl mx-auto px-4 py-5">
        {view === 'list' ? (
          <ListView
            tab={tab}
            setTab={setTab}
            stocks={stocks}
            expandedRow={expandedRow}
            onRowClick={handleRowClick}
            onDetail={handleDetail}
          />
        ) : (
          <DetailView stock={selectedStock!} onBack={handleBack} />
        )}
      </main>

      {/* 디자인 라벨 */}
      <div className="fixed bottom-4 left-4 bg-emerald-600 text-white text-xs px-3 py-1.5 rounded-full shadow-lg z-50">
        Proto C — 종목 중심 싱글뷰
      </div>
    </div>
  )
}

// ─── 목록 뷰 ─────────────────────────────────────────────

function ListView({
  tab,
  setTab,
  stocks,
  expandedRow,
  onRowClick,
  onDetail,
}: {
  tab: 'my' | 'watch'
  setTab: (t: 'my' | 'watch') => void
  stocks: Stock[]
  expandedRow: string | null
  onRowClick: (s: Stock) => void
  onDetail: (s: Stock) => void
}) {
  return (
    <>
      {/* 계좌 요약 */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">{MOCK_ACCOUNT.broker}</span>
            <span className="text-xs text-gray-600">{MOCK_ACCOUNT.accountNo}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-400" />
            <span className="text-green-400 text-xs">{MOCK_MARKET_STATUS.status}</span>
          </div>
        </div>
        <div className="flex items-baseline gap-6">
          <div>
            <div className="text-xs text-gray-500 mb-0.5">총 평가</div>
            <div className="text-xl font-mono font-bold">{MOCK_ACCOUNT.totalValue.toLocaleString()}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-0.5">주문가능</div>
            <div className="text-lg font-mono text-gray-300">{MOCK_ACCOUNT.availableCash.toLocaleString()}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-0.5">보유</div>
            <div className="text-lg font-mono text-gray-300">{MOCK_ACCOUNT.holdings.length}종목</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-0.5">오늘</div>
            <div className={`text-lg font-mono font-medium ${MOCK_ACCOUNT.dailyReturn >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
              {MOCK_ACCOUNT.dailyReturn >= 0 ? '+' : ''}{MOCK_ACCOUNT.dailyReturn}%
            </div>
          </div>
        </div>
      </div>

      {/* 종목 리스트 — 탭을 카드 내부에 배치 */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden mb-5">
        {/* 탭 (카드 헤더) */}
        <div className="flex gap-1 px-4 pt-3 pb-2 border-b border-gray-800/50">
          <button
            onClick={() => setTab('my')}
            className={`px-3 py-1 text-sm rounded-md transition ${
              tab === 'my'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            내 종목
          </button>
          <button
            onClick={() => setTab('watch')}
            className={`px-3 py-1 text-sm rounded-md transition ${
              tab === 'watch'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            관심 종목
          </button>
        </div>
        {stocks.map((s, i) => {
          const isExpanded = expandedRow === s.symbol
          return (
            <div key={s.symbol} className={`flex group ${i > 0 ? 'border-t border-gray-800/50' : ''} ${isExpanded ? 'bg-gray-800/20' : ''}`}>
              {/* 왼쪽 액센트 바 — 확장 시 항상, 호버 시 은은하게 */}
              <div className={`w-1 shrink-0 rounded-l transition-colors ${isExpanded ? 'bg-blue-500' : 'group-hover:bg-blue-500/40'}`} />

              {/* 왼쪽: 행 + 확장 영역 */}
              <div className="flex-1 min-w-0">
                {/* 기본 행 — 클릭 = 확장/축소 토글 */}
                <div
                  onClick={() => onRowClick(s)}
                  className="flex items-center px-4 py-3.5 cursor-pointer transition-colors hover:bg-gray-800/60"
                >
                  <div className="flex-1 min-w-0">
                    <div className="font-medium">{s.name}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{s.symbol}</div>
                  </div>
                  <div className="text-right mr-6">
                    <div className="font-mono font-medium">{s.price.toLocaleString()}</div>
                    <div className={`text-xs font-mono ${s.change >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                      {s.change >= 0 ? '+' : ''}{s.change}%
                    </div>
                  </div>
                  <div className="w-20 text-right mr-6">
                    {s.rules > 0 ? (
                      <span className="text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded-full">
                        {s.rules}개 규칙
                      </span>
                    ) : (
                      <span className="text-xs text-gray-600">—</span>
                    )}
                  </div>
                  <div className="w-28 text-right text-xs text-gray-500">
                    {s.lastTrade || '—'}
                  </div>
                </div>

                {/* 아코디언 확장 영역 */}
                {isExpanded && (
                  <div className="px-4 pb-4">
                    <div className="grid grid-cols-4 gap-3">
                      {MOCK_INDICATORS.slice(0, 4).map(ind => (
                        <div key={ind.label} className="bg-gray-900 border border-gray-700/50 rounded-lg px-3 py-2.5">
                          <div className="text-[11px] text-gray-400">{ind.label}</div>
                          <div className={`font-mono text-sm font-medium ${
                            ind.status === 'low' ? 'text-blue-400' :
                            ind.status === 'neg' ? 'text-red-400' : ''
                          }`}>{ind.value}</div>
                        </div>
                      ))}
                    </div>
                    <div className="mt-3 text-right">
                      <button
                        onClick={(e) => { e.stopPropagation(); onDetail(s) }}
                        className="text-xs text-blue-400 hover:text-blue-300 transition"
                      >
                        상세 보기 →
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* 오른쪽: 상세 보기 버튼 — 행 높이에 맞춰 늘어남 */}
              <button
                onClick={(e) => { e.stopPropagation(); onDetail(s) }}
                className={`w-11 shrink-0 flex items-center justify-center border-l border-gray-800/50 transition-colors cursor-pointer ${
                  isExpanded
                    ? 'bg-blue-500/10 text-blue-400 hover:bg-blue-500/20'
                    : 'bg-gray-800/30 text-gray-600 hover:text-blue-400 hover:bg-gray-800/50'
                }`}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              </button>
            </div>
          )
        })}
      </div>

      {/* 미체결 주문 */}
      {MOCK_PENDING_ORDERS.length > 0 && (
        <div className="mb-5">
          <h3 className="text-sm font-medium text-gray-400 mb-2">미체결 주문 <span className="text-yellow-400">{MOCK_PENDING_ORDERS.length}</span></h3>
          <div className="bg-gray-900 border border-yellow-800/30 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-gray-500 border-b border-gray-800">
                  <th className="text-left px-4 py-2.5 font-medium">시각</th>
                  <th className="text-left px-4 py-2.5 font-medium">종목</th>
                  <th className="text-left px-4 py-2.5 font-medium">방향</th>
                  <th className="text-right px-4 py-2.5 font-medium">수량</th>
                  <th className="text-right px-4 py-2.5 font-medium">가격</th>
                  <th className="text-right px-4 py-2.5 font-medium">유형</th>
                  <th className="text-right px-4 py-2.5 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {MOCK_PENDING_ORDERS.map((o, i) => (
                  <tr key={i} className="border-t border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                    <td className="px-4 py-2.5 font-mono text-gray-400">{o.time}</td>
                    <td className="px-4 py-2.5 font-medium">{o.symbol}</td>
                    <td className={`px-4 py-2.5 ${o.side === '매수' ? 'text-red-400' : 'text-blue-400'}`}>{o.side}</td>
                    <td className="px-4 py-2.5 text-right font-mono">{o.qty}</td>
                    <td className="px-4 py-2.5 text-right font-mono">{o.price.toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-right text-xs text-gray-400">{o.type}</td>
                    <td className="px-4 py-2.5 text-right">
                      <button className="text-xs text-red-400 hover:text-red-300 transition">취소</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 체결 내역 (탭과 무관하게 항상 노출) */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 mb-2">체결 내역</h3>
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-gray-800">
                <th className="text-left px-4 py-2.5 font-medium">시각</th>
                <th className="text-left px-4 py-2.5 font-medium">종목</th>
                <th className="text-left px-4 py-2.5 font-medium">방향</th>
                <th className="text-right px-4 py-2.5 font-medium">수량</th>
                <th className="text-right px-4 py-2.5 font-medium">가격</th>
                <th className="text-right px-4 py-2.5 font-medium">상태</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_TRADES.map((t, i) => (
                <tr key={i} className="border-t border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-2.5 font-mono text-gray-400">{t.time}</td>
                  <td className="px-4 py-2.5 font-medium">{t.symbol}</td>
                  <td className={`px-4 py-2.5 ${t.side === '매수' ? 'text-red-400' : 'text-blue-400'}`}>{t.side}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{t.qty}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{t.price.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-right">
                    {t.ok ? (
                      <span className="text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded">체결</span>
                    ) : (
                      <span className="text-xs text-red-400 bg-red-400/10 px-2 py-0.5 rounded">거부</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}

// ─── 가격 차트 (Lightweight Charts) ──────────────────────

function PriceChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ReturnType<IChartApi['addSeries']> | null>(null)
  const volumeSeriesRef = useRef<ReturnType<IChartApi['addSeries']> | null>(null)
  const [period, setPeriod] = useState<(typeof PERIOD_OPTIONS)[number]['label']>('3M')
  const [isZoomed, setIsZoomed] = useState(false)

  // 드래그 선택 상태
  const dragRef = useRef<{ active: boolean; startX: number }>({ active: false, startX: 0 })
  const selectionRef = useRef<HTMLDivElement>(null)

  // 차트 생성 (한 번만)
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#111827' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: '#374151' },
      timeScale: { borderColor: '#374151', timeVisible: false },
      handleScroll: { mouseWheel: true, pressedMouseMove: false },
      handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: false },
      height: 300,
    })
    chartRef.current = chart

    candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
      upColor: '#ef4444', downColor: '#3b82f6',
      borderUpColor: '#ef4444', borderDownColor: '#3b82f6',
      wickUpColor: '#ef4444', wickDownColor: '#3b82f6',
    })

    volumeSeriesRef.current = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })

    const ro = new ResizeObserver(() => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth })
    })
    ro.observe(containerRef.current)

    return () => { ro.disconnect(); chart.remove() }
  }, [])

  // 기간 변경 시 데이터 업데이트
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current || !chartRef.current) return

    const days = PERIOD_OPTIONS.find(p => p.label === period)!.days
    const sliced = MOCK_CANDLES.slice(-days)

    candleSeriesRef.current.setData(sliced.map(c => ({ time: c.time, open: c.open, high: c.high, low: c.low, close: c.close })))
    volumeSeriesRef.current.setData(sliced.map(c => ({
      time: c.time, value: c.volume,
      color: c.close >= c.open ? 'rgba(239,68,68,0.3)' : 'rgba(59,130,246,0.3)',
    })))

    chartRef.current.timeScale().fitContent()
    setIsZoomed(false)
  }, [period])

  // 드래그 선택 → 확대
  const handleMouseDown = (e: React.MouseEvent) => {
    if (!wrapperRef.current) return
    const rect = wrapperRef.current.getBoundingClientRect()
    dragRef.current = { active: true, startX: e.clientX - rect.left }
    if (selectionRef.current) {
      selectionRef.current.style.left = `${dragRef.current.startX}px`
      selectionRef.current.style.width = '0px'
      selectionRef.current.style.display = 'block'
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragRef.current.active || !wrapperRef.current || !selectionRef.current) return
    const rect = wrapperRef.current.getBoundingClientRect()
    const currentX = e.clientX - rect.left
    const left = Math.min(dragRef.current.startX, currentX)
    const width = Math.abs(currentX - dragRef.current.startX)
    selectionRef.current.style.left = `${left}px`
    selectionRef.current.style.width = `${width}px`
  }

  const handleMouseUp = (e: React.MouseEvent) => {
    if (!dragRef.current.active || !chartRef.current || !wrapperRef.current) return
    if (selectionRef.current) selectionRef.current.style.display = 'none'

    const rect = wrapperRef.current.getBoundingClientRect()
    const endX = e.clientX - rect.left
    const width = Math.abs(endX - dragRef.current.startX)
    dragRef.current.active = false

    // 최소 20px 드래그 시에만 줌
    if (width < 20) return

    const ts = chartRef.current.timeScale()
    const left = Math.min(dragRef.current.startX, endX)
    const right = left + width
    const from = ts.coordinateToLogical(left)
    const to = ts.coordinateToLogical(right)
    if (from !== null && to !== null) {
      ts.setVisibleLogicalRange({ from, to })
      setIsZoomed(true)
    }
  }

  const handleReset = () => {
    chartRef.current?.timeScale().fitContent()
    setIsZoomed(false)
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* 기간 선택 + 리셋 */}
      <div className="flex items-center justify-between px-4 pt-3 pb-1">
        <div className="flex items-center gap-1">
          {PERIOD_OPTIONS.map(p => (
            <button
              key={p.label}
              onClick={() => setPeriod(p.label)}
              className={`px-2.5 py-1 text-xs rounded-md transition ${
                period === p.label
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          {isZoomed && (
            <button onClick={handleReset} className="text-xs text-blue-400 hover:text-blue-300 transition">
              전체 보기
            </button>
          )}
          <span className="text-[10px] text-gray-600">드래그로 확대 · 휠로 줌</span>
        </div>
      </div>
      <div
        ref={wrapperRef}
        className="relative px-4 pb-4 cursor-crosshair"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => {
          dragRef.current.active = false
          if (selectionRef.current) selectionRef.current.style.display = 'none'
        }}
      >
        <div ref={containerRef} />
        {/* 드래그 선택 오버레이 */}
        <div
          ref={selectionRef}
          className="absolute top-0 bottom-4 bg-blue-500/10 border-l border-r border-blue-500/40 pointer-events-none"
          style={{ display: 'none' }}
        />
      </div>
    </div>
  )
}

// ─── 상세 뷰 ─────────────────────────────────────────────

function DetailView({ stock, onBack }: { stock: Stock; onBack: () => void }) {
  const [ruleEditing, setRuleEditing] = useState<number | null>(null)

  return (
    <>
      {/* 뒤로가기 + 종목 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="flex items-center gap-1 text-sm text-gray-400 hover:text-white transition"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
            목록
          </button>
          <div className="h-5 w-px bg-gray-700" />
          <div>
            <h1 className="text-xl font-bold">{stock.name}</h1>
            <span className="text-xs text-gray-500">{stock.symbol}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold font-mono">{stock.price.toLocaleString()}</div>
          <div className={`text-sm font-mono ${stock.change >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
            {stock.change >= 0 ? '+' : ''}{stock.change}%
          </div>
        </div>
      </div>

      {/* 가격 차트 — Lightweight Charts */}
      <section className="mb-6">
        <h3 className="text-sm font-medium text-gray-400 mb-3">가격 추이</h3>
        <PriceChart />
      </section>

      {/* 지표 그리드 */}
      <section className="mb-6">
        <h3 className="text-sm font-medium text-gray-400 mb-3">기술적 지표</h3>
        <div className="grid grid-cols-4 gap-3">
          {MOCK_INDICATORS.map(ind => (
            <div key={ind.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="text-xs text-gray-500 mb-1">{ind.label}</div>
              <div className={`font-mono text-lg font-medium ${
                ind.status === 'low' ? 'text-blue-400' :
                ind.status === 'neg' ? 'text-red-400' :
                ind.status === 'high' ? 'text-yellow-400' : ''
              }`}>{ind.value}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 시장 컨텍스트 */}
      <section className="mb-6">
        <h3 className="text-sm font-medium text-gray-400 mb-3">시장 컨텍스트</h3>
        <div className="grid grid-cols-4 gap-3">
          {MOCK_CONTEXT.map(c => (
            <div key={c.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="text-xs text-gray-500 mb-1">{c.label}</div>
              <div className="font-mono text-lg font-medium">{c.value}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 규칙 */}
      <section className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-400">규칙</h3>
          <button className="text-xs text-blue-400 hover:text-blue-300 font-medium transition">+ 규칙 추가</button>
        </div>
        <div className="space-y-2">
          {MOCK_RULES.map(r => (
            <div key={r.id}>
              <div className={`flex items-center justify-between p-4 bg-gray-900 border border-gray-800 rounded-xl transition ${!r.active ? 'opacity-50' : ''} ${ruleEditing === r.id ? 'rounded-b-none border-b-0' : ''}`}>
                <div className="flex items-center gap-3">
                  {/* ON/OFF 토글 */}
                  <button
                    className={`relative w-9 h-5 rounded-full transition-colors ${r.active ? 'bg-green-500' : 'bg-gray-600'}`}
                    title={r.active ? '활성' : '비활성'}
                  >
                    <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${r.active ? 'left-[18px]' : 'left-0.5'}`} />
                  </button>
                  <span className="text-sm">{r.desc}</span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setRuleEditing(ruleEditing === r.id ? null : r.id)}
                    className="text-xs text-gray-400 hover:text-blue-400 transition"
                  >
                    {ruleEditing === r.id ? '닫기' : '수정'}
                  </button>
                  <button className="text-xs text-gray-400 hover:text-red-400 transition">삭제</button>
                </div>
              </div>

              {/* 인라인 규칙 편집 */}
              {ruleEditing === r.id && (
                <div className="bg-gray-800/50 border border-gray-800 border-t-0 rounded-b-xl p-4">
                  <div className="flex flex-wrap gap-2 mb-3">
                    <select className="bg-gray-700 rounded-lg px-3 py-1.5 text-sm border-0 focus:outline-none focus:ring-1 focus:ring-blue-500">
                      <option>RSI(14)</option><option>RSI(21)</option><option>MACD</option><option>거래량배수</option>
                    </select>
                    <select className="bg-gray-700 rounded-lg px-3 py-1.5 text-sm border-0 focus:outline-none focus:ring-1 focus:ring-blue-500">
                      <option>≤</option><option>≥</option><option>=</option>
                    </select>
                    <input className="bg-gray-700 rounded-lg px-3 py-1.5 text-sm w-20 border-0 focus:outline-none focus:ring-1 focus:ring-blue-500" defaultValue="30" />
                    <span className="text-gray-500 self-center">→</span>
                    <select className="bg-gray-700 rounded-lg px-3 py-1.5 text-sm border-0 focus:outline-none focus:ring-1 focus:ring-blue-500">
                      <option>매수</option><option>매도</option>
                    </select>
                    <input className="bg-gray-700 rounded-lg px-3 py-1.5 text-sm w-16 border-0 focus:outline-none focus:ring-1 focus:ring-blue-500" defaultValue="10" />
                    <span className="text-sm text-gray-500 self-center">주</span>
                    <select className="bg-gray-700 rounded-lg px-3 py-1.5 text-sm border-0 focus:outline-none focus:ring-1 focus:ring-blue-500">
                      <option>시장가</option><option>지정가</option>
                    </select>
                  </div>
                  <div className="flex gap-2">
                    <button className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition">저장</button>
                    <button onClick={() => setRuleEditing(null)} className="px-4 py-1.5 text-sm text-gray-400 hover:text-white transition">취소</button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* 이 종목 최근 체결 */}
      <section>
        <h3 className="text-sm font-medium text-gray-400 mb-3">이 종목 체결 내역</h3>
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 border-b border-gray-800">
                <th className="text-left px-4 py-2.5 font-medium">시각</th>
                <th className="text-left px-4 py-2.5 font-medium">방향</th>
                <th className="text-right px-4 py-2.5 font-medium">수량</th>
                <th className="text-right px-4 py-2.5 font-medium">가격</th>
                <th className="text-right px-4 py-2.5 font-medium">상태</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_TRADES.filter(t => t.symbol === stock.name).map((t, i) => (
                <tr key={i} className="border-t border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-2.5 font-mono text-gray-400">{t.time}</td>
                  <td className={`px-4 py-2.5 ${t.side === '매수' ? 'text-red-400' : 'text-blue-400'}`}>{t.side}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{t.qty}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{t.price.toLocaleString()}</td>
                  <td className="px-4 py-2.5 text-right">
                    {t.ok ? (
                      <span className="text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded">체결</span>
                    ) : (
                      <span className="text-xs text-red-400 bg-red-400/10 px-2 py-0.5 rounded">거부</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* 하단 액션 */}
      <div className="mt-6 flex gap-3">
        <button className="text-sm text-gray-500 hover:text-red-400 transition">관심 종목 해제</button>
      </div>
    </>
  )
}
