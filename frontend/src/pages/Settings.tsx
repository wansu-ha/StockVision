/** 설정 페이지 (API Key 등록, 모드 전환, 프로필) */
import { useState, useEffect } from 'react'
import { localConfig } from '../services/localClient'
import { cloudAuth } from '../services/cloudClient'
import { useAuth } from '../context/AuthContext'
import { useAlertStore } from '../stores/alertStore'
import type { LocalConfig } from '../types/settings'

export default function Settings() {
  const { email } = useAuth()
  const addAlert = useAlertStore((s) => s.add)

  // 증권사 API Key
  const [appKey, setAppKey] = useState('')
  const [appSecret, setAppSecret] = useState('')
  const [config, setConfig] = useState<LocalConfig | null>(null)

  // 프로필
  const [nickname, setNickname] = useState('')

  useEffect(() => {
    localConfig.get().then((c) => { if (c) setConfig(c) })
  }, [])

  const handleSaveKeys = async () => {
    try {
      await localConfig.setBrokerKeys(appKey, appSecret)
      addAlert('API Key가 등록되었습니다', 'success')
      setAppKey('')
      setAppSecret('')
    } catch {
      addAlert('API Key 등록 실패. 로컬 서버 연결을 확인하세요.', 'error')
    }
  }

  const handleModeChange = async (mode: 'paper' | 'live') => {
    const result = await localConfig.update({ mode })
    if (result) {
      setConfig((prev) => prev ? { ...prev, mode } : null)
      addAlert(`모드 전환: ${mode === 'paper' ? '모의투자' : '실거래'}`, 'info')
    }
  }

  const handleSaveProfile = async () => {
    try {
      await cloudAuth.updateProfile(nickname)
      addAlert('프로필이 수정되었습니다', 'success')
    } catch {
      addAlert('프로필 수정 실패', 'error')
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-8 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">설정</h1>

      {/* 증권사 API 설정 */}
      <section className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">증권사 API 설정</h2>
        <p className="text-xs text-gray-500 mb-4">API Key는 이 PC에만 저장됩니다. 클라우드로 전송되지 않습니다.</p>

        <div className="space-y-3">
          <input
            type="password"
            autoComplete="off"
            placeholder="App Key"
            value={appKey}
            onChange={(e) => setAppKey(e.target.value)}
            className="w-full px-4 py-2 border border-gray-200 rounded-xl text-sm"
          />
          <input
            type="password"
            autoComplete="off"
            placeholder="App Secret"
            value={appSecret}
            onChange={(e) => setAppSecret(e.target.value)}
            className="w-full px-4 py-2 border border-gray-200 rounded-xl text-sm"
          />
          <button
            onClick={handleSaveKeys}
            disabled={!appKey || !appSecret}
            className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            등록
          </button>
        </div>

        {/* 모드 전환 */}
        <div className="mt-6">
          <h3 className="text-sm font-medium text-gray-700 mb-2">거래 모드</h3>
          <div className="flex gap-3">
            {(['paper', 'live'] as const).map((m) => (
              <button
                key={m}
                onClick={() => handleModeChange(m)}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                  config?.mode === m
                    ? 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                }`}
              >
                {m === 'paper' ? '모의투자' : '실거래'}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 프로필 */}
      <section className="bg-white rounded-2xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">프로필</h2>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-500">이메일</label>
            <input
              type="text"
              value={email ?? ''}
              disabled
              className="w-full px-4 py-2 border border-gray-100 rounded-xl text-sm bg-gray-50"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">닉네임</label>
            <input
              type="text"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              className="w-full px-4 py-2 border border-gray-200 rounded-xl text-sm"
              placeholder="닉네임 입력"
            />
          </div>
          <button
            onClick={handleSaveProfile}
            disabled={!nickname}
            className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
          >
            저장
          </button>
        </div>
      </section>
    </div>
  )
}
