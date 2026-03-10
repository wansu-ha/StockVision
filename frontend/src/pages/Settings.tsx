/** 설정 페이지 — API Key 등록, 엔진 제어, 프로필 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { localConfig, localEngine } from '../services/localClient'
import { useAuth } from '../context/AuthContext'
import { useAlertStore } from '../stores/alertStore'
import { useAccountStatus } from '../hooks/useAccountStatus'

export default function Settings() {
  const { email, logout } = useAuth()
  const addAlert = useAlertStore((s) => s.add)
  const navigate = useNavigate()
  const { engineRunning, brokerConnected, credentials, isMock } = useAccountStatus()

  // 증권사 API Key
  const [brokerType, setBrokerType] = useState<'kiwoom' | 'kis'>('kiwoom')
  const [appKey, setAppKey] = useState('')
  const [appSecret, setAppSecret] = useState('')
  const [saving, setSaving] = useState(false)

  const hasKeys = !!(credentials?.kiwoom?.app_key || credentials?.kis?.app_key)

  const handleSaveKeys = async () => {
    setSaving(true)
    try {
      const res = await localConfig.setBrokerKeys(brokerType, appKey, appSecret)
      const label = res?.data?.is_mock ? '모의투자' : '실전투자'
      addAlert(`API Key 등록 완료 (${label})`, 'success')
      setAppKey('')
      setAppSecret('')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'API Key 등록 실패. 키를 확인하세요.'
      addAlert(msg, 'error')
    } finally {
      setSaving(false)
    }
  }

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
            /* 미등록 — 입력 폼 */
            <div className="space-y-3">
              <select
                value={brokerType}
                onChange={(e) => setBrokerType(e.target.value as 'kiwoom' | 'kis')}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm text-gray-300 focus:outline-none focus:border-indigo-500 transition"
              >
                <option value="kiwoom">키움증권</option>
                <option value="kis">한국투자증권 (KIS)</option>
              </select>
              <input
                type="password"
                autoComplete="off"
                placeholder="App Key"
                value={appKey}
                onChange={(e) => setAppKey(e.target.value)}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
              />
              <input
                type="password"
                autoComplete="off"
                placeholder="App Secret"
                value={appSecret}
                onChange={(e) => setAppSecret(e.target.value)}
                className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
              />
              <button
                onClick={handleSaveKeys}
                disabled={!appKey || !appSecret || saving}
                className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                {saving ? '확인 중...' : '등록'}
              </button>
            </div>
          )}
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

      </main>
    </div>
  )
}
