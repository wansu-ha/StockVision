import { useState, useRef, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useNotifStore } from '../../hooks/useLocalBridgeWS'
import { cloudStocks } from '../../services/cloudClient'
import type { StockMasterItem } from '../../services/cloudClient'
import AccountDropdown from './AccountDropdown'

interface Props {
  onMenuOpen: () => void
}

export default function UnifiedHeader({ onMenuOpen }: Props) {
  const navigate = useNavigate()
  const unreadCount = useNotifStore((s) => s.unread)
  const notifications = useNotifStore((s) => s.items)
  const markAllRead = useNotifStore((s) => s.markAllRead)

  // 검색 상태
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<StockMasterItem[]>([])
  const [searchOpen, setSearchOpen] = useState(false)
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  // 알림 패널 상태
  const [notiOpen, setNotiOpen] = useState(false)

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 1) { setResults([]); return }
    try {
      const items = await cloudStocks.search(q, 10)
      setResults(items)
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

  const handleSelectResult = () => {
    setQuery('')
    setSearchOpen(false)
    setResults([])
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-50 bg-[#111827] border-b border-[#1f2937]">
      <div className="max-w-[1100px] mx-auto flex items-center justify-between px-8 py-3 gap-4">
        <Link to="/" className="font-bold text-indigo-500 text-[17px] shrink-0 no-underline">
          StockVision
        </Link>

        {/* 검색바 — 모바일 숨김 */}
        <div className="hidden md:block flex-1 max-w-[400px] relative">
          <input
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSearchOpen(true) }}
            onFocus={() => { if (results.length > 0) setSearchOpen(true) }}
            placeholder="종목 검색..."
            className="w-full bg-[#1f2937] border border-[#374151] rounded-lg px-3.5 py-1.5 text-[13px] text-gray-200 placeholder:text-gray-500 outline-none focus:border-indigo-500 transition-colors"
          />
          {searchOpen && results.length > 0 && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setSearchOpen(false)} />
              <ul className="absolute top-full mt-1 left-0 right-0 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl z-50 max-h-80 overflow-y-auto">
                {results.map((item, i) => (
                  <li
                    key={item.symbol}
                    onClick={handleSelectResult}
                    className={`px-4 py-2.5 cursor-pointer transition-colors hover:bg-gray-700/50 ${i > 0 ? 'border-t border-gray-700/50' : ''}`}
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

        <div className="flex items-center gap-3.5">
          {/* 알림 */}
          <div className="relative">
            <button
              onClick={() => setNotiOpen(!notiOpen)}
              className="relative text-gray-400 hover:text-gray-200 transition-colors"
              aria-label={`알림 ${unreadCount > 0 ? `${unreadCount}건 미읽음` : ''}`}
            >
              <span className="text-base">🔔</span>
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1.5 bg-red-500 text-white text-[8px] w-[15px] h-[15px] rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
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

          {/* 계정 — 데스크탑 */}
          <div className="hidden md:block">
            <AccountDropdown />
          </div>

          {/* 햄버거 — 모바일 */}
          <button
            onClick={onMenuOpen}
            className="md:hidden text-gray-400 hover:text-gray-200 text-xl transition-colors"
          >
            ☰
          </button>
        </div>
      </div>
    </header>
  )
}
