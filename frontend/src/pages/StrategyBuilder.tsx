import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { conditionsToDsl } from '../services/rules'
import type { Condition, Variable } from '../services/rules'
import { cloudRules } from '../services/cloudClient'
import { localRules } from '../services/localClient'
import type { Rule, CreateRulePayload } from '../types/strategy'
import { AVAILABLE_INDICATORS, CONTEXT_FIELDS } from '../types/strategy'
import ConditionRow from '../components/ConditionRow'
import RuleList from '../components/RuleList'

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
  const [readOnlyScript, setReadOnlyScript] = useState<string | null>(null)

  const { data: rulesData } = useQuery({
    queryKey: ['rules'],
    queryFn:  cloudRules.list,
  })
  const invalidate = () => qc.invalidateQueries({ queryKey: ['rules'] })

  const saveMut = useMutation({
    mutationFn: () => {
      const payload = formToPayload(form)
      return editId ? cloudRules.update(editId, payload) : cloudRules.create(payload)
    },
    onSuccess: () => {
      invalidate(); setShowForm(false); setEditId(null); setForm(EMPTY_FORM); setError(null); setReadOnlyScript(null)
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

  const startEdit = (rule: Rule) => {
    setEditId(rule.id)
    // TODO: script → 폼 역파싱 (복잡한 DSL은 읽기 전용)
    setForm({
      name: rule.name,
      symbol: rule.symbol,
      buyConditions: EMPTY_FORM.buyConditions,
      sellConditions: EMPTY_FORM.sellConditions,
      qty: rule.execution?.qty_value ?? rule.qty ?? 10,
      is_active: rule.is_active,
    })
    setReadOnlyScript(rule.script ?? null)
    setShowForm(true)
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">전략 빌더</h1>
        {!showForm && (
          <button
            onClick={() => { setShowForm(true); setEditId(null); setForm(EMPTY_FORM); setError(null); setReadOnlyScript(null) }}
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

            {editId && readOnlyScript ? (
              <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
                <p className="text-sm text-gray-400 mb-2">기존 전략 조건 (읽기 전용)</p>
                <pre className="bg-gray-800 p-3 rounded text-sm text-gray-300 whitespace-pre-wrap">{readOnlyScript}</pre>
                <p className="text-xs text-gray-500 mt-2">조건 수정은 DSL 역파싱 지원 후 가능합니다.</p>
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
              onClick={() => saveMut.mutate()}
              disabled={saveMut.isPending || !form.name || !form.symbol}
              className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
            >
              {saveMut.isPending ? '저장 중...' : '저장'}
            </button>
            <button
              onClick={() => { setShowForm(false); setEditId(null); setError(null); setReadOnlyScript(null) }}
              className="px-4 py-2 border border-gray-700 rounded-xl text-sm text-gray-300 hover:bg-gray-800 transition"
            >
              취소
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
