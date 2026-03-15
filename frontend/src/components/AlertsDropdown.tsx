/** AlertsDropdown — OpsPanel 경고 배지 + 드롭다운 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useNotifStore } from '../hooks/useLocalBridgeWS'

function SeverityIcon({ severity }: { severity?: string }) {
  const color = severity === 'critical' ? 'text-red-400' : 'text-yellow-400'
  const pulse = severity === 'critical' ? 'animate-pulse' : ''
  return (
    <span className={`${color} shrink-0`}>
      <svg className={`w-3.5 h-3.5 ${pulse}`} viewBox="0 0 24 24" fill="currentColor">
        <rect x="6" y="14" width="12" height="4" rx="1" />
        <path d="M8 14 A4 4 0 0 1 16 14" />
        <circle cx="12" cy="11" r="2.5" opacity="0.6" />
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
        <svg className={`w-4 h-4 ${hasCritical ? 'text-red-500 animate-pulse' : unreadAlerts > 0 ? 'text-red-400' : 'text-gray-500'}`}
          viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="14" width="12" height="4" rx="1" />
          <path d="M8 14 A4 4 0 0 1 16 14" />
          <circle cx="12" cy="11" r="2.5" opacity="0.6" />
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
