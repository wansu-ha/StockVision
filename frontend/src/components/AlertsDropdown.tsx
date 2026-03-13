/** AlertsDropdown — OpsPanel 경고 배지 + 드롭다운 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useNotifStore } from '../hooks/useLocalBridgeWS'

function SeverityIcon({ severity }: { severity?: string }) {
  if (severity === 'critical') {
    return (
      <span className="text-red-400 shrink-0">
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
      </span>
    )
  }
  return (
    <span className="text-yellow-400 shrink-0">
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
    </span>
  )
}

export default function AlertsDropdown() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const { items, unreadAlerts, markAllRead } = useNotifStore()

  // severity 있는 항목만
  const alerts = items.filter(n => n.severity)
  const hasCritical = alerts.some(n => n.severity === 'critical' && !n.read)

  const handleOpen = () => {
    setOpen(o => !o)
    if (!open) markAllRead()
  }

  return (
    <div className="relative">
      <button
        onClick={handleOpen}
        className="relative flex items-center gap-1 text-xs text-gray-400 hover:text-gray-200 transition"
        aria-label="경고 알림"
      >
        <svg className={`w-4 h-4 ${hasCritical ? 'text-red-400' : unreadAlerts > 0 ? 'text-yellow-400' : 'text-gray-500'}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
        </svg>
        {unreadAlerts > 0 && (
          <span className={`absolute -top-1 -right-1 text-[10px] font-bold px-1 rounded-full leading-tight
            ${hasCritical ? 'bg-red-500 text-white' : 'bg-yellow-500 text-gray-900'}`}>
            {unreadAlerts > 9 ? '9+' : unreadAlerts}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute top-full right-0 mt-2 z-20 bg-gray-800 border border-gray-700 rounded-xl shadow-xl w-72">
            <div className="px-3 py-2 border-b border-gray-700 flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-300">경고</span>
              <button
                onClick={() => { navigate('/logs?tab=alerts'); setOpen(false) }}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                전체 보기
              </button>
            </div>

            <div className="max-h-64 overflow-y-auto">
              {alerts.length === 0 ? (
                <div className="px-3 py-4 text-xs text-gray-500 text-center">경고 없음</div>
              ) : (
                alerts.slice(0, 10).map(alert => (
                  <div key={alert.id} className={`px-3 py-2.5 border-b border-gray-700/50 last:border-0 ${!alert.read ? 'bg-gray-750/50' : ''}`}>
                    <div className="flex items-start gap-2">
                      <SeverityIcon severity={alert.severity} />
                      <div className="flex-1 min-w-0">
                        <div className="text-xs text-gray-200 font-medium truncate">{alert.title ?? alert.alertType}</div>
                        <div className="text-xs text-gray-400 mt-0.5 leading-snug">{alert.message}</div>
                      </div>
                      <span className="text-[10px] text-gray-600 shrink-0">{alert.ts}</span>
                    </div>
                    {alert.action && (
                      <button
                        onClick={() => { navigate(alert.action!.route); setOpen(false) }}
                        className="mt-1.5 text-[10px] text-blue-400 hover:text-blue-300 ml-5"
                      >
                        {alert.action.label} →
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
