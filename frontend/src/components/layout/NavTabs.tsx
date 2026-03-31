import { Link, useLocation } from 'react-router-dom'

const tabs = [
  { label: '대시보드', path: '/' },
  { label: '전략', path: '/strategies' },
  { label: '백테스트', path: '/backtest' },
  { label: '관심종목', path: '/stocks' },
  { label: '실행 로그', path: '/logs' },
]

export default function NavTabs() {
  const { pathname } = useLocation()

  const isActive = (path: string) => {
    if (path === '/') return pathname === '/'
    return pathname.startsWith(path) || (path === '/strategies' && pathname.startsWith('/strategy'))
  }

  return (
    <div className="bg-transparent hidden md:block">
      <div className="max-w-[1100px] mx-auto flex gap-1 px-8">
        {tabs.map((tab) => (
          <Link
            key={tab.path}
            to={tab.path}
            className={`px-2 py-2 text-[13px] border-b-2 transition-colors ${
              isActive(tab.path)
                ? 'text-white font-semibold border-indigo-500'
                : 'text-gray-500 border-transparent hover:text-gray-300'
            }`}
          >
            {tab.label}
          </Link>
        ))}
      </div>
    </div>
  )
}
