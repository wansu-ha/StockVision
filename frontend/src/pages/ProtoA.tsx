/**
 * Proto A — 리스트 + 슬라이드 패널 디자인
 * (claude/design-frontend-Kd0vV 브랜치 기반)
 *
 * 구조: 관심종목 테이블(메인) → 행 클릭 → 우측 슬라이드 패널 → 규칙 모달
 */
import { useState } from 'react'

// Mock 데이터
const MOCK_STOCKS = [
  { symbol: '005930', name: '삼성전자', price: 72400, change: 1.2, rules: 3, lastTrade: '매수 @72,400' },
  { symbol: '000660', name: 'SK하이닉스', price: 185000, change: -0.5, rules: 1, lastTrade: '—' },
  { symbol: '035420', name: 'NAVER', price: 215000, change: 0.8, rules: 2, lastTrade: '매도 @215,500' },
  { symbol: '005380', name: '현대차', price: 245000, change: -1.1, rules: 0, lastTrade: '—' },
  { symbol: '051910', name: 'LG화학', price: 320000, change: 2.3, rules: 1, lastTrade: '매수 @318,000' },
]

const MOCK_TRADES = [
  { time: '10:30:15', symbol: '삼성전자', side: '매수', qty: 10, price: '72,400', status: '성공' },
  { time: '10:15:02', symbol: 'SK하이닉스', side: '매도', qty: 5, price: '185,000', status: '성공' },
  { time: '09:45:33', symbol: '삼성전자', side: '매수', qty: 10, price: '72,800', status: '거부' },
  { time: '09:30:00', symbol: 'NAVER', side: '매도', qty: 3, price: '215,500', status: '성공' },
]

const MOCK_RULES = [
  { id: 1, desc: 'RSI ≤ 30 → 매수 10주', active: true },
  { id: 2, desc: 'RSI ≥ 70 → 매도 전량', active: true },
  { id: 3, desc: '거래량 급증 → 매수 5주', active: false },
]

const MOCK_INDICATORS = { rsi14: 34, macd: -0.5, volRatio: 1.8, bollUpper: 74200, bollLower: 70600 }

