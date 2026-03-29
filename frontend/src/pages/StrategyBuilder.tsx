import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { conditionsToDsl } from '../services/rules'
import type { Condition, Variable } from '../services/rules'
import { cloudRules } from '../services/cloudClient'
import { localRules } from '../services/localClient'
import type { Rule, CreateRulePayload } from '../types/strategy'
import { AVAILABLE_INDICATORS, CONTEXT_FIELDS } from '../types/strategy'
import { STRATEGY_PRESETS } from '../data/strategyPresets'
import ConditionRow from '../components/ConditionRow'
import RuleList from '../components/RuleList'
import DslEditor from '../components/DslEditor'
import { dslToConditions } from '../utils/dslConverter'
import { runBacktest, type BacktestResponse } from '../services/backtest'
import BacktestResultView from '../components/BacktestResult'
import ParameterSliders from '../components/ParameterSliders'

interface FormState {
  name: string
  symbol: string
  buyConditions: Condition[]
  sellConditions: Condition[]
  qty: number
  is_active: boolean
}

const EMPTY_FORM: FormState = {
  name: '',
  symbol: '',
  buyConditions: [{ variable: 'kospi_rsi_14', operator: '<', value: 30 }],
  sellConditions: [{ variable: 'kospi_rsi_14', operator: '>', value: 70 }],
  qty: 10,
  is_active: true,
}

/** 폼 → CreateRulePayload (DSL script 포함) */
function formToPayload(form: FormState): CreateRulePayload {
  const script = conditionsToDsl(form.buyConditions, form.sellConditions)
  return {
    name: form.name,
    symbol: form.symbol,
    script,
    execution: { order_type: 'MARKET', qty_type: 'FIXED', qty_value: form.qty },
    trigger_policy: { frequency: 'ONCE_PER_DAY' },
    qty: form.qty,
    is_active: form.is_active,
  }
}

