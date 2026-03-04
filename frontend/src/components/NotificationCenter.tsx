import { useState } from 'react'
import { BellIcon } from '@heroicons/react/24/outline'
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
      <button onClick={handleOpen} className="relative p-1 rounded hover:bg-gray-100">
        <BellIcon className="w-5 h-5 text-gray-600" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-red-500 text-white text-xs flex items-center justify-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border z-50 overflow-hidden">
          <div className="px-4 py-2 border-b flex justify-between items-center">
            <span className="text-sm font-semibold">알림</span>
            <button onClick={() => setOpen(false)} className="text-xs text-gray-400 hover:text-gray-600">닫기</button>
          </div>
          <ul className="max-h-72 overflow-y-auto divide-y">
            {items.length === 0 ? (
              <li className="px-4 py-6 text-center text-sm text-gray-400">알림 없음</li>
            ) : items.map(n => (
              <li key={n.id} className={`px-4 py-3 text-sm ${n.type === 'error' ? 'bg-red-50' : n.type === 'success' ? 'bg-green-50' : ''}`}>
                <div className="text-gray-800">{n.message}</div>
                <div className="text-xs text-gray-400 mt-0.5">{n.ts}</div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
