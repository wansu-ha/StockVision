/** AlertSettings — Settings 페이지의 알림 설정 섹션 */
import { useState, useEffect } from 'react'
import { alertsClient, type AlertSettings } from '../services/alertsClient'

interface ToggleProps {
  checked: boolean
  onChange: (v: boolean) => void
  disabled?: boolean
}

function Toggle({ checked, onChange, disabled }: ToggleProps) {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={`relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors
        ${checked ? 'bg-green-500' : 'bg-gray-600'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transform transition-transform mt-0.5
        ${checked ? 'translate-x-4' : 'translate-x-0.5'}`} />
    </button>
  )
}

interface NumberInputProps {
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
  step?: number
  suffix?: string
}

function NumberInput({ value, onChange, min, max, step = 1, suffix }: NumberInputProps) {
  return (
    <div className="flex items-center gap-1">
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={e => onChange(Number(e.target.value))}
        className="w-16 px-2 py-0.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-200 text-right"
      />
      {suffix && <span className="text-xs text-gray-500">{suffix}</span>}
    </div>
  )
}

export default function AlertSettings() {
  const [settings, setSettings] = useState<AlertSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    alertsClient.getSettings()
      .then(setSettings)
      .catch(() => setError('경고 설정을 불러오지 못했습니다.'))
  }, [])

  const save = async (updated: AlertSettings) => {
    setSaving(true)
    setError(null)
    try {
      const result = await alertsClient.updateSettings(updated)
      setSettings(result)
    } catch {
      setError('설정 저장에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  const updateRule = <K extends keyof AlertSettings['rules']>(
    key: K,
    patch: Partial<AlertSettings['rules'][K]>,
  ) => {
    if (!settings) return
    const updated: AlertSettings = {
      ...settings,
      rules: { ...settings.rules, [key]: { ...settings.rules[key], ...patch } },
    }
    setSettings(updated)
    save(updated)
  }

  const updateMaster = (v: boolean) => {
    if (!settings) return
    const updated = { ...settings, master_enabled: v }
    setSettings(updated)
    save(updated)
  }

  if (!settings) {
    return (
      <div className="text-xs text-gray-500">
        {error ?? '경고 설정 로딩 중...'}
      </div>
    )
  }

  const r = settings.rules

  return (
    <div className="space-y-4">
      {error && <p className="text-xs text-red-400">{error}</p>}

      {/* 알림 채널 */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-gray-200">알림 채널</div>
          <div className="text-xs text-gray-500 mt-0.5">경고 수신 방법</div>
        </div>
        <select
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200"
          defaultValue="app"
        >
          <option value="app">앱 내 알림</option>
          <option value="email" disabled>이메일 (준비 중)</option>
          <option value="telegram" disabled>텔레그램 (준비 중)</option>
          <option value="discord" disabled>디스코드 (준비 중)</option>
        </select>
      </div>

      {/* 마스터 ON/OFF */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-gray-200">경고 알림</div>
          <div className="text-xs text-gray-500 mt-0.5">모든 경고 알림 ON/OFF</div>
        </div>
        <Toggle checked={settings.master_enabled} onChange={updateMaster} />
      </div>

      <div className={`space-y-3 ${!settings.master_enabled ? 'opacity-40 pointer-events-none' : ''}`}>

        {/* 종목 손실 경고 */}
        <div className="flex items-center justify-between py-2 border-t border-gray-800">
          <div>
            <div className="text-xs text-gray-300">종목 손실 경고</div>
            <div className="text-xs text-gray-500">보유종목 평가손익이 임계값 이하</div>
          </div>
          <div className="flex items-center gap-3">
            <NumberInput
              value={Math.abs(r.position_loss.threshold_pct ?? 3)}
              onChange={v => updateRule('position_loss', { threshold_pct: -Math.abs(v) })}
              min={0.5} max={20} step={0.5} suffix="%"
            />
            <Toggle
              checked={r.position_loss.enabled}
              onChange={v => updateRule('position_loss', { enabled: v })}
            />
          </div>
        </div>

        {/* 급변동 경고 */}
        <div className="flex items-center justify-between py-2 border-t border-gray-800">
          <div>
            <div className="text-xs text-gray-300">급변동 경고</div>
            <div className="text-xs text-gray-500">전일 대비 ±N% 이상 변동</div>
          </div>
          <div className="flex items-center gap-3">
            <NumberInput
              value={r.volatility.threshold_pct ?? 5}
              onChange={v => updateRule('volatility', { threshold_pct: v })}
              min={1} max={30} step={0.5} suffix="%"
            />
            <Toggle
              checked={r.volatility.enabled}
              onChange={v => updateRule('volatility', { enabled: v })}
            />
          </div>
        </div>

        {/* 미체결 방치 */}
        <div className="flex items-center justify-between py-2 border-t border-gray-800">
          <div>
            <div className="text-xs text-gray-300">미체결 장기 방치</div>
            <div className="text-xs text-gray-500">N분 경과 미체결 주문</div>
          </div>
          <div className="flex items-center gap-3">
            <NumberInput
              value={r.stale_order.threshold_min ?? 10}
              onChange={v => updateRule('stale_order', { threshold_min: v })}
              min={1} max={60} step={1} suffix="분"
            />
            <Toggle
              checked={r.stale_order.enabled}
              onChange={v => updateRule('stale_order', { enabled: v })}
            />
          </div>
        </div>

        {/* 일일 손실 한도 근접 */}
        <div className="flex items-center justify-between py-2 border-t border-gray-800">
          <div>
            <div className="text-xs text-gray-300">일일 손실 한도 근접</div>
            <div className="text-xs text-gray-500">최대 손실의 80% 도달 시</div>
          </div>
          <Toggle
            checked={r.daily_loss_proximity.enabled}
            onChange={v => updateRule('daily_loss_proximity', { enabled: v })}
          />
        </div>

        {/* 장 종료 임박 미체결 */}
        <div className="flex items-center justify-between py-2 border-t border-gray-800">
          <div>
            <div className="text-xs text-gray-300">장 종료 임박 미체결</div>
            <div className="text-xs text-gray-500">15:20 이후 미체결 주문 존재</div>
          </div>
          <Toggle
            checked={r.market_close_orders.enabled}
            onChange={v => updateRule('market_close_orders', { enabled: v })}
          />
        </div>

        {/* 엔진/브로커 장애 */}
        <div className="flex items-center justify-between py-2 border-t border-gray-800">
          <div>
            <div className="text-xs text-gray-300">엔진/브로커 장애</div>
            <div className="text-xs text-gray-500">엔진 비정상 정지 또는 브로커 연결 단절</div>
          </div>
          <div className="flex items-center gap-2">
            <Toggle
              checked={r.engine_health.enabled}
              onChange={v => updateRule('engine_health', { enabled: v })}
            />
          </div>
        </div>

        {/* Kill Switch / 손실 락 — 항상 ON */}
        <div className="flex items-center justify-between py-2 border-t border-gray-800 opacity-60">
          <div>
            <div className="text-xs text-gray-300">Kill Switch / 손실 락</div>
            <div className="text-xs text-gray-500">안전장치 발동 시 — 끌 수 없음</div>
          </div>
          <Toggle checked={true} onChange={() => {}} disabled={true} />
        </div>

      </div>

      {saving && <p className="text-xs text-gray-500">저장 중...</p>}
    </div>
  )
}