export default function StrategyBuilder() {
  const qc = useQueryClient()
  const [form, setForm]       = useState<FormState>(EMPTY_FORM)
  const [editId, setEditId]   = useState<number | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  // 조건 편집 모드: 'form' = 폼 UI, 'script' = DSL 텍스트 편집
  const [condMode, setCondMode] = useState<'form' | 'script'>('form')
  const [dslText, setDslText]  = useState<string>('')
  const [showPresets, setShowPresets] = useState(false)

  // 백테스트 상태
  const [btLoading, setBtLoading] = useState(false)
  const [btResult, setBtResult] = useState<BacktestResponse['data'] | null>(null)

  const handleBacktest = async () => {
    const script = condMode === 'script' ? dslText : conditionsToDsl(form.buyConditions, form.sellConditions)
    if (!script || !form.symbol) return
    setBtLoading(true)
    setBtResult(null)
    try {
      const resp = await runBacktest({ script, symbol: form.symbol, timeframe: '1d' })
      if (resp.success) setBtResult(resp.data)
    } catch { /* 에러 무시 — UI에 결과 없음으로 표시 */ }
    setBtLoading(false)
  }

  const { data: rulesData } = useQuery({
    queryKey: ['rules'],
    queryFn:  cloudRules.list,
    staleTime: 2 * 60_000,
  })
  const invalidate = () => qc.invalidateQueries({ queryKey: ['rules'] })

  const saveMut = useMutation({
    mutationFn: () => {
      // script 모드일 때는 dslText를 그대로 payload에 사용
      const payload = condMode === 'script'
        ? { ...formToPayload(form), script: dslText }
        : formToPayload(form)
      return editId ? cloudRules.update(editId, payload) : cloudRules.create(payload)
    },
    onSuccess: () => {
      invalidate(); setShowForm(false); setEditId(null); setForm(EMPTY_FORM); setError(null); setCondMode('form'); setDslText(''); setShowPresets(false)
      cloudRules.list().then((rules) => localRules.sync(rules)).catch(() => {})
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail || '저장 실패')
    },
  })
  const toggleMut = useMutation({
    mutationFn: (rule: Rule) => cloudRules.update(rule.id, { is_active: !rule.is_active }),
    onSuccess: () => {
      invalidate()
      cloudRules.list().then((rules) => localRules.sync(rules)).catch(() => {})
    },
  })
  const deleteMut = useMutation({
    mutationFn: cloudRules.remove,
    onSuccess: () => {
      invalidate()
      cloudRules.list().then((rules) => localRules.sync(rules)).catch(() => {})
    },
  })

  const rules  = rulesData ?? []
  const allVars: Variable[] = [...AVAILABLE_INDICATORS, ...CONTEXT_FIELDS].map(ind => ({
    key: ind.key, label: ind.name, current: null,
  }))
  const ops = ['>', '<', '>=', '<=', '==']

  const updateBuyCond = (i: number, c: Condition) => {
    const buyConditions = [...form.buyConditions]
    buyConditions[i] = c
    setForm({ ...form, buyConditions })
  }
  const updateSellCond = (i: number, c: Condition) => {
    const sellConditions = [...form.sellConditions]
    sellConditions[i] = c
    setForm({ ...form, sellConditions })
  }
  const removeBuyCond = (i: number) =>
    setForm({ ...form, buyConditions: form.buyConditions.filter((_, idx) => idx !== i) })
  const removeSellCond = (i: number) =>
    setForm({ ...form, sellConditions: form.sellConditions.filter((_, idx) => idx !== i) })
  const addBuyCond = () =>
    setForm({ ...form, buyConditions: [...form.buyConditions, { variable: 'kospi_rsi_14', operator: '<', value: 30 }] })
  const addSellCond = () =>
    setForm({ ...form, sellConditions: [...form.sellConditions, { variable: 'kospi_rsi_14', operator: '>', value: 70 }] })

  /** 폼 → 스크립트 모드 전환: 현재 폼 조건을 DSL 문자열로 변환 */
  const switchToScript = () => {
    setDslText(conditionsToDsl(form.buyConditions, form.sellConditions))
    setCondMode('script')
  }

  /** 스크립트 → 폼 모드 전환: DSL을 파싱해 폼 조건으로 복원 (오류 시 모드 유지) */
  const switchToForm = () => {
    const converted = dslToConditions(dslText)
    if (!converted.success) return // 오류 있으면 전환 보류
    setForm({
      ...form,
      buyConditions: converted.buyConditions.length > 0 ? converted.buyConditions : form.buyConditions,
      sellConditions: converted.sellConditions.length > 0 ? converted.sellConditions : form.sellConditions,
    })
    setCondMode('form')
  }

  const startEdit = (rule: Rule) => {
    setEditId(rule.id)
    const script = rule.script ?? ''
    // script → 폼 역파싱 시도; 실패 시 DSL 모드로 열기
    const converted = script ? dslToConditions(script) : null
    if (converted && converted.success && (converted.buyConditions.length > 0 || converted.sellConditions.length > 0)) {
      setForm({
        name: rule.name,
        symbol: rule.symbol,
        buyConditions: converted.buyConditions.length > 0 ? converted.buyConditions : EMPTY_FORM.buyConditions,
        sellConditions: converted.sellConditions.length > 0 ? converted.sellConditions : EMPTY_FORM.sellConditions,
        qty: rule.execution?.qty_value ?? rule.qty ?? 10,
        is_active: rule.is_active,
      })
      setCondMode('form')
      setDslText(script)
    } else {
      setForm({
        name: rule.name,
        symbol: rule.symbol,
        buyConditions: EMPTY_FORM.buyConditions,
        sellConditions: EMPTY_FORM.sellConditions,
        qty: rule.execution?.qty_value ?? rule.qty ?? 10,
        is_active: rule.is_active,
      })
      setDslText(script)
      setCondMode(script ? 'script' : 'form')
    }
    setShowPresets(false)
    setShowForm(true)
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">전략 빌더</h1>
        {!showForm && (
          <button
            onClick={() => { setShowForm(true); setEditId(null); setForm(EMPTY_FORM); setError(null); setCondMode('form'); setDslText(''); setShowPresets(false) }}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
          >
            + 새 전략
          </button>
        )}
      </div>

      {/* 규칙 목록 */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6">
        <h2 className="text-sm font-semibold text-gray-400 mb-2">저장된 전략</h2>
        <RuleList
          rules={rules}
          onToggle={(rule: Rule) => toggleMut.mutate(rule)}
          onEdit={startEdit}
          onDelete={(id: number) => deleteMut.mutate(id)}
        />
      </div>

      {/* 폼 */}
      {showForm && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-100">{editId ? '전략 수정' : '새 전략 만들기'}</h2>

          {error && (
            <div className="bg-red-900/30 border border-red-800/50 text-red-400 px-4 py-2 rounded mb-4 text-sm">{error}</div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">전략 이름</label>
              <input
                data-testid="strategy-name-input"
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
                placeholder="예: RSI 과매도 전략"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1">종목 코드</label>
                <input
                  data-testid="strategy-symbol-input"
                  value={form.symbol}
                  onChange={e => setForm({ ...form, symbol: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition"
                  placeholder="005930"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">수량 (주)</label>
                <input
                  type="number"
                  value={form.qty}
                  onChange={e => setForm({ ...form, qty: Number(e.target.value) })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-indigo-500 transition"
                  min={1}
                />
              </div>
            </div>

            {/* 프리셋 템플릿 선택 */}
            <div>
              <button
                type="button"
                onClick={() => setShowPresets(!showPresets)}
                className="text-xs text-indigo-400 hover:text-indigo-300 underline"
              >
                {showPresets ? '템플릿 닫기' : '템플릿에서 시작'}
              </button>
              {showPresets && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                  {STRATEGY_PRESETS.map(preset => (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() => {
                        setDslText(preset.script)
                        setCondMode('script')
                        setShowPresets(false)
                      }}
                      className="text-left bg-gray-800 border border-gray-700 rounded-lg p-3 hover:border-indigo-500 transition"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold text-gray-100">{preset.name}</span>
                        <span className="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded">{preset.category}</span>
                      </div>
                      <div className="text-xs text-gray-400">{preset.description}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* 조건 편집 모드 토글 */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-300">조건 편집</span>
              <div className="flex rounded-lg overflow-hidden border border-gray-700 text-xs">
                <button
                  type="button"
                  onClick={() => condMode === 'script' ? switchToForm() : undefined}
                  className={`px-3 py-1 transition-colors ${condMode === 'form' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                >
                  폼
                </button>
                <button
                  type="button"
                  onClick={() => condMode === 'form' ? switchToScript() : undefined}
                  className={`px-3 py-1 transition-colors ${condMode === 'script' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                >
                  DSL
                </button>
              </div>
            </div>

            {condMode === 'script' ? (
              /* DSL 텍스트 편집 모드 */
              <div className="space-y-2">
                <DslEditor value={dslText} onChange={setDslText} />
                <ParameterSliders script={dslText} onChange={setDslText} />
                <p className="text-xs text-gray-500">
                  폼 모드로 전환하면 DSL을 파싱해 조건을 복원합니다 (파싱 오류 시 전환 불가).
                </p>
              </div>
            ) : (
              <>
                {/* 매수 조건 */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm font-medium text-blue-600">매수 조건 (모두 충족 시)</label>
                    <button onClick={addBuyCond} className="text-xs text-blue-600 hover:underline">+ 조건 추가</button>
                  </div>
                  <div className="space-y-2">
                    {form.buyConditions.map((c, i) => (
                      <ConditionRow
                        key={`buy-${i}`}
                        condition={c}
                        variables={allVars}
                        operators={ops}
                        onChange={nc => updateBuyCond(i, nc)}
                        onDelete={() => removeBuyCond(i)}
                      />
                    ))}
                  </div>
                </div>

                {/* 매도 조건 */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm font-medium text-red-600">매도 조건 (하나라도 충족 시)</label>
                    <button onClick={addSellCond} className="text-xs text-red-600 hover:underline">+ 조건 추가</button>
                  </div>
                  <div className="space-y-2">
                    {form.sellConditions.map((c, i) => (
                      <ConditionRow
                        key={`sell-${i}`}
                        condition={c}
                        variables={allVars}
                        operators={ops}
                        onChange={nc => updateSellCond(i, nc)}
                        onDelete={() => removeSellCond(i)}
                      />
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="flex gap-3 mt-6">
            <button
              data-testid="save-strategy-btn"
              onClick={() => saveMut.mutate()}
              disabled={saveMut.isPending || !form.name || !form.symbol}
              className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
            >
              {saveMut.isPending ? '저장 중...' : '저장'}
            </button>
            <button
              data-testid="backtest-btn"
              onClick={handleBacktest}
              disabled={btLoading || !form.symbol}
              className="flex-1 bg-indigo-600 text-white py-2 rounded hover:bg-indigo-700 disabled:opacity-50 text-sm"
            >
              {btLoading ? '실행 중...' : '백테스트'}
            </button>
            <button
              onClick={() => { setShowForm(false); setEditId(null); setError(null); setCondMode('form'); setDslText(''); setShowPresets(false); setBtResult(null) }}
              className="px-4 py-2 border border-gray-700 rounded-xl text-sm text-gray-300 hover:bg-gray-800 transition"
            >
              취소
            </button>
          </div>

          {/* 백테스트 결과 패널 */}
          {btResult && (
            <div className="mt-6 border-t border-gray-700 pt-4">
              <BacktestResultView
                summary={btResult.summary}
                equityCurve={btResult.equity_curve}
                trades={btResult.trades}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
