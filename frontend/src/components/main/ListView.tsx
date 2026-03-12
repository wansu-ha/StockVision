/**
 * ListView — 계좌 요약 + 탭 + 종목 행(아코디언) + 미체결 + 체결
 * 디자인 개선: (A) indigo, (B) 하단 발광+첫행확장, (C) 계좌요약 2행, (E) 아코디언 애니메이션, (F) aria
 */
import { useState, useEffect } from 'react'

// ─── Types ───

export interface Stock {
  symbol: string
  name: string
  price: number
  change: number
  rules: number
  lastTrade: string
}

export interface Trade {
  time: string
  symbol: string
  side: '매수' | '매도'
  qty: number
  price: number
  ok: boolean
}

export interface PendingOrder {
  time: string
  symbol: string
  side: '매수' | '매도'
  qty: number
  price: number
  type: string
}

export interface AccountInfo {
  broker: string
  accountNo: string
  totalValue: number
  availableCash: number
  dailyReturn: number
  dailyPnl?: number
  holdings: { symbol: string; name: string; qty: number; avgPrice: number; currentPrice: number }[]
}

export interface MarketStatus {
  status: '장전' | '장중' | '장후' | '휴장'
  openTime: string
  closeTime: string
}

const FIRST_VISIT_KEY = 'sv_accordion_seen'

// ─── Component ───

interface ListViewProps {
  tab: 'my' | 'watch'
  setTab: (t: 'my' | 'watch') => void
  stocks: Stock[]
  account: AccountInfo
  isMock: boolean | null
  marketStatus: MarketStatus
  trades: Trade[]
  pendingOrders: PendingOrder[]
  onDetail: (stock: Stock) => void
  engineRunning: boolean
  brokerConnected: boolean
  onStrategyToggle: () => void
  strategyLoading: boolean
}

