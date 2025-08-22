import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'

interface LayoutProps {
  children: ReactNode
}

const Layout = ({ children }: LayoutProps) => {
  const location = useLocation()

  const isActive = (path: string) => {
    return location.pathname === path
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-lg border-b border-gray-100">
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
            </div>
            
            <div className="flex items-center space-x-2">
              <Link
                to="/"
                className={`px-6 py-3 rounded-2xl text-sm font-semibold transition-all duration-200 ${
                  isActive('/') 
                    ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                대시보드
              </Link>
              <Link
                to="/stocks"
                className={`px-6 py-3 rounded-2xl text-sm font-semibold transition-all duration-200 ${
                  isActive('/stocks') 
                    ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white shadow-lg' 
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                주식 목록
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main>
        {children}
      </main>
    </div>
  )
}

export default Layout
