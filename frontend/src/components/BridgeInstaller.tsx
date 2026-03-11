import { useEffect, useRef, useState } from 'react'

const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'
const SV_INSTALLED_KEY = 'sv_installed'

interface Props {
  onConnected: () => void
}

type Phase = 'download' | 'run' | 'connect'

export default function BridgeInstaller({ onConnected }: Props) {
  const [connected, setConnected] = useState(false)
  const [phase, setPhase] = useState<Phase>('download')
  const [retries, setRetries] = useState(0)
  const [deeplinkFailed, setDeeplinkFailed] = useState(false)
  const onConnectedRef = useRef(onConnected)
  onConnectedRef.current = onConnected

  // HTTP health 폴링
  useEffect(() => {
    if (connected) return

    const check = () =>
      fetch(`${LOCAL_URL}/health`, { method: 'GET' })
        .then(r => r.ok ? r.json() : Promise.reject())
        .then(data => {
          if (data.app !== 'stockvision') {
            // 다른 서버가 포트를 사용 중
            setRetries(n => n + 1)
            return
          }
          setConnected(true)
          setPhase('connect')
          localStorage.setItem(SV_INSTALLED_KEY, '1')
          onConnectedRef.current()
        })
        .catch(() => setRetries(n => n + 1))

    check()
    const id = setInterval(check, 5000)
    return () => clearInterval(id)
  }, [connected])

  // 딥링크 시도 후 2초 내 미응답 → 미설치 판단
  const handleDeeplink = () => {
    window.location.href = 'stockvision://launch'
    setPhase('run')
    setTimeout(() => {
      // 2초 후에도 connected가 아니면 미설치 가능성
      setDeeplinkFailed(true)
    }, 2000)
  }

  const wasInstalled = localStorage.getItem(SV_INSTALLED_KEY) === '1'

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

      {/* 액션 버튼 */}
      {!connected && (
        <div className="flex items-center gap-3">
          {/* 이전 연결 기록이 있으면 딥링크 시작 버튼 우선 */}
          {wasInstalled && (
            <button
              onClick={handleDeeplink}
              className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 transition"
            >
              서버 시작
            </button>
          )}
          <a
            href="#"
            onClick={() => setPhase('run')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-500 transition"
          >
            StockVision 다운로드 (.exe)
          </a>
        </div>
      )}

      {/* 상태 */}
      <div className="flex items-center gap-2 text-sm">
        <span className={`inline-block w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-yellow-400 animate-pulse'}`} />
        <span className={connected ? 'text-green-400 font-medium' : 'text-gray-400'}>
          {connected ? '연결됨!' : `연결 대기 중... (${retries}회 시도)`}
        </span>
      </div>

      {/* 딥링크 실패 → 미설치 안내 */}
      {!connected && deeplinkFailed && wasInstalled && (
        <div className="bg-orange-900/20 border border-orange-800/50 rounded-lg p-3 text-xs text-orange-400 space-y-1">
          <p className="font-medium">서버가 응답하지 않습니다</p>
          <p className="text-orange-400/80">프로그램이 설치되어 있지 않거나, 실행에 실패했을 수 있습니다. 다운로드 버튼으로 재설치해 보세요.</p>
        </div>
      )}

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
