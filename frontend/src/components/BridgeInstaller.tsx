import { useEffect, useRef, useState } from 'react'

const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'
const WS_URL = LOCAL_URL.replace(/^http/, 'ws') + '/ws'

interface Props {
  onConnected: () => void
}

export default function BridgeInstaller({ onConnected }: Props) {
  const [connected, setConnected] = useState(false)
  const onConnectedRef = useRef(onConnected)
  onConnectedRef.current = onConnected

  useEffect(() => {
    if (connected) return
    let currentWs: WebSocket | null = null

    const check = () => {
      currentWs = new WebSocket(WS_URL)
      const ws = currentWs
      ws.onopen = () => {
        ws.close()
        setConnected(true)
        onConnectedRef.current()
      }
      ws.onerror = () => ws.close()
    }
    check()
    const id = setInterval(check, 5000)
    return () => {
      clearInterval(id)
      currentWs?.close()
    }
  }, [connected])

  return (
    <div className="space-y-5">
      <ol className="space-y-3 text-sm text-gray-700 list-decimal list-inside">
        <li>아래 버튼으로 설치 파일을 다운로드하세요.</li>
        <li>설치 후 실행하면 자동으로 백그라운드에서 시작됩니다.</li>
        <li>연결이 감지되면 자동으로 다음 단계로 이동합니다.</li>
      </ol>

      <a
        href="#"
        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition"
      >
        StockVision v1.0.0 다운로드 (.exe)
      </a>

      <div className="flex items-center gap-2 text-sm">
        <span className={`inline-block w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-red-400 animate-pulse'}`} />
        <span className={connected ? 'text-green-700 font-medium' : 'text-gray-500'}>
          {connected ? '연결됨! 다음 단계로 이동합니다...' : '연결 대기 중 (5초마다 자동 확인)'}
        </span>
      </div>
    </div>
  )
}
