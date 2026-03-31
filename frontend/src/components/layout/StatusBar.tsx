import { useAccountStatus } from '../../hooks/useAccountStatus'
import { useMarketContext } from '../../hooks/useMarketContext'

interface StatusItem {
  label: string
  ok: boolean
}

export default function StatusBar() {
  const { engineRunning, brokerConnected, isLoading } = useAccountStatus()
  const { context } = useMarketContext()

  const now = new Date()
  const dayOfWeek = now.getDay()
  const isWeekend = dayOfWeek === 0 || dayOfWeek === 6
  const isHoliday = isWeekend || context?.is_holiday === true
  const hhmm = now.getHours() * 100 + now.getMinutes()
  const marketPhase = isHoliday ? '휴장' : hhmm >= 900 && hhmm < 1530 ? '장중' : hhmm < 900 ? '장전' : '장후'

  const items: StatusItem[] = [
    { label: '로컬', ok: !isLoading },
    { label: '브로커', ok: brokerConnected },
    { label: '클라우드', ok: true },
    { label: '엔진', ok: engineRunning },
  ]

  return (
    <div className="sticky bottom-0 z-40 bg-[#16162a] border-t border-[#2d2d4a] px-8 py-1 flex justify-between text-[11px] text-gray-200">
      <div className="flex gap-3.5">
        {items.map((item) => (
          <span key={item.label} className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${item.ok ? 'bg-green-500' : 'bg-gray-500'}`} />
            {item.label}
          </span>
        ))}
      </div>
      <span className="text-gray-500">{marketPhase}</span>
    </div>
  )
}