export default function ListView({
  tab, setTab, stocks, account, isMock, marketStatus, trades, pendingOrders, onDetail,
  engineRunning, brokerConnected, onStrategyToggle, strategyLoading,
}: ListViewProps) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null)
  const [hintVisible, setHintVisible] = useState(false)

  // (B) 첫 방문 시 첫 행 자동 확장
  useEffect(() => {
    const seen = localStorage.getItem(FIRST_VISIT_KEY)
    if (!seen && stocks.length > 0) {
      setExpandedRow(stocks[0].symbol)
      setHintVisible(true)
    }
  }, [stocks])

  const handleRowClick = (stock: Stock) => {
    // 첫 방문 힌트 제거
    if (hintVisible) {
      setHintVisible(false)
      localStorage.setItem(FIRST_VISIT_KEY, '1')
    }
    setExpandedRow(expandedRow === stock.symbol ? null : stock.symbol)
  }

  return (
    <>
      {/* (C) 계좌 요약 — 반응형 */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-3 sm:p-4 mb-4 sm:mb-5">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-baseline gap-2 sm:gap-3 min-w-0">
            <div className="text-xl sm:text-2xl font-mono font-bold truncate">{account.totalValue.toLocaleString()}<span className="text-xs sm:text-sm text-gray-500 ml-1">원</span></div>
            <span className={`text-xs sm:text-sm font-mono font-medium px-1.5 sm:px-2 py-0.5 rounded-full shrink-0 ${
              account.dailyReturn >= 0
                ? 'text-red-400 bg-red-400/10'
                : 'text-blue-400 bg-blue-400/10'
            }`}>
              {account.dailyPnl != null && account.dailyPnl !== 0 && (
                <>{account.dailyPnl >= 0 ? '+' : ''}{account.dailyPnl.toLocaleString('ko-KR')}원 </>
              )}
              ({account.dailyReturn >= 0 ? '+' : ''}{account.dailyReturn}%)
            </span>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <span className={`w-2 h-2 rounded-full ${marketStatus.status === '장중' ? 'bg-green-400' : 'bg-gray-600'}`} />
            <span className={`text-xs ${marketStatus.status === '장중' ? 'text-green-400' : 'text-gray-500'}`}>{marketStatus.status}</span>
          </div>
        </div>
        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-x-3 sm:gap-x-4 gap-y-1 text-xs sm:text-sm text-gray-400">
            <span>주문가능 <span className="font-mono text-gray-300">{account.availableCash.toLocaleString()}</span></span>
            <span className="text-gray-700 hidden sm:inline">│</span>
            <span>보유 <span className="font-mono text-gray-300">{account.holdings.length}종목</span></span>
            <span className="text-gray-700 hidden sm:inline">│</span>
            <span className="hidden sm:inline">{account.broker}{isMock !== null && <span className={`ml-1 text-[10px] font-bold px-1.5 py-0.5 rounded ${isMock ? 'bg-yellow-900/50 text-yellow-400' : 'bg-red-900/50 text-red-400'}`}>{isMock ? '모의' : '실전'}</span>} <span className="text-gray-600">{account.accountNo}</span></span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span
              className={`w-2 h-2 rounded-full ${engineRunning ? 'bg-green-400' : brokerConnected ? 'bg-yellow-400' : 'bg-gray-600'}`}
              title={engineRunning ? '자동매매 중' : brokerConnected ? '브로커 연결됨' : '미연결'}
            />
            {brokerConnected ? (
              <button
                onClick={onStrategyToggle}
                disabled={strategyLoading}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition ${
                  engineRunning
                    ? 'bg-red-900/50 text-red-400 border border-red-800 hover:bg-red-900'
                    : 'bg-indigo-600 text-white hover:bg-indigo-500'
                } disabled:opacity-40 disabled:cursor-not-allowed`}
              >
                {strategyLoading ? '...' : engineRunning ? '중지' : '전략 실행'}
              </button>
            ) : (
              <span className="text-[11px] text-gray-500">설정에서 키 등록</span>
            )}
          </div>
        </div>
      </div>

      {/* 종목 리스트 — 탭을 카드 내부에 배치 */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden mb-5">
        {/* 탭 */}
        <div className="flex gap-1 px-4 pt-3 pb-2 border-b border-gray-800/50" role="tablist">
          {([['my', '내 종목'], ['watch', '관심 종목']] as const).map(([key, label]) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`px-3 py-1 text-sm rounded-md transition ${
                tab === key
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {stocks.length === 0 ? (
          /* (D) 빈 상태 — Step 2에서 실제 빈 데이터 시 표시 */
          <div className="py-12 text-center">
            <div className="text-gray-600 text-sm mb-2">
              {tab === 'my' ? '규칙이 설정된 종목이 없습니다' : '관심 종목이 없습니다'}
            </div>
            <button className="text-xs text-indigo-400 hover:text-indigo-300 transition">종목 검색하기</button>
          </div>
        ) : (
          stocks.map((s, i) => {
            const isExpanded = expandedRow === s.symbol
            return (
              <div key={s.symbol} className={`flex group ${i > 0 ? 'border-t border-gray-800/50' : ''} ${isExpanded ? 'bg-gray-800/20' : ''}`}>
                {/* 왼쪽 액센트 바 */}
                <div className={`w-1 shrink-0 rounded-l transition-colors ${isExpanded ? 'bg-indigo-500' : 'group-hover:bg-indigo-500/40'}`} />

                {/* 왼쪽: 행 + 확장 영역 */}
                <div className="flex-1 min-w-0 relative">
                  {/* 기본 행 */}
                  <div
                    onClick={() => handleRowClick(s)}
                    onDoubleClick={() => onDetail(s)}
                    role="button"
                    aria-expanded={isExpanded}
                    aria-controls={`accordion-${s.symbol}`}
                    className="flex items-center px-3 sm:px-4 py-3 sm:py-3.5 cursor-pointer transition-colors hover:bg-gray-800/60"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm sm:text-base truncate">{s.name}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{s.symbol}</div>
                    </div>
                    <div className="text-right mr-2 sm:mr-6">
                      <div className="font-mono font-medium text-sm sm:text-base">{s.price.toLocaleString()}</div>
                      <div className={`text-xs font-mono ${s.change >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                        {s.change >= 0 ? '+' : ''}{s.change}%
                      </div>
                    </div>
                    <div className="w-20 text-right mr-6 hidden md:block">
                      {s.rules > 0 ? (
                        <span className="text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded-full">
                          {s.rules}개 규칙
                        </span>
                      ) : (
                        <span className="text-xs text-gray-600">—</span>
                      )}
                    </div>
                    <div className="w-28 text-right text-xs text-gray-500 hidden lg:block">
                      {s.lastTrade || '—'}
                    </div>
                  </div>

                  {/* (E) 아코디언 확장 영역 — max-height transition */}
                  <div
                    id={`accordion-${s.symbol}`}
                    className={`overflow-hidden transition-all duration-150 ${isExpanded ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}
                  >
                    <div className="px-4 pb-4">
                      {/* 첫 방문 힌트 */}
                      {hintVisible && i === 0 && (
                        <div className="text-xs text-gray-500 mb-2">행을 탭하면 지표를 볼 수 있습니다</div>
                      )}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
                        <div className="bg-gray-900 border border-gray-700/50 rounded-lg px-3 py-2.5">
                          <div className="text-[11px] text-gray-400">가격</div>
                          <div className="font-mono text-sm font-medium">{s.price.toLocaleString()}</div>
                        </div>
                        <div className="bg-gray-900 border border-gray-700/50 rounded-lg px-3 py-2.5">
                          <div className="text-[11px] text-gray-400">등락</div>
                          <div className={`font-mono text-sm font-medium ${s.change >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                            {s.change >= 0 ? '+' : ''}{s.change}%
                          </div>
                        </div>
                        <div className="bg-gray-900 border border-gray-700/50 rounded-lg px-3 py-2.5">
                          <div className="text-[11px] text-gray-400">규칙</div>
                          <div className="font-mono text-sm font-medium">{s.rules}개</div>
                        </div>
                        <div className="bg-gray-900 border border-gray-700/50 rounded-lg px-3 py-2.5">
                          <div className="text-[11px] text-gray-400">최근 체결</div>
                          <div className="font-mono text-sm font-medium text-gray-400">{s.lastTrade || '—'}</div>
                        </div>
                      </div>
                      <div className="mt-3 text-right">
                        <button
                          onClick={(e) => { e.stopPropagation(); onDetail(s) }}
                          className="text-xs text-indigo-400 hover:text-indigo-300 transition"
                        >
                          상세 보기 →
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* (B) 하단 발광 — 호버 시 */}
                  <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-indigo-500/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>

                {/* 오른쪽: 상세 보기 버튼 */}
                <button
                  onClick={(e) => { e.stopPropagation(); onDetail(s) }}
                  aria-label={`${s.name} 상세 보기`}
                  className={`w-11 shrink-0 flex items-center justify-center border-l border-gray-800/50 transition-colors cursor-pointer ${
                    isExpanded
                      ? 'bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20'
                      : 'bg-gray-800/30 text-gray-600 hover:text-indigo-400 hover:bg-gray-800/50'
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                </button>
              </div>
            )
          })
        )}
      </div>

      {/* 미체결 주문 */}
      {pendingOrders.length > 0 && (
        <div className="mb-5">
          <h3 className="text-sm font-medium text-gray-400 mb-2">미체결 주문 <span className="text-yellow-400">{pendingOrders.length}</span></h3>
          <div className="bg-gray-900 border border-yellow-800/30 rounded-xl overflow-x-auto">
            <table className="w-full text-sm min-w-[500px]" aria-label="미체결 주문">
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
                {pendingOrders.map((o, i) => (
                  <tr key={i} className="border-t border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                    <td className="px-4 py-2.5 font-mono text-gray-400">{o.time}</td>
                    <td className="px-4 py-2.5 font-medium">{o.symbol}</td>
                    <td className={`px-4 py-2.5 ${o.side === '매수' ? 'text-red-400' : 'text-blue-400'}`}>{o.side}</td>
                    <td className="px-4 py-2.5 text-right font-mono">{o.qty}</td>
                    <td className="px-4 py-2.5 text-right font-mono">{o.price.toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-right text-xs text-gray-400">{o.type}</td>
                    <td className="px-4 py-2.5 text-right">
                      <button className="text-xs text-gray-600 cursor-not-allowed" disabled title="준비 중">취소</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 체결 내역 */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 mb-2">체결 내역</h3>
        {trades.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800 rounded-xl py-8 text-center text-sm text-gray-600">
            체결 내역이 없습니다
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
            <table className="w-full text-sm min-w-[500px]" aria-label="체결 내역">
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
                {trades.map((t, i) => (
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
        )}
      </div>
    </>
  )
}
