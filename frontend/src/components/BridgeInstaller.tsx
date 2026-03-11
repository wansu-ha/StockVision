import { useEffect, useRef, useState } from 'react'

const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'

interface Props {
  onConnected: () => void
}

type Phase = 'download' | 'run' | 'connect'

export default function BridgeInstaller({ onConnected }: Props) {
  const [connected, setConnected] = useState(false)
  const [phase, setPhase] = useState<Phase>('download')
  const [retries, setRetries] = useState(0)
  const onConnectedRef = useRef(onConnected)
  onConnectedRef.current = onConnected

  // HTTP health 폴링
  useEffect(() => {
    if (connected) return

    const check = () =>
      fetch(`${LOCAL_URL}/health`, { method: 'GET' })
        .then(r => {
          if (r.ok) {
            setConnected(true)
            setPhase('connect')
            onConnectedRef.current()
          } else {
            setRetries(n => n + 1)
          }
        })
        .catch(() => setRetries(n => n + 1))

    check()
    const id = setInterval(check, 5000)
    return () => clearInterval(id)
  }, [connected])

  const STEPS: { phase: Phase; label: string; desc: string }[] = [
    { phase: 'download', label: '다운로드', desc: '아래 버튼으로 설치 파일을 다운로드하세요.' },
    { phase: 'run', label: '실행', desc: '설치 후 실행하면 자동으로 백그라운드에서 시작됩니다.' },
    { phase: 'connect', label: '연결', desc: '연결이 감지되면 자동으로 다음 단계로 이동합니다.' },
  ]

  return (
    <div className="space-y-5">
      {/* 3단계 표시 */}
      <div className="space-y-2">
        {STEPS.map((s, i) => {
          const done = connected || STEPS.findIndex(x => x.phase === phase) > i
          const active = s.phase === phase && !connected
          return (
            <div key={s.phase} className={`flex items-start gap-3 p-3 rounded-lg transition ${
              done ? 'bg-green-900/20 border border-green-800/50' :
              active ? 'bg-gray-800/50 border border-gray-700' :
              'opacity-50'
            }`}>
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                done ? 'bg-green-600 text-white' :
                active ? 'bg-indigo-600 text-white' :
                'bg-gray-800 text-gray-500'
              }`}>
                {done ? '✓' : i + 1}
              </div>
              <div>
                <div className={`text-sm font-medium ${done ? 'text-green-400' : active ? 'text-gray-200' : 'text-gray-500'}`}>
                  {s.label}
                </div>
                <div className="text-xs text-gray-400 mt-0.5">{s.desc}</div>
              </div>
            </div>
          )
        })}
      </div>

      {/* 다운로드 버튼 */}
      {!connected && (
        <a
          href="#"
          onClick={() => setPhase('run')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-500 transition"
        >
          StockVision 다운로드 (.exe)
        </a>
      )}

      {/* 상태 */}
      <div className="flex items-center gap-2 text-sm">
        <span className={`inline-block w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-yellow-400 animate-pulse'}`} />
        <span className={connected ? 'text-green-400 font-medium' : 'text-gray-400'}>
          {connected ? '연결됨!' : `연결 대기 중... (${retries}회 시도)`}
        </span>
      </div>

      {/* 실패 시 체크리스트 */}
      {!connected && retries >= 3 && (
        <div className="bg-yellow-900/20 border border-yellow-800/50 rounded-lg p-3 text-xs text-yellow-400 space-y-1">
          <p className="font-medium">연결이 안 되나요?</p>
          <ul className="list-disc list-inside space-y-0.5 text-yellow-400/80">
            <li>프로그램이 실행 중인지 확인하세요</li>
            <li>방화벽이 포트 4020을 차단하고 있지 않은지 확인하세요</li>
            <li>프로그램을 재시작해 보세요</li>
          </ul>
        </div>
      )}
    </div>
  )
}
