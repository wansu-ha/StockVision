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
  const [portConflict, setPortConflict] = useState(false)
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
            setPortConflict(true)
            setRetries(n => n + 1)
            return
          }
          setPortConflict(false)
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
      setDeeplinkFailed(true)
    }, 2000)
  }

  const wasInstalled = localStorage.getItem(SV_INSTALLED_KEY) === '1'

  const STEPS: { phase: Phase; label: string; desc: string }[] = [
    { phase: 'download', label: '다운로드', desc: '설치 파일을 다운로드하세요.' },
    { phase: 'run', label: '서버 실행', desc: '프로그램을 실행하면 백그라운드에서 시작됩니다.' },
    { phase: 'connect', label: '연결 확인', desc: '서버가 감지되면 자동으로 다음 단계로 이동합니다.' },
  ]

  return (
    <div className="space-y-4">
      {/* 맥락 설명 */}
      <div className="flex gap-2.5 bg-blue-900/15 border border-blue-800/40 rounded-lg px-3.5 py-2.5">
        <span className="text-base shrink-0 mt-0.5">🔒</span>
        <p className="text-xs text-blue-300/90 leading-relaxed">
          주문은 이 PC에서만 실행됩니다. API 키와 비밀번호는 외부로 전송되지 않습니다.
        </p>
      </div>

      {/* 3단계 진행 상태 */}
      <div className="space-y-2">
        {STEPS.map((s, i) => {
          const done = connected || STEPS.findIndex(x => x.phase === phase) > i
          const active = s.phase === phase && !connected
          return (
            <div key={s.phase} className={`flex items-center gap-3 p-3 rounded-lg transition ${
              done ? 'bg-green-900/20 border border-green-800/50' :
              active ? 'bg-indigo-900/15 border border-indigo-700/40' :
              'bg-gray-800/30 border border-gray-800/50 opacity-50'
            }`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                done ? 'bg-green-600 text-white' :
                active ? 'bg-indigo-600 text-white animate-pulse' :
                'bg-gray-800 text-gray-500'
              }`}>
                {done ? '✓' : i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className={`text-sm font-medium ${
                  done ? 'text-green-400' : active ? 'text-gray-100' : 'text-gray-500'
                }`}>
                  {done ? `${s.label} 완료` : active && s.phase === 'run' ? `${s.label} 중...` : s.label}
                </div>
                <div className="text-xs text-gray-400 mt-0.5">{s.desc}</div>
              </div>
              {active && s.phase !== 'download' && (
                <div className="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin shrink-0" />
              )}
            </div>
          )
        })}
      </div>

      {/* 액션 버튼 */}
      {!connected && (
        <div className="flex items-center gap-3">
          {wasInstalled && (
            <button
              onClick={handleDeeplink}
              className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 transition"
            >
              서버 시작
            </button>
          )}
          <a
            href="https://github.com/wansu-ha/StockVision/releases/latest/download/StockVision-Bridge-Setup.exe"
            onClick={() => setPhase('run')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-500 transition"
          >
            StockVision 설치파일 다운로드
          </a>
        </div>
      )}

      {/* 연결 상태 */}
      <div className="flex items-center gap-2 text-sm">
        <span className={`inline-block w-3 h-3 rounded-full ${connected ? 'bg-green-500' : 'bg-yellow-400 animate-pulse'}`} />
        <span className={connected ? 'text-green-400 font-medium' : 'text-gray-400'}>
          {connected ? '연결됨!' : `연결 대기 중... (${retries}회 시도)`}
        </span>
      </div>

      {/* 포트 충돌 감지 */}
      {!connected && portConflict && (
        <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-3 text-xs text-red-400 space-y-1">
          <p className="font-medium">포트 충돌 감지</p>
          <p className="text-red-400/80">
            포트 4020이 다른 프로그램에서 사용 중입니다. 해당 프로그램을 종료하거나, 방화벽 설정을 확인하세요.
          </p>
        </div>
      )}

      {/* 딥링크 실패 → 수동 실행 안내 */}
      {!connected && deeplinkFailed && wasInstalled && !portConflict && (
        <div className="bg-orange-900/20 border border-orange-800/50 rounded-lg p-3 text-xs text-orange-400 space-y-2">
          <p className="font-medium">⚠ 자동 시작이 안 되나요?</p>
          <p className="text-orange-400/80">
            프로그램을 직접 실행해 주세요:
          </p>
          <code className="block bg-gray-900/60 rounded px-2.5 py-1.5 text-[11px] text-orange-300/90 break-all select-all">
            %LOCALAPPDATA%\StockVision\stockvision-local.exe
          </code>
          <p className="text-orange-400/60">
            또는 시작 메뉴에서 &quot;StockVision&quot;을 검색하세요.
          </p>
        </div>
      )}

      {/* 재시도 3회 이상 */}
      {!connected && retries >= 3 && !portConflict && (
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
