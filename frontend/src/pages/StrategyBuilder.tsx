import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { rulesApi, TradingRule, Condition, RuleBody } from '../services/rules'
import ConditionRow from '../components/ConditionRow'
import RuleList from '../components/RuleList'

const EMPTY_RULE: RuleBody = {
  name: '',
  stock_code: '',
  side: 'BUY',
  conditions: [{ variable: 'kospi_rsi_14', operator: '<', value: 30 }],
  quantity: 10,
  is_active: true,
}

export default function StrategyBuilder() {
  const qc = useQueryClient()
  const [form, setForm]       = useState<RuleBody>(EMPTY_RULE)
  const [editId, setEditId]   = useState<number | null>(null)
  const [showForm, setShowForm] = useState(false)

  const { data: rulesData } = useQuery({
    queryKey: ['rules'],
    queryFn:  rulesApi.list,
  })
  const { data: varsData } = useQuery({
    queryKey: ['variables'],
    queryFn:  rulesApi.variables,
  })

  const invalidate = () => qc.invalidateQueries({ queryKey: ['rules'] })

  const saveMut = useMutation({
    mutationFn: () => editId ? rulesApi.update(editId, form) : rulesApi.create(form),
    onSuccess: () => { invalidate(); setShowForm(false); setEditId(null); setForm(EMPTY_RULE) },
  })
  const toggleMut = useMutation({
    mutationFn: rulesApi.toggle,
    onSuccess:  invalidate,
  })
  const deleteMut = useMutation({
    mutationFn: rulesApi.remove,
    onSuccess:  invalidate,
  })

  const rules  = rulesData?.data ?? []
  const vars   = varsData?.data
  const allVars = vars ? [...vars.market, ...vars.price] : []
  const ops    = vars?.operators ?? ['>', '<', '>=', '<=', '==']

  const updateCondition = (i: number, c: Condition) => {
    const conditions = [...form.conditions]
    conditions[i] = c
    setForm({ ...form, conditions })
  }
  const removeCondition = (i: number) =>
    setForm({ ...form, conditions: form.conditions.filter((_, idx) => idx !== i) })
  const addCondition = () =>
    setForm({ ...form, conditions: [...form.conditions, { variable: 'kospi_rsi_14', operator: '<', value: 30 }] })

  const startEdit = (rule: TradingRule) => {
    setEditId(rule.id)
    setForm({ name: rule.name, stock_code: rule.stock_code, side: rule.side,
              conditions: rule.conditions, quantity: rule.quantity, is_active: rule.is_active })
    setShowForm(true)
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">전략 빌더</h1>
        {!showForm && (
          <button
            onClick={() => { setShowForm(true); setEditId(null); setForm(EMPTY_RULE) }}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
          >
            + 새 전략
          </button>
        )}
      </div>

      {/* 규칙 목록 */}
      <div className="bg-white rounded-xl shadow p-4 mb-6">
        <h2 className="text-sm font-semibold text-gray-600 mb-2">저장된 전략</h2>
        <RuleList
          rules={rules}
          onToggle={id => toggleMut.mutate(id)}
          onEdit={startEdit}
          onDelete={id => deleteMut.mutate(id)}
        />
      </div>

      {/* 폼 */}
      {showForm && (
        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-lg font-semibold mb-4">{editId ? '전략 수정' : '새 전략 만들기'}</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">전략 이름</label>
              <input
                value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })}
                className="w-full border rounded px-3 py-2 text-sm"
                placeholder="예: RSI 과매도 매수"
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1">종목 코드</label>
                <input
                  value={form.stock_code}
                  onChange={e => setForm({ ...form, stock_code: e.target.value })}
                  className="w-full border rounded px-3 py-2 text-sm"
                  placeholder="005930"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">방향</label>
                <select
                  value={form.side}
                  onChange={e => setForm({ ...form, side: e.target.value as 'BUY' | 'SELL' })}
                  className="w-full border rounded px-3 py-2 text-sm"
                >
                  <option value="BUY">매수</option>
                  <option value="SELL">매도</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">수량 (주)</label>
                <input
                  type="number"
                  value={form.quantity}
                  onChange={e => setForm({ ...form, quantity: Number(e.target.value) })}
                  className="w-full border rounded px-3 py-2 text-sm"
                  min={1}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm font-medium">조건 (모두 충족 시 실행)</label>
                <button onClick={addCondition} className="text-xs text-blue-600 hover:underline">+ 조건 추가</button>
              </div>
              <div className="space-y-2">
                {form.conditions.map((c, i) => (
                  <ConditionRow
                    key={i}
                    condition={c}
                    variables={allVars}
                    operators={ops}
                    onChange={nc => updateCondition(i, nc)}
                    onDelete={() => removeCondition(i)}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="flex gap-3 mt-6">
            <button
              onClick={() => saveMut.mutate()}
              disabled={saveMut.isPending || !form.name || !form.stock_code}
              className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
            >
              {saveMut.isPending ? '저장 중...' : '저장'}
            </button>
            <button
              onClick={() => { setShowForm(false); setEditId(null) }}
              className="px-4 py-2 border rounded text-sm hover:bg-gray-50"
            >
              취소
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
