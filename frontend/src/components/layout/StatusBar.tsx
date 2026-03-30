import { useAccountStatus } from '../../hooks/useAccountStatus'

interface StatusItem {
  label: string
  ok: boolean
}

export default function StatusBar() {
  const { engineRunning, brokerConnected, isLoading } = useAccountStatus()

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
      <span className="text-gray-500">장전</span>
    </div>
  )
}
