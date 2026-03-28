import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import NotificationCenter from './NotificationCenter'
import TrafficLightStatus from './TrafficLightStatus'
import UserMenu from './UserMenu'
import { useLocalBridgeWS } from '../hooks/useLocalBridgeWS'

interface LayoutProps {
  children: ReactNode
}

const navItems = [
  { path: '/', label: '대시보드' },
  { path: '/strategies', label: '전략' },
  { path: '/backtest', label: '백테스트' },
  { path: '/stocks', label: '관심종목' },
  { path: '/logs', label: '실행 로그' },
]

const Layout = ({ children }: LayoutProps) => {
  const location = useLocation()
  useLocalBridgeWS()

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Navigation */}
      <nav className="bg-gray-900 shadow-lg border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex justify-between h-20">
            <div className="flex items-center">
              <Link to="/" className="flex items-center space-x-3">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-2xl flex items-center justify-center shadow-lg">
                  <span className="text-white font-bold text-xl">S</span>
                </div>
                <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-700 bg-clip-text text-transparent">
                  StockVision
                </span>
              </Link>

              {/* 신호등 */}
              <div className="ml-6">
                <TrafficLightStatus />
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-5 py-2.5 rounded-2xl text-sm font-semibold transition-all duration-200 ${
                    isActive(item.path)
                      ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800'
                  }`}
                >
                  {item.label}
                </Link>
              ))}

              <NotificationCenter />
              <UserMenu />
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main>
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-4 mt-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs text-gray-600">
          <Link to="/legal/terms" className="hover:text-gray-400 transition">이용약관</Link>
          <span>&middot;</span>
          <Link to="/legal/privacy" className="hover:text-gray-400 transition">개인정보처리방침</Link>
          <span>&middot;</span>
          <Link to="/legal/disclaimer" className="hover:text-gray-400 transition">투자 위험 고지</Link>
          <span className="w-full text-center mt-1">&copy; 2026 StockVision</span>
        </div>
      </footer>
    </div>
  )
}

export default Layout
