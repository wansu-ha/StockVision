/** 설정 페이지 — Bridge 상태, API Key 등록, 엔진 제어, 알림 설정, 프로필 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { localEngine, localBroker } from '../services/localClient'
import { cloudAuth } from '../services/cloudClient'
import { useAuth } from '../context/AuthContext'
import { useAlertStore } from '../stores/alertStore'
import { useAccountStatus } from '../hooks/useAccountStatus'
import BrokerKeyForm from '../components/onboarding/BrokerKeyForm'
import AlertSettings from '../components/AlertSettings'
import DeviceManager from '../components/DeviceManager'
import { localConfig } from '../services/localClient'

const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'
const DOWNLOAD_URL = 'https://github.com/wansu-ha/StockVision/releases/latest/download/StockVision-Bridge-Setup.exe'

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}초`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}분`
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return m > 0 ? `${h}시간 ${m}분` : `${h}시간`
}

export default function Settings() {
  const { email, logout } = useAuth()
  const addAlert = useAlertStore((s) => s.add)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { engineRunning, brokerConnected, credentials, isMock } = useAccountStatus()

  // 프로필
  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: cloudAuth.getProfile,
    staleTime: 5 * 60_000,
  })
  const [nickname, setNickname] = useState('')
  const [nickSaving, setNickSaving] = useState(false)
  useEffect(() => {
    if (profile?.nickname) setNickname(profile.nickname)
  }, [profile?.nickname])

  const handleNicknameSave = async () => {
    const trimmed = nickname.trim()
    if (trimmed.length < 2 || trimmed.length > 20) {
      addAlert('닉네임은 2~20자여야 합니다.', 'warning')
      return
    }
    setNickSaving(true)
    try {
      await cloudAuth.updateProfile(trimmed)
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      addAlert('닉네임이 변경되었습니다.', 'success')
    } catch {
      addAlert('닉네임 변경 실패', 'error')
    } finally {
      setNickSaving(false)
    }
  }

  // Bridge 연결 상태 (localReady와 독립적으로 /health 직접 폴링)
  const [bridgeConnected, setBridgeConnected] = useState(false)
  const [bridgeUptime, setBridgeUptime] = useState<number | null>(null)
  const [launchWaiting, setLaunchWaiting] = useState(false)
  const [launchFailed, setLaunchFailed] = useState(false)
  const launchIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    const check = () =>
      fetch(`${LOCAL_URL}/health`, { method: 'GET' })
        .then(r => r.ok ? r.json() : Promise.reject())
        .then(data => {
          if (data.app === 'stockvision') {
            setBridgeConnected(true)
            setBridgeUptime(data.uptime ?? null)
          } else {
            setBridgeConnected(false)
            setBridgeUptime(null)
          }
        })
        .catch(() => {
          setBridgeConnected(false)
          setBridgeUptime(null)
        })

    check()
    const id = setInterval(check, 10_000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    return () => {
      if (launchIntervalRef.current) clearInterval(launchIntervalRef.current)
    }
  }, [])

  const handleLaunch = () => {
    setLaunchFailed(false)
    setLaunchWaiting(true)
    window.location.href = 'stockvision://launch'
    let attempts = 0
    const id = setInterval(() => {
      attempts++
      fetch(`${LOCAL_URL}/health`).then(r => r.ok ? r.json() : Promise.reject())
        .then(data => {
          if (data.app === 'stockvision') {
            clearInterval(id)
            launchIntervalRef.current = null
            setLaunchWaiting(false)
            setBridgeConnected(true)
            setBridgeUptime(data.uptime ?? null)
          }
        })
        .catch(() => {
          if (attempts >= 5) {
            clearInterval(id)
            launchIntervalRef.current = null
            setLaunchWaiting(false)
            setLaunchFailed(true)
          }
        })
    }, 2000)
    launchIntervalRef.current = id
  }

  const hasKeys = !!(credentials?.kiwoom?.app_key || credentials?.kis?.app_key)

  const handleEngineToggle = async () => {
    try {
      if (engineRunning) {
        await localEngine.stop()
        addAlert('엔진이 중지되었습니다', 'info')
      } else {
        await localEngine.start()
        addAlert('엔진이 시작되었습니다', 'success')
      }
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? '엔진 제어 실패. 로컬 서버 연결을 확인하세요.'
      addAlert(msg, 'error')
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* 헤더 */}
      <header className="sticky top-0 z-40 bg-gray-900 border-b border-gray-800">
        <div className="max-w-3xl mx-auto h-12 flex items-center px-3 sm:px-6 gap-4">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-1 text-sm text-gray-400 hover:text-white transition"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
            돌아가기
          </button>
          <h1 className="text-lg font-bold">설정</h1>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-3 sm:px-6 py-6 sm:py-8 space-y-5 sm:space-y-6">

        {/* 로컬 서버 (Bridge) */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4">로컬 서버 (Bridge)</h2>
          <div className="flex items-center gap-2 mb-4">
            <span className={`w-2.5 h-2.5 rounded-full ${bridgeConnected ? 'bg-green-400' : 'bg-yellow-400 animate-pulse'}`} />
            <span className={`text-sm ${bridgeConnected ? 'text-green-400' : 'text-yellow-400'}`}>
              {bridgeConnected ? '연결됨' : '미연결'}
            </span>
            {bridgeConnected && bridgeUptime != null && (
              <span className="text-xs text-gray-500 ml-2">
                업타임: {formatUptime(bridgeUptime)}
              </span>
            )}
          </div>

          {!bridgeConnected && (
            <div className="space-y-3">
              <p className="text-xs text-gray-400">
                주문 실행과 증권사 연결을 위해 이 PC에서 로컬 서버가 실행되어야 합니다.
              </p>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleLaunch}
                  disabled={launchWaiting}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-500 transition disabled:opacity-50"
                >
                  {launchWaiting ? '연결 대기 중...' : '서버 시작'}
                </button>
                <a
                  href={DOWNLOAD_URL}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-500 transition"
                >
                  설치파일 다운로드
                </a>
              </div>
              {launchFailed && (
                <p className="text-xs text-red-400">
                  서버를 찾을 수 없습니다. 설치파일을 다운로드하여 먼저 설치해 주세요.
                </p>
              )}
              <details className="text-xs text-gray-500">
                <summary className="cursor-pointer hover:text-gray-300 transition">수동 실행 경로</summary>
                <code className="block mt-1.5 bg-gray-800 rounded px-2.5 py-1.5 text-[11px] text-gray-400 select-all">
                  %LOCALAPPDATA%\StockVision\stockvision-local.exe
                </code>
              </details>
            </div>
          )}
        </section>

        {/* 엔진 상태 + 제어 */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4">엔진 상태</h2>
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${engineRunning ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`} />
                <span className={`text-sm ${engineRunning ? 'text-green-400' : 'text-gray-500'}`}>
                  전략 엔진: {engineRunning ? '실행 중' : '정지'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${brokerConnected ? 'bg-green-400' : 'bg-gray-600'}`} />
                <span className={`text-sm ${brokerConnected ? 'text-green-400' : 'text-gray-500'}`}>
                  브로커: {brokerConnected ? '연결됨' : '미연결'}
                </span>
              </div>
            </div>
            <button
              onClick={handleEngineToggle}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition ${
                engineRunning
                  ? 'bg-red-900/50 text-red-400 border border-red-800 hover:bg-red-900'
                  : 'bg-green-900/50 text-green-400 border border-green-800 hover:bg-green-900'
              }`}
            >
              {engineRunning ? '엔진 중지' : '엔진 시작'}
            </button>
          </div>
        </section>

        {/* 증권사 API 설정 */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-base font-semibold mb-1">증권사 API 설정</h2>
          <p className="text-xs text-gray-500 mb-4">API Key는 이 PC에만 저장됩니다. 클라우드로 전송되지 않습니다.</p>

          {hasKeys ? (
            /* 등록 완료 — 읽기전용 표시 */
            <div className="space-y-2">
              {credentials?.kiwoom?.app_key && (
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs text-gray-400 font-medium">키움증권</span>
                    {isMock !== null && (
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${isMock ? 'bg-yellow-900/50 text-yellow-400' : 'bg-red-900/50 text-red-400'}`}>
                        {isMock ? '모의' : '실전'}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-4 text-xs font-mono">
                    <span className="text-gray-500">App Key: <span className="text-gray-300">{credentials.kiwoom.app_key}</span></span>
                    <span className="text-gray-500">Secret: <span className="text-gray-300">{credentials.kiwoom.secret_key}</span></span>
                  </div>
                </div>
              )}
              {credentials?.kis?.app_key && (
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs text-gray-400 font-medium">한국투자증권</span>
                    {isMock !== null && (
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${isMock ? 'bg-yellow-900/50 text-yellow-400' : 'bg-red-900/50 text-red-400'}`}>
                        {isMock ? '모의' : '실전'}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-4 text-xs font-mono">
                    <span className="text-gray-500">App Key: <span className="text-gray-300">{credentials.kis.app_key}</span></span>
                    <span className="text-gray-500">Secret: <span className="text-gray-300">{credentials.kis.app_secret}</span></span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <BrokerKeyForm onSuccess={async () => {
              addAlert('API Key 등록 완료', 'success')
              queryClient.invalidateQueries({ queryKey: ['localStatus'] })
              try { await localBroker.reconnect() } catch { /* 연결 실패 — 무시 */ }
            }} />
          )}
        </section>


        {/* 알림 설정 */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4">알림 설정</h2>
          <AlertSettings />
        </section>

        {/* 프로필 */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-base font-semibold mb-4">계정</h2>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">이메일</label>
              <input
                type="text"
                value={email ?? ''}
                disabled
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-gray-400"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">닉네임</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  maxLength={20}
                  className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-gray-100 focus:outline-none focus:border-indigo-500 transition"
                  placeholder="닉네임 (2~20자)"
                />
                <button
                  onClick={handleNicknameSave}
                  disabled={nickSaving || nickname.trim() === (profile?.nickname ?? '')}
                  className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition"
                >
                  {nickSaving ? '저장 중...' : '저장'}
                </button>
              </div>
            </div>
          </div>
          <div className="mt-6 pt-5 border-t border-gray-800">
            <button
              onClick={async () => { await logout(); navigate('/login') }}
              className="px-4 py-2 text-sm text-red-400 bg-red-900/30 border border-red-800 rounded-xl hover:bg-red-900/50 transition"
            >
              로그아웃
            </button>
          </div>
        </section>
        {/* 디바이스 관리 */}
        <section className="bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
          <DeviceManager />
        </section>

        {/* 자동 업데이트 */}
        {bridgeConnected && (
          <UpdateSettings />
        )}

      </main>
    </div>
  )
}

/** 자동 업데이트 설정 섹션 */
function UpdateSettings() {
  const [autoEnabled, setAutoEnabled] = useState(true)
  const [noUpdateStart, setNoUpdateStart] = useState('08:00')
  const [noUpdateEnd, setNoUpdateEnd] = useState('17:00')
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    localConfig.get().then((cfg) => {
      if (cfg?.update) {
        setAutoEnabled(cfg.update.auto_enabled ?? true)
        setNoUpdateStart(cfg.update.no_update_start ?? '08:00')
        setNoUpdateEnd(cfg.update.no_update_end ?? '17:00')
      }
      setLoaded(true)
    })
  }, [])

  const save = (patch: Partial<import('../types/settings').UpdateConfig>) => {
    localConfig.update({ update: { auto_enabled: autoEnabled, no_update_start: noUpdateStart, no_update_end: noUpdateEnd, ...patch } })
  }

  if (!loaded) return null

  return (
    <section className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 className="text-base font-semibold mb-4">자동 업데이트</h2>

      <label className="flex items-center gap-3 mb-4 cursor-pointer">
        <input
          type="checkbox"
          checked={autoEnabled}
          onChange={(e) => { setAutoEnabled(e.target.checked); save({ auto_enabled: e.target.checked }) }}
          className="accent-blue-500 w-4 h-4"
        />
        <span className="text-sm text-gray-300">자동 업데이트 사용</span>
      </label>

      {autoEnabled && (
        <div className="space-y-3">
          <p className="text-xs text-gray-500">업데이트 차단 시간 (이 구간에는 설치하지 않음)</p>
          <div className="flex items-center gap-2">
            <input
              type="time"
              value={noUpdateStart}
              onChange={(e) => { setNoUpdateStart(e.target.value); save({ no_update_start: e.target.value }) }}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-gray-300"
            />
            <span className="text-gray-500 text-sm">~</span>
            <input
              type="time"
              value={noUpdateEnd}
              onChange={(e) => { setNoUpdateEnd(e.target.value); save({ no_update_end: e.target.value }) }}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-gray-300"
            />
          </div>
          <p className="text-xs text-gray-600">기본: 08:00 ~ 17:00 (장중 업데이트 방지)</p>
        </div>
      )}
    </section>
  )
}
