/** 어드민 레이아웃 (사이드바 + Outlet) */
import { Link, Outlet, useLocation } from 'react-router-dom'

const adminNav = [
  { path: '/admin', label: '대시보드', exact: true },
  { path: '/admin/users', label: '유저 관리' },
  { path: '/admin/stats', label: '접속 통계' },
  { path: '/admin/service-keys', label: '서비스 키' },
  { path: '/admin/templates', label: '템플릿' },
  { path: '/admin/data', label: '시세 모니터링' },
  { path: '/admin/errors', label: '에러 로그' },
]

export default function AdminLayout() {
  const location = useLocation()

  const isActive = (path: string, exact?: boolean) => {
    if (exact) return location.pathname === path
    return location.pathname.startsWith(path)
  }

  return (
    <div className="flex min-h-[calc(100vh-80px)]">
      {/* 사이드바 */}
      <aside className="w-56 bg-white border-r border-gray-200 py-6 px-3 flex-shrink-0">
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider px-3 mb-4">
          관리자
        </h2>
        <nav className="space-y-1">
          {adminNav.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive(item.path, item.exact)
                  ? 'bg-indigo-50 text-indigo-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      {/* 콘텐츠 */}
      <main className="flex-1 p-6 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
