/**
 * Header — 로고 + 신호등 + 검색 + 알림 + 톱니바퀴
 * 드롭다운(알림/톱니바퀴)은 Header 내부에서만 사용하므로 분리하지 않음.
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useNotifStore } from '../../hooks/useLocalBridgeWS'
import { localEngine } from '../../services/localClient'
import { cloudStocks } from '../../services/cloudClient'
import type { StockMasterItem } from '../../services/cloudClient'
import type { Stock } from './ListView'

interface HeaderProps {
  onStockSelect?: (stock: Stock) => void
  engineRunning?: boolean
  brokerConnected?: boolean
}

export default function Header({ onStockSelect, engineRunning = false, brokerConnected = false }: HeaderProps) {
  const { email, logout } = useAuth()
  const navigate = useNavigate()
  const notifications = useNotifStore(s => s.items)
  const unreadCount = useNotifStore(s => s.unread)
  const markAllRead = useNotifStore(s => s.markAllRead)
  const [gearOpen, setGearOpen] = useState(false)
  const [notiOpen, setNotiOpen] = useState(false)
  const [engineConfirm, setEngineConfirm] = useState<'stop' | 'kill' | null>(null)

  // 검색 상태
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<StockMasterItem[]>([])
  const [searchOpen, setSearchOpen] = useState(false)
  const [selectedIdx, setSelectedIdx] = useState(-1)
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const inputRef = useRef<HTMLInputElement>(null)

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 1) { setResults([]); return }
    try {
      const items = await cloudStocks.search(q, 10)
      setResults(items)
      setSelectedIdx(-1)
    } catch { setResults([]) }
  }, [])

  useEffect(() => {
    clearTimeout(searchTimeout.current)
    if (query.length >= 1) {
      searchTimeout.current = setTimeout(() => doSearch(query), 200)
    } else {
      setResults([])
      setSearchOpen(false)
    }
    return () => clearTimeout(searchTimeout.current)
  }, [query, doSearch])

  const handleSelectResult = (item: StockMasterItem) => {
    const stock: Stock = { symbol: item.symbol, name: item.name, price: 0, change: 0, rules: 0, lastTrade: '' }
    onStockSelect?.(stock)
    setQuery('')
    setSearchOpen(false)
    setResults([])
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (!searchOpen || results.length === 0) return
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIdx(i => Math.min(i + 1, results.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIdx(i => Math.max(i - 1, 0)) }
    else if (e.key === 'Enter' && selectedIdx >= 0) { e.preventDefault(); handleSelectResult(results[selectedIdx]) }
    else if (e.key === 'Escape') { setSearchOpen(false); inputRef.current?.blur() }
  }

  const handleEngineAction = async (action: 'stop' | 'kill') => {
    if (action === 'stop' || action === 'kill') {
      await localEngine.stop()
    }
    setEngineConfirm(null)
  }

  return (
    <header className="sticky top-0 z-40 w-full max-w-6xl mx-auto px-3 sm:px-4 pt-3">
      <div className="h-12 flex items-center px-3 sm:px-4 gap-2 sm:gap-4 bg-gray-900 border border-gray-800 rounded-xl">
        {/* 로고 + 신호등 */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="font-bold text-indigo-400">StockVision</span>
          <span
            className={`w-2.5 h-2.5 rounded-full ${engineRunning && brokerConnected ? 'bg-green-400' : brokerConnected ? 'bg-yellow-400' : 'bg-gray-600'}`}
            title={engineRunning ? '엔진 실행 중' : '엔진 정지'}
          />
        </div>

        {/* 검색바 + 오버레이 */}
        <div className="flex-1 max-w-md mx-auto relative min-w-0">
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSearchOpen(true) }}
            onFocus={() => { if (results.length > 0) setSearchOpen(true) }}
            onKeyDown={handleSearchKeyDown}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
            placeholder="종목 검색..."
            role="combobox"
            aria-expanded={searchOpen && results.length > 0}
            aria-autocomplete="list"
            aria-controls="search-results"
          />
          {searchOpen && results.length > 0 && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setSearchOpen(false)} />
              <ul id="search-results" role="listbox" className="absolute top-full mt-1 left-0 right-0 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl z-50 max-h-80 overflow-y-auto">
                {results.map((item, i) => (
                  <li
                    key={item.symbol}
                    role="option"
                    aria-selected={i === selectedIdx}
                    onClick={() => handleSelectResult(item)}
                    className={`px-4 py-2.5 cursor-pointer transition-colors ${
                      i === selectedIdx ? 'bg-indigo-500/20 text-white' : 'hover:bg-gray-700/50'
                    } ${i > 0 ? 'border-t border-gray-700/50' : ''}`}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <span className="text-sm font-medium">{item.name}</span>
                        <span className="text-xs text-gray-500 ml-2">{item.symbol}</span>
                      </div>
                      <span className="text-xs text-gray-600">{item.market}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
          {searchOpen && query.length >= 1 && results.length === 0 && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setSearchOpen(false)} />
              <div className="absolute top-full mt-1 left-0 right-0 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl z-50 px-4 py-4 text-center text-sm text-gray-500">
                검색 결과가 없습니다
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {/* 알림 */}
          <div className="relative">
            <button
              onClick={() => { setNotiOpen(!notiOpen); setGearOpen(false) }}
              className="relative text-gray-400 hover:text-white transition"
              aria-haspopup="true"
              aria-expanded={notiOpen}
              aria-label={`알림 ${unreadCount > 0 ? `${unreadCount}건 미읽음` : ''}`}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
              </svg>
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1.5 bg-red-500 text-[10px] text-white rounded-full w-4 h-4 flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </button>
            {notiOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setNotiOpen(false)} />
                <div className="absolute right-0 top-full mt-2 w-80 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl z-50 overflow-hidden">
                  <div className="px-4 py-2.5 border-b border-gray-700 flex justify-between items-center">
                    <span className="text-sm font-medium">알림</span>
                    <button onClick={markAllRead} className="text-xs text-gray-500 hover:text-gray-300 transition">모두 읽음</button>
                  </div>
                  {notifications.length === 0 ? (
                    <div className="px-4 py-6 text-center text-sm text-gray-600">알림이 없습니다</div>
                  ) : (
                    notifications.slice(0, 10).map(n => (
                      <div key={n.id} className={`px-4 py-3 border-b border-gray-700/50 ${!n.read ? 'bg-indigo-500/5' : ''}`}>
                        <div className="flex justify-between items-start">
                          <span className={`text-sm ${!n.read ? 'text-white' : 'text-gray-400'}`}>{n.message}</span>
                          {!n.read && <span className="w-2 h-2 rounded-full bg-indigo-400 shrink-0 mt-1.5 ml-2" />}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">{n.ts}</div>
                      </div>
                    ))
                  )}
                </div>
              </>
            )}
          </div>

          {/* 톱니바퀴 */}
          <div className="relative">
            <button
              onClick={() => { setGearOpen(!gearOpen); setNotiOpen(false) }}
              className="text-gray-400 hover:text-white transition"
              aria-haspopup="true"
              aria-expanded={gearOpen}
              aria-label="설정"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>

            {gearOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => { setGearOpen(false); setEngineConfirm(null) }} />
                <div className="absolute right-0 top-full mt-2 w-72 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl z-50 overflow-hidden">
                  {/* 사용자 */}
                  <div className="px-4 py-3 border-b border-gray-700">
                    <div className="text-sm font-medium">{email || '사용자'}</div>
                  </div>

                  {/* 엔진 상태 */}
                  <div className="px-4 py-3 border-b border-gray-700">
                    <div className="text-xs text-gray-500 font-medium mb-2">엔진</div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className={`w-2 h-2 rounded-full ${engineRunning ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`} />
                        <span className={`text-sm ${engineRunning ? 'text-green-400' : 'text-gray-500'}`}>
                          {engineRunning ? '실행 중' : '정지'}
                        </span>
                      </div>
                      {engineRunning && (
                        engineConfirm ? (
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs text-gray-400">
                              {engineConfirm === 'stop' ? '중지합니까?' : 'Kill합니까?'}
                            </span>
                            <button
                              onClick={() => handleEngineAction(engineConfirm)}
                              className="px-2 py-1 text-xs bg-red-600 text-white rounded border border-red-500 hover:bg-red-500 transition"
                            >
                              확인
                            </button>
                            <button
                              onClick={() => setEngineConfirm(null)}
                              className="px-2 py-1 text-xs bg-gray-700 text-gray-400 rounded border border-gray-600 hover:bg-gray-600 transition"
                            >
                              취소
                            </button>
                          </div>
                        ) : (
                          <div className="flex gap-1.5">
                            <button
                              onClick={() => setEngineConfirm('stop')}
                              className="px-2 py-1 text-xs bg-red-900/50 text-red-400 rounded border border-red-800 hover:bg-red-900 transition"
                            >
                              중지
                            </button>
                            <button
                              onClick={() => setEngineConfirm('kill')}
                              className="px-2 py-1 text-xs bg-gray-700 text-gray-400 rounded border border-gray-600 hover:bg-gray-600 transition"
                            >
                              Kill
                            </button>
                          </div>
                        )
                      )}
                    </div>
                  </div>

                  {/* 연결 상태 */}
                  <div className="px-4 py-3 border-b border-gray-700">
                    <div className="text-xs text-gray-500 font-medium mb-2">연결 상태</div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-400">브로커</span>
                        <span className={brokerConnected ? 'text-green-400' : 'text-gray-600'}>{brokerConnected ? '연결됨' : '미연결'}</span>
                      </div>
                    </div>
                  </div>

                  {/* 메뉴 */}
                  <div className="py-1">
                    <button
                      onClick={() => { setGearOpen(false); navigate('/settings') }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700/50 transition"
                    >
                      설정
                    </button>
                    <button
                      onClick={() => { setGearOpen(false); logout() }}
                      className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-gray-700/50 transition"
                    >
                      로그아웃
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
