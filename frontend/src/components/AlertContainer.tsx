/** 토스트 알림 컨테이너 (우상단) */
import { useAlertStore } from '../stores/alertStore'
import type { AlertType } from '../types/ui'

const bgMap: Record<AlertType, string> = {
  info: 'bg-blue-500',
  success: 'bg-green-500',
  warning: 'bg-yellow-500',
  error: 'bg-red-500',
}

export default function AlertContainer() {
  const alerts = useAlertStore((s) => s.alerts)
  const remove = useAlertStore((s) => s.remove)

  if (alerts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      {alerts.map((a) => (
        <div
          key={a.id}
          className={`${bgMap[a.type]} text-white px-4 py-3 rounded-xl shadow-lg flex items-center justify-between gap-3 animate-slide-in`}
        >
          <span className="text-sm">{a.message}</span>
          <button
            onClick={() => remove(a.id)}
            className="text-white/70 hover:text-white text-lg leading-none"
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  )
}
