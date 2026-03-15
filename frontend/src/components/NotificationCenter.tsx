import { useState } from 'react'
import { useNotifStore } from '../hooks/useLocalBridgeWS'

export default function NotificationCenter() {
  const [open, setOpen] = useState(false)
  const { items, unread, markAllRead } = useNotifStore()

  const handleOpen = () => {
    setOpen(o => !o)
    if (!open) markAllRead()
  }

  return (
    <div className="relative">
      <button onClick={handleOpen} className="relative p-1 rounded hover:bg-gray-800">
        <svg className={`w-5 h-5 ${unread > 0 ? 'text-orange-400' : 'text-gray-400'}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
        </svg>
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-orange-500 text-white text-xs flex items-center justify-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-2 w-80 bg-gray-800 border border-gray-700 rounded-xl shadow-xl z-50 overflow-hidden">
            <div className="px-4 py-2 border-b border-gray-700 flex justify-between items-center">
              <span className="text-sm font-semibold text-gray-200">알림</span>
              <button onClick={() => setOpen(false)} className="text-xs text-gray-400 hover:text-gray-200">닫기</button>
            </div>
            <ul className="max-h-72 overflow-y-auto divide-y divide-gray-700/50">
              {items.length === 0 ? (
                <li className="px-4 py-6 text-center text-sm text-gray-500">알림 없음</li>
              ) : items.map(n => (
                <li key={n.id} className={`px-4 py-3 text-sm ${n.type === 'error' ? 'bg-red-900/20' : n.type === 'success' ? 'bg-green-900/20' : ''}`}>
                  <div className="text-gray-200">{n.message}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{n.ts}</div>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  )
}