export default function ProtoA() {
  const [selected, setSelected] = useState<typeof MOCK_STOCKS[0] | null>(null)
  const [showRuleModal, setShowRuleModal] = useState(false)

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* 상단 바 */}
      <header className="h-14 bg-gray-900 border-b border-gray-800 flex items-center px-4 gap-4">
        <div className="flex items-center gap-2 font-bold text-lg">
          <span className="text-blue-400">StockVision</span>
          <span className="flex gap-1 ml-1">
            <span className="w-2.5 h-2.5 rounded-full bg-green-400" title="클라우드: 연결됨" />
            <span className="w-2.5 h-2.5 rounded-full bg-green-400" title="로컬: 연결됨" />
            <span className="w-2.5 h-2.5 rounded-full bg-green-400" title="KIS: 연결됨" />
          </span>
        </div>
        <div className="flex-1 max-w-md mx-auto">
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-1.5 text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
            placeholder="🔍 종목 검색..."
          />
        </div>
        <div className="flex items-center gap-3">
          <button className="text-gray-400 hover:text-white relative">
            🔔<span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full text-[8px] flex items-center justify-center">2</span>
          </button>
          <span className="text-sm text-gray-300">홍길동 ▼</span>
        </div>
      </header>

      <div className="flex h-[calc(100vh-56px)]">
        {/* 메인 콘텐츠 */}
        <main className={`flex-1 p-6 overflow-y-auto transition-all ${selected ? 'mr-96' : ''}`}>
          {/* 엔진 상태 바 */}
          <div className="flex items-center justify-between mb-6 bg-gray-900 rounded-lg p-4 border border-gray-800">
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-400">엔진 상태:</span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                <span className="text-green-400 font-medium">실행 중</span>
              </span>
              <button className="px-3 py-1 text-xs bg-red-900/50 text-red-400 rounded border border-red-800 hover:bg-red-900">
                중지
              </button>
              <button className="px-3 py-1 text-xs bg-gray-800 text-gray-400 rounded border border-gray-700 hover:bg-gray-700">
                Kill Switch
              </button>
            </div>
            <div className="text-sm text-gray-400">오늘 체결: <span className="text-white font-medium">5건</span></div>
          </div>

          {/* 관심종목 테이블 */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold">내 종목</h2>
              <button className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-500">
                + 종목 추가
              </button>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-400 border-b border-gray-800">
                    <th className="text-left py-3 px-4 font-medium">종목</th>
                    <th className="text-right py-3 px-4 font-medium">현재가</th>
                    <th className="text-right py-3 px-4 font-medium">변동률</th>
                    <th className="text-center py-3 px-4 font-medium">규칙</th>
                    <th className="text-left py-3 px-4 font-medium">최근 체결</th>
                  </tr>
                </thead>
                <tbody>
                  {MOCK_STOCKS.map(s => (
                    <tr
                      key={s.symbol}
                      onClick={() => setSelected(s)}
                      className={`cursor-pointer border-b border-gray-800/50 hover:bg-gray-800/50 transition ${
                        selected?.symbol === s.symbol ? 'bg-blue-900/20 border-l-2 border-l-blue-500' : ''
                      }`}
                    >
                      <td className="py-3 px-4">
                        <div className="font-medium">{s.name}</div>
                        <div className="text-xs text-gray-500">{s.symbol}</div>
                      </td>
                      <td className="text-right py-3 px-4 font-mono">{s.price.toLocaleString()}</td>
                      <td className={`text-right py-3 px-4 font-mono ${s.change >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                        {s.change >= 0 ? '+' : ''}{s.change}%
                      </td>
                      <td className="text-center py-3 px-4">
                        {s.rules > 0 ? (
                          <span className="px-2 py-0.5 text-xs bg-green-900/50 text-green-400 rounded">{s.rules}개 활성</span>
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-gray-400 text-xs">{s.lastTrade}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 최근 체결 피드 */}
          <div>
            <h2 className="text-lg font-semibold mb-3">최근 체결</h2>
            <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-400 border-b border-gray-800">
                    <th className="text-left py-2 px-4 font-medium">시각</th>
                    <th className="text-left py-2 px-4 font-medium">종목</th>
                    <th className="text-center py-2 px-4 font-medium">방향</th>
                    <th className="text-right py-2 px-4 font-medium">수량</th>
                    <th className="text-right py-2 px-4 font-medium">가격</th>
                    <th className="text-center py-2 px-4 font-medium">상태</th>
                  </tr>
                </thead>
                <tbody>
                  {MOCK_TRADES.map((t, i) => (
                    <tr key={i} className="border-b border-gray-800/50">
                      <td className="py-2 px-4 font-mono text-gray-400">{t.time}</td>
                      <td className="py-2 px-4">{t.symbol}</td>
                      <td className={`text-center py-2 px-4 ${t.side === '매수' ? 'text-red-400' : 'text-blue-400'}`}>{t.side}</td>
                      <td className="text-right py-2 px-4 font-mono">{t.qty}</td>
                      <td className="text-right py-2 px-4 font-mono">{t.price}</td>
                      <td className="text-center py-2 px-4">
                        <span className={`px-2 py-0.5 text-xs rounded ${t.status === '성공' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'}`}>
                          {t.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </main>

        {/* 우측 슬라이드 패널 */}
        {selected && (
          <aside className="w-96 fixed right-0 top-14 bottom-0 bg-gray-900 border-l border-gray-800 overflow-y-auto shadow-2xl">
            <div className="p-5">
              {/* 종목 헤더 */}
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-xl font-bold">{selected.name}</h2>
                  <span className="text-sm text-gray-500">{selected.symbol}</span>
                </div>
                <button onClick={() => setSelected(null)} className="text-gray-500 hover:text-white text-xl">✕</button>
              </div>
              <div className="mb-6">
                <span className="text-3xl font-bold font-mono">{selected.price.toLocaleString()}</span>
                <span className={`ml-2 text-lg ${selected.change >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                  {selected.change >= 0 ? '+' : ''}{selected.change}%
                </span>
              </div>

              {/* 현재 지표 */}
              <div className="mb-6">
                <h3 className="text-sm font-medium text-gray-400 mb-3">현재 지표</h3>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries({ 'RSI(14)': MOCK_INDICATORS.rsi14, 'MACD': MOCK_INDICATORS.macd, '거래량배수': `${MOCK_INDICATORS.volRatio}x`, '볼린저 상단': MOCK_INDICATORS.bollUpper.toLocaleString() }).map(([k, v]) => (
                    <div key={k} className="bg-gray-800 rounded p-2.5">
                      <div className="text-xs text-gray-500">{k}</div>
                      <div className="font-mono font-medium">{v}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 규칙 목록 */}
              <div className="mb-6">
                <h3 className="text-sm font-medium text-gray-400 mb-3">규칙 ({MOCK_RULES.length}개)</h3>
                <div className="space-y-2">
                  {MOCK_RULES.map(r => (
                    <div key={r.id} className={`flex items-center justify-between p-3 rounded-lg border ${r.active ? 'bg-gray-800 border-gray-700' : 'bg-gray-800/50 border-gray-800 opacity-60'}`}>
                      <div className="flex items-center gap-2">
                        <span>{r.active ? '✅' : '⏸'}</span>
                        <span className="text-sm">{r.desc}</span>
                      </div>
                      <div className="flex gap-1">
                        <button onClick={() => setShowRuleModal(true)} className="text-xs text-blue-400 hover:underline">수정</button>
                        <span className="text-gray-700">|</span>
                        <button className="text-xs text-red-400 hover:underline">삭제</button>
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => setShowRuleModal(true)}
                  className="w-full mt-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 text-sm font-medium"
                >
                  + 규칙 추가
                </button>
              </div>

              <button className="text-sm text-gray-500 hover:text-red-400">관심 종목 해제</button>
            </div>
          </aside>
        )}
      </div>

      {/* 규칙 편집 모달 */}
      {showRuleModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowRuleModal(false)}>
          <div className="bg-gray-900 border border-gray-700 rounded-xl w-[520px] shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="p-5 border-b border-gray-800">
              <h3 className="font-semibold text-lg">규칙 편집 — {selected?.name}</h3>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-2">조건</h4>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 bg-gray-800 rounded-lg p-3">
                    <select className="bg-gray-700 text-sm rounded px-2 py-1 border-0"><option>RSI(14)</option></select>
                    <select className="bg-gray-700 text-sm rounded px-2 py-1 border-0"><option>≤</option></select>
                    <input className="bg-gray-700 text-sm rounded px-2 py-1 w-20 border-0" defaultValue="30" />
                    <button className="text-red-400 text-sm ml-auto">✕</button>
                  </div>
                  <div className="text-center text-xs text-gray-500">AND</div>
                  <div className="flex items-center gap-2 bg-gray-800 rounded-lg p-3">
                    <select className="bg-gray-700 text-sm rounded px-2 py-1 border-0"><option>거래량배수</option></select>
                    <select className="bg-gray-700 text-sm rounded px-2 py-1 border-0"><option>≥</option></select>
                    <input className="bg-gray-700 text-sm rounded px-2 py-1 w-20 border-0" defaultValue="2.0" />
                    <button className="text-red-400 text-sm ml-auto">✕</button>
                  </div>
                </div>
                <button className="text-sm text-blue-400 mt-2 hover:underline">+ 조건 추가</button>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-2">실행</h4>
                <div className="flex items-center gap-3 bg-gray-800 rounded-lg p-3">
                  <span className="text-sm text-gray-400">방향:</span>
                  <select className="bg-gray-700 text-sm rounded px-2 py-1 border-0"><option>매수</option><option>매도</option></select>
                  <span className="text-sm text-gray-400">수량:</span>
                  <input className="bg-gray-700 text-sm rounded px-2 py-1 w-16 border-0" defaultValue="10" />
                  <span className="text-sm text-gray-400">주</span>
                  <span className="text-sm text-gray-400 ml-2">유형:</span>
                  <select className="bg-gray-700 text-sm rounded px-2 py-1 border-0"><option>시장가</option><option>지정가</option></select>
                </div>
              </div>
            </div>
            <div className="p-5 border-t border-gray-800 flex justify-end gap-2">
              <button onClick={() => setShowRuleModal(false)} className="px-4 py-2 text-sm text-gray-400 hover:text-white">취소</button>
              <button className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-500">저장</button>
              <button className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-500">저장 + 활성화</button>
            </div>
          </div>
        </div>
      )}

      {/* 디자인 라벨 */}
      <div className="fixed bottom-4 left-4 bg-blue-600 text-white text-xs px-3 py-1.5 rounded-full shadow-lg z-50">
        Proto A — 리스트 + 슬라이드 패널
      </div>
    </div>
  )
}
