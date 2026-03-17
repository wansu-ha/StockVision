import { HeartIcon as HeartOutline } from '@heroicons/react/24/outline'
import { HeartIcon as HeartSolid } from '@heroicons/react/24/solid'
import { useRef, useCallback, useEffect } from 'react'

interface HeartToggleProps {
  symbol: string
  isWatchlisted: boolean
  onToggle: (symbol: string, newState: boolean) => void
  size?: number
}

export default function HeartToggle({
  symbol, isWatchlisted, onToggle, size = 20,
}: HeartToggleProps) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => {
    if (timerRef.current) clearTimeout(timerRef.current)
  }, [])

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()

    // 300ms 디바운스: 연속 클릭 무시
    if (timerRef.current) return
    timerRef.current = setTimeout(() => { timerRef.current = null }, 300)

    onToggle(symbol, !isWatchlisted)
  }, [symbol, isWatchlisted, onToggle])

  const Icon = isWatchlisted ? HeartSolid : HeartOutline

  return (
    <button
      onClick={handleClick}
      className="p-1.5 rounded-full transition-transform duration-150
                 hover:scale-110 active:scale-95"
      aria-label={isWatchlisted ? '관심종목 해제' : '관심종목 추가'}
    >
      <Icon
        className={`transition-colors ${
          isWatchlisted ? 'text-red-500' : 'text-gray-500 hover:text-red-400'
        }`}
        style={{ width: size, height: size }}
      />
    </button>
  )
}
