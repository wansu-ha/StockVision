/** 증권사 API 키 등록 폼 — 온보딩/Settings 공용. */
import { useState } from 'react'
import { localConfig, localBroker } from '../../services/localClient'

interface Props {
  onSuccess: () => void
  showHints?: boolean // 온보딩 모드에서 추가 안내 표시
}

export default function BrokerKeyForm({ onSuccess, showHints }: Props) {
  const [brokerType, setBrokerType] = useState<'kiwoom' | 'kis'>('kiwoom')
  const [appKey, setAppKey] = useState('')
  const [appSecret, setAppSecret] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const res = await localConfig.setBrokerKeys(brokerType, appKey, appSecret)
      const label = res?.data?.is_mock ? '모의투자' : '실전투자'
      setResult(`등록 완료 (${label})`)
      setAppKey('')
      setAppSecret('')
      localBroker.reconnect()
      onSuccess()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'API Key 등록 실패. 키를 확인하세요.'
      setError(msg)
    } finally {
      setSaving(false)
    }
  }

  const inputCls = 'w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-xl text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition'

  return (
    <div className="space-y-3">
      {showHints && (
        <div className="text-xs text-gray-400 space-y-1 mb-2">
          <p>API 키는 이 PC에만 저장됩니다. 외부로 전송되지 않습니다.</p>
          <p>처음이라면 <strong className="text-yellow-400">모의투자</strong> 키로 먼저 테스트하세요.</p>
        </div>
      )}

      <select
        value={brokerType}
        onChange={(e) => setBrokerType(e.target.value as 'kiwoom' | 'kis')}
        className={inputCls + ' text-gray-300'}
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
        className={inputCls}
      />
      <input
        type="password"
        autoComplete="off"
        placeholder="App Secret"
        value={appSecret}
        onChange={(e) => setAppSecret(e.target.value)}
        className={inputCls}
      />

      {error && <p className="text-xs text-red-400">{error}</p>}
      {result && <p className="text-xs text-green-400">{result}</p>}

      <button
        onClick={handleSave}
        disabled={!appKey || !appSecret || saving}
        className="w-full py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition"
      >
        {saving ? '확인 중...' : '등록'}
      </button>
    </div>
  )
}
