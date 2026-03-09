/**
 * Proto B — 3컬럼 워크벤치 디자인
 * (codex/frontend-admin-design 브랜치 기반)
 *
 * 구조: 좌측(종목+체결) | 중앙(종목 상세) | 우측(규칙+엔진)
 */
import { useState } from 'react'

const MOCK_STOCKS = [
  { symbol: '005930', name: '삼성전자', price: 72400, change: 1.2, rules: 3, status: '●' },
  { symbol: '000660', name: 'SK하이닉스', price: 185000, change: -0.5, rules: 1, status: '●' },
  { symbol: '035420', name: 'NAVER', price: 215000, change: 0.8, rules: 2, status: '●' },
  { symbol: '005380', name: '현대차', price: 245000, change: -1.1, rules: 0, status: '○' },
  { symbol: '051910', name: 'LG화학', price: 320000, change: 2.3, rules: 1, status: '●' },
]

const MOCK_TRADES = [
  { time: '10:30', symbol: '삼성전자', side: '매수', qty: 10, price: 72400, ok: true },
  { time: '10:15', symbol: 'SK하이닉스', side: '매도', qty: 5, price: 185000, ok: true },
  { time: '09:45', symbol: '삼성전자', side: '매수', qty: 10, price: 72800, ok: false },
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

export default function ProtoB() {
  const [selected, setSelected] = useState(MOCK_STOCKS[0])
  const [ruleDrawerOpen, setRuleDrawerOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      {/* 상단 바 */}
      <header className="h-12 bg-gray-900 border-b border-gray-800 flex items-center px-4 gap-4 shrink-0">
        <div className="flex items-center gap-2 font-bold">
          <span className="text-blue-400">StockVision</span>
          <span className="w-2.5 h-2.5 rounded-full bg-green-400" title="거래 가능" />
        </div>
        <div className="flex-1 max-w-sm mx-auto">
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1 text-sm placeholder-gray-500 focus:outline-none focus:border-blue-500"
            placeholder="🔍 종목 검색..."
          />
        </div>
        <div className="flex items-center gap-3 text-sm">
          <button className="text-gray-400 hover:text-white">🔔</button>
          <span className="text-gray-300">홍길동 ▼</span>
        </div>
      </header>

      {/* 3컬럼 워크벤치 */}
      <div className="flex flex-1 overflow-hidden">
        {/* 좌측: 관심종목 + 체결 피드 */}
        <div className="w-72 bg-gray-900/50 border-r border-gray-800 flex flex-col shrink-0">
          {/* 관심종목 */}
          <div className="flex-1 overflow-y-auto">
            <div className="px-3 py-2 text-xs text-gray-500 font-medium uppercase tracking-wider border-b border-gray-800 flex justify-between items-center">
              <span>관심 종목</span>
              <button className="text-blue-400 hover:text-blue-300">+</button>
            </div>
            {MOCK_STOCKS.map(s => (
              <div
                key={s.symbol}
                onClick={() => setSelected(s)}
                className={`px-3 py-2.5 cursor-pointer border-b border-gray-800/50 hover:bg-gray-800/50 transition ${
                  selected.symbol === s.symbol ? 'bg-blue-900/20 border-l-2 border-l-blue-500' : ''
                }`}
              >
                <div className="flex justify-between items-baseline">
                  <span className="font-medium text-sm">{s.name}</span>
                  <span className="font-mono text-sm">{s.price.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center mt-0.5">
                  <span className="text-xs text-gray-500">{s.symbol}</span>
                  <div className="flex items-center gap-2">
                    {s.rules > 0 && <span className="text-xs text-green-400">{s.rules}규칙</span>}
                    <span className={`text-xs font-mono ${s.change >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                      {s.change >= 0 ? '+' : ''}{s.change}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* 체결 피드 */}
          <div className="border-t border-gray-800">
            <div className="px-3 py-2 text-xs text-gray-500 font-medium uppercase tracking-wider">
              최근 체결
            </div>
            <div className="overflow-y-auto max-h-40">
              {MOCK_TRADES.map((t, i) => (
                <div key={i} className="px-3 py-1.5 text-xs flex justify-between border-b border-gray-800/30">
                  <div className="flex gap-2">
                    <span className="text-gray-500 font-mono">{t.time}</span>
                    <span>{t.symbol}</span>
                    <span className={t.side === '매수' ? 'text-red-400' : 'text-blue-400'}>{t.side}</span>
                  </div>
                  <div className="flex gap-1">
                    <span className="font-mono">{t.qty}주</span>
                    {!t.ok && <span className="text-red-400">✕</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 중앙: 종목 상세 */}
        <div className="flex-1 overflow-y-auto p-5">
          {/* 종목 헤더 */}
          <div className="flex items-center justify-between mb-5">
            <div>
              <h1 className="text-2xl font-bold">{selected.name}</h1>
              <span className="text-sm text-gray-500">{selected.symbol}</span>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold font-mono">{selected.price.toLocaleString()}</div>
              <div className={`text-lg ${selected.change >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                {selected.change >= 0 ? '+' : ''}{selected.change}%
              </div>
            </div>
          </div>

          {/* 지표 그리드 */}
          <div className="mb-5">
            <h3 className="text-sm text-gray-400 font-medium mb-2">기술적 지표</h3>
            <div className="grid grid-cols-4 gap-2">
              {MOCK_INDICATORS.map(ind => (
                <div key={ind.label} className="bg-gray-900 border border-gray-800 rounded-lg p-3">
                  <div className="text-xs text-gray-500 mb-1">{ind.label}</div>
                  <div className={`font-mono font-medium ${
                    ind.status === 'low' ? 'text-blue-400' :
                    ind.status === 'neg' ? 'text-red-400' :
                    ind.status === 'high' ? 'text-yellow-400' : ''
                  }`}>{ind.value}</div>
                </div>
              ))}
            </div>
          </div>

          {/* 규칙 요약 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm text-gray-400 font-medium">연결된 규칙</h3>
              <button
                onClick={() => setRuleDrawerOpen(true)}
                className="text-xs text-blue-400 hover:underline"
              >
                + 규칙 추가
              </button>
            </div>
            <div className="space-y-2">
              {MOCK_RULES.map(r => (
                <div key={r.id} className={`flex items-center justify-between p-3 bg-gray-900 border border-gray-800 rounded-lg ${!r.active ? 'opacity-50' : ''}`}>
                  <div className="flex items-center gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full ${r.active ? 'bg-green-400' : 'bg-gray-600'}`} />
                    {r.desc}
                  </div>
                  <button onClick={() => setRuleDrawerOpen(true)} className="text-xs text-gray-400 hover:text-blue-400">수정</button>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4">
            <button className="text-sm text-gray-500 hover:text-red-400">⊖ 관심 종목 해제</button>
          </div>
        </div>

        {/* 우측: 규칙 빌더 / 시장 컨텍스트 / 엔진 */}
        <div className="w-72 bg-gray-900/50 border-l border-gray-800 flex flex-col shrink-0 overflow-y-auto">
          {/* 엔진 제어 */}
          <div className="p-3 border-b border-gray-800">
            <div className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-2">엔진</div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                <span className="text-sm text-green-400">실행 중</span>
              </div>
              <div className="flex gap-1">
                <button className="px-2 py-1 text-xs bg-red-900/50 text-red-400 rounded border border-red-800 hover:bg-red-900">중지</button>
                <button className="px-2 py-1 text-xs bg-gray-800 text-gray-400 rounded border border-gray-700 hover:bg-gray-700">Kill</button>
              </div>
            </div>
            <div className="mt-2 text-xs text-gray-500">오늘 체결: <span className="text-white">5건</span></div>
          </div>

          {/* 시장 컨텍스트 */}
          <div className="p-3 border-b border-gray-800">
            <div className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-2">시장 컨텍스트</div>
            <div className="space-y-1.5">
              {MOCK_CONTEXT.map(c => (
                <div key={c.label} className="flex justify-between text-xs">
                  <span className="text-gray-400">{c.label}</span>
                  <span className="font-mono">{c.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 상태 진단 */}
          <div className="p-3 border-b border-gray-800">
            <div className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-2">연결 상태</div>
            <div className="space-y-1.5 text-xs">
              {[
                ['클라우드 인증', true],
                ['로컬 브리지', true],
                ['브로커 연결', true],
                ['Kill Switch', false],
              ].map(([label, ok]) => (
                <div key={String(label)} className="flex justify-between">
                  <span className="text-gray-400">{String(label)}</span>
                  <span className={ok ? 'text-green-400' : 'text-gray-600'}>{ok ? '정상' : 'OFF'}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 규칙 드로어 */}
          {ruleDrawerOpen && (
            <div className="p-3 border-b border-gray-800 bg-gray-800/30">
              <div className="flex items-center justify-between mb-3">
                <div className="text-xs text-gray-500 font-medium uppercase tracking-wider">규칙 편집</div>
                <button onClick={() => setRuleDrawerOpen(false)} className="text-xs text-gray-500 hover:text-white">✕</button>
              </div>
              <div className="space-y-2 mb-3">
                <div className="bg-gray-800 rounded p-2 text-xs">
                  <div className="flex items-center gap-1">
                    <select className="bg-gray-700 rounded px-1.5 py-0.5 text-xs border-0"><option>RSI(14)</option></select>
                    <select className="bg-gray-700 rounded px-1.5 py-0.5 text-xs border-0"><option>≤</option></select>
                    <input className="bg-gray-700 rounded px-1.5 py-0.5 w-12 text-xs border-0" defaultValue="30" />
                  </div>
                </div>
                <div className="text-center text-[10px] text-gray-600">AND</div>
                <div className="bg-gray-800 rounded p-2 text-xs">
                  <div className="flex items-center gap-1">
                    <select className="bg-gray-700 rounded px-1.5 py-0.5 text-xs border-0"><option>거래량배수</option></select>
                    <select className="bg-gray-700 rounded px-1.5 py-0.5 text-xs border-0"><option>≥</option></select>
                    <input className="bg-gray-700 rounded px-1.5 py-0.5 w-12 text-xs border-0" defaultValue="2.0" />
                  </div>
                </div>
                <button className="text-[10px] text-blue-400">+ 조건</button>
              </div>
              <div className="bg-gray-800 rounded p-2 text-xs mb-3">
                <div className="flex items-center gap-2">
                  <select className="bg-gray-700 rounded px-1.5 py-0.5 text-xs border-0"><option>매수</option></select>
                  <input className="bg-gray-700 rounded px-1.5 py-0.5 w-10 text-xs border-0" defaultValue="10" />
                  <span className="text-gray-500">주</span>
                  <select className="bg-gray-700 rounded px-1.5 py-0.5 text-xs border-0"><option>시장가</option></select>
                </div>
              </div>
              <div className="flex gap-1">
                <button className="flex-1 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-500">저장</button>
                <button onClick={() => setRuleDrawerOpen(false)} className="px-3 py-1.5 text-xs text-gray-400 hover:text-white">취소</button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 디자인 라벨 */}
      <div className="fixed bottom-4 left-4 bg-purple-600 text-white text-xs px-3 py-1.5 rounded-full shadow-lg z-50">
        Proto B — 3컬럼 워크벤치
      </div>
    </div>
  )
}
