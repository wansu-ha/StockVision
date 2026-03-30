import { Link } from 'react-router-dom'
import { useNotifStore } from '../../hooks/useLocalBridgeWS'
import AccountDropdown from './AccountDropdown'

interface Props {
  onMenuOpen: () => void
}

export default function UnifiedHeader({ onMenuOpen }: Props) {
  const unreadCount = useNotifStore((s) => s.unread)

  return (
    <header className="sticky top-0 z-50 bg-[#111827] border-b border-[#1f2937]">
      <div className="max-w-[1100px] mx-auto flex items-center justify-between px-8 py-3 gap-4">
        <Link to="/" className="font-bold text-indigo-500 text-[17px] shrink-0 no-underline">
          StockVision
        </Link>

        {/* 검색바 — 모바일 숨김 */}
        <input
          type="text"
          placeholder="종목 검색..."
          className="hidden md:block flex-1 max-w-[400px] bg-[#1f2937] border border-[#374151] rounded-lg px-3.5 py-1.5 text-[13px] text-gray-200 placeholder:text-gray-500 outline-none focus:border-indigo-500 transition-colors"
          readOnly
        />

        <div className="flex items-center gap-3.5">
          {/* 알림 */}
          <button className="relative text-gray-400 hover:text-gray-200 transition-colors">
            <span className="text-base">🔔</span>
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1.5 bg-red-500 text-white text-[8px] w-[15px] h-[15px] rounded-full flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

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
