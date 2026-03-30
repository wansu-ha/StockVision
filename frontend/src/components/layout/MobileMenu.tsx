import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

interface Props {
  open: boolean
  onClose: () => void
}

const menuItems = [
  { label: '대시보드', path: '/' },
  { label: '전략', path: '/strategies' },
  { label: '백테스트', path: '/backtest' },
  { label: '관심종목', path: '/stocks' },
  { label: '실행 로그', path: '/logs' },
  { label: '설정', path: '/settings' },
]

export default function MobileMenu({ open, onClose }: Props) {
  const { pathname } = useLocation()
  const { email, logout } = useAuth()

  const isActive = (path: string) => {
    if (path === '/') return pathname === '/'
    return pathname.startsWith(path)
  }

  const initial = (email?.[0] ?? 'U').toUpperCase()

  return (
    <div
      className={`fixed inset-0 bg-[#0a0a1a] z-[100] flex flex-col transition-transform duration-300 will-change-transform ${
        open ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800">
        <span className="font-bold text-indigo-500 text-[15px]">StockVision</span>
        <button onClick={onClose} className="text-white text-lg">✕</button>
      </div>

      {/* Account card */}
      <div className="mx-4 mt-4 mb-2 bg-gray-800 border border-gray-700 rounded-xl p-3.5 flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-gray-700 flex items-center justify-center font-bold text-sm border border-gray-600 shrink-0">
          {initial}
        </div>
        <div className="min-w-0">
          <div className="text-[13px] font-semibold truncate">{email ?? '사용자'}</div>
          <div className="text-[11px] text-gray-500 mt-0.5">Free Plan</div>
        </div>
      </div>

      {/* Menu items — no icons, text only */}
      <div className="flex-1 flex flex-col justify-center px-6">
        {menuItems.map((item, i) => (
          <Link
            key={item.path}
            to={item.path}
            onClick={onClose}
            className={`py-3.5 text-xl ${i < menuItems.length - 1 ? 'border-b border-gray-800' : ''} ${
              isActive(item.path) ? 'text-white font-semibold' : 'text-gray-400'
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>

      {/* Logout */}
      <div className="px-6 py-4 border-t border-gray-800">
        <button onClick={() => { logout(); onClose() }} className="text-red-400 text-sm">로그아웃</button>
      </div>
    </div>
  )
}
