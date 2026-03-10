/**
 * DetailView — 상세 뷰 (차트, 지표, 컨텍스트, 규칙 토글+편집, 체결)
 * 디자인 개선: (A) indigo, (F) aria
 */
import { useState, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import PriceChart from './PriceChart'
import { cloudRules, cloudWatchlist } from '../../services/cloudClient'
import type { Stock, Trade } from './ListView'
import type { Rule } from '../../types/strategy'
import type { MarketContextData } from '../../types/dashboard'
import { AVAILABLE_INDICATORS } from '../../types/strategy'

interface DetailViewProps {
  stock: Stock
  trades: Trade[]
  rules: Rule[]
  context: MarketContextData | null
  onBack: () => void
}

export default function DetailView({ stock, trades, rules: propRules, context, onBack }: DetailViewProps) {
  const [ruleEditing, setRuleEditing] = useState<number | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const queryClient = useQueryClient()

  const stockTrades = trades.filter(t => t.symbol === stock.symbol || t.symbol === stock.name)

  const handleToggle = async (rule: Rule) => {
    try {
      await cloudRules.update(rule.id, { is_active: !rule.is_active })
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    } catch { /* 에러 시 무시 */ }
  }

  const handleDelete = async (rule: Rule) => {
    try {
      await cloudRules.remove(rule.id)
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    } catch { /* 에러 시 무시 */ }
  }

  const handleRemoveWatchlist = async () => {
    try {
      await cloudWatchlist.remove(stock.symbol)
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      onBack()
    } catch { /* 에러 시 무시 */ }
  }

  // 시장 컨텍스트 → 표시용 배열
  const contextItems = context ? [
    { label: 'KOSPI RSI', value: context.kospi_rsi?.toFixed(1) ?? '—' },
    { label: 'KOSDAQ RSI', value: context.kosdaq_rsi?.toFixed(1) ?? '—' },
    { label: '시장 추세', value: ({ bullish: '상승세', bearish: '하락세', neutral: '중립' }[context.trend ?? ''] ?? context.trend ?? '—') },
    { label: '변동성', value: context.volatility?.toFixed(2) ?? '—' },
  ] : []

  return (
    <>
      {/* 뒤로가기 + 종목 헤더 */}
      <div className="flex items-center justify-between mb-4 sm:mb-6">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <button
            onClick={onBack}
            className="flex items-center gap-1 text-sm text-gray-400 hover:text-white transition shrink-0"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
            </svg>
            <span className="hidden sm:inline">목록</span>
          </button>
          <div className="h-5 w-px bg-gray-700 shrink-0" />
          <div className="min-w-0">
            <h1 className="text-lg sm:text-xl font-bold truncate">{stock.name}</h1>
            <span className="text-xs text-gray-500">{stock.symbol}</span>
          </div>
        </div>
        <div className="text-right shrink-0 ml-2">
          <div className="text-xl sm:text-2xl font-bold font-mono">{stock.price.toLocaleString()}</div>
          <div className={`text-sm font-mono ${stock.change >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
            {stock.change >= 0 ? '+' : ''}{stock.change}%
          </div>
        </div>
      </div>

      {/* 가격 차트 */}
      <section className="mb-6">
        <h3 className="text-sm font-medium text-gray-400 mb-3">가격 추이</h3>
        <PriceChart symbol={stock.symbol} />
      </section>

      {/* 시장 컨텍스트 */}
      <section className="mb-6">
        <h3 className="text-sm font-medium text-gray-400 mb-3">시장 컨텍스트</h3>
        {contextItems.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800 rounded-xl py-6 text-center text-sm text-gray-600">
            컨텍스트 데이터를 불러올 수 없습니다
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
            {contextItems.map(c => (
              <div key={c.label} className="bg-gray-900 border border-gray-800 rounded-xl p-3 sm:p-4">
                <div className="text-xs text-gray-500 mb-1">{c.label}</div>
                <div className="font-mono text-base sm:text-lg font-medium">{c.value}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 규칙 */}
      <section className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-400">규칙</h3>
          <button
            onClick={() => setShowAddModal(true)}
            className="w-6 h-6 flex items-center justify-center rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm transition"
            aria-label="규칙 추가"
          >+</button>
        </div>
        {propRules.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800 rounded-xl py-8 text-center text-sm text-gray-600">
            이 종목에 설정된 규칙이 없습니다
          </div>
        ) : (
          <div className="space-y-2">
            {propRules.map(r => (
              <RuleRow
                key={r.id}
                rule={r}
                isEditing={ruleEditing === r.id}
                onToggleEdit={() => setRuleEditing(ruleEditing === r.id ? null : r.id)}
                onToggle={() => handleToggle(r)}
                onDelete={() => handleDelete(r)}
                onSaved={() => {
                  setRuleEditing(null)
                  queryClient.invalidateQueries({ queryKey: ['rules'] })
                }}
              />
            ))}
          </div>
        )}
      </section>

      {/* 이 종목 최근 체결 */}
      <section>
        <h3 className="text-sm font-medium text-gray-400 mb-3">이 종목 체결 내역</h3>
        {stockTrades.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800 rounded-xl py-8 text-center text-sm text-gray-600">
            이 종목의 체결 내역이 없습니다
          </div>
        ) : (
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
            <table className="w-full text-sm min-w-[400px]" aria-label={`${stock.name} 체결 내역`}>
              <thead>
                <tr className="text-xs text-gray-500 border-b border-gray-800">
                  <th className="text-left px-4 py-2.5 font-medium">시각</th>
                  <th className="text-left px-4 py-2.5 font-medium">방향</th>
                  <th className="text-right px-4 py-2.5 font-medium">수량</th>
                  <th className="text-right px-4 py-2.5 font-medium">가격</th>
                  <th className="text-right px-4 py-2.5 font-medium">상태</th>
                </tr>
              </thead>
              <tbody>
                {stockTrades.map((t, i) => (
                  <tr key={i} className="border-t border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                    <td className="px-4 py-2.5 font-mono text-gray-400">{t.time}</td>
                    <td className={`px-4 py-2.5 ${t.side === '매수' ? 'text-red-400' : 'text-blue-400'}`}>{t.side}</td>
                    <td className="px-4 py-2.5 text-right font-mono">{t.qty}</td>
                    <td className="px-4 py-2.5 text-right font-mono">{t.price.toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-right">
                      {t.ok ? (
                        <span className="text-xs text-green-400 bg-green-400/10 px-2 py-0.5 rounded">체결</span>
                      ) : (
                        <span className="text-xs text-red-400 bg-red-400/10 px-2 py-0.5 rounded">거부</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* 하단 액션 */}
      <div className="mt-6 flex gap-3">
        <button onClick={handleRemoveWatchlist} className="text-sm text-gray-500 hover:text-red-400 transition">
          관심 종목 해제
        </button>
      </div>

      {/* 규칙 추가 모달 */}
      {showAddModal && (
        <AddRuleModal
          symbol={stock.symbol}
          stockName={stock.name}
          onClose={() => setShowAddModal(false)}
          onSaved={() => {
            setShowAddModal(false)
            queryClient.invalidateQueries({ queryKey: ['rules'] })
          }}
        />
      )}
    </>
  )
}

// ── AddRuleModal ──

interface AddRuleModalProps {
  symbol: string
  stockName: string
  onClose: () => void
  onSaved: () => void
}

function AddRuleModal({ symbol, stockName, onClose, onSaved }: AddRuleModalProps) {
  const nameRef = useRef<HTMLInputElement>(null)
  const indicatorRef = useRef<HTMLSelectElement>(null)
  const operatorRef = useRef<HTMLSelectElement>(null)
  const valueRef = useRef<HTMLInputElement>(null)
  const sideRef = useRef<HTMLSelectElement>(null)
  const qtyRef = useRef<HTMLInputElement>(null)
  const orderTypeRef = useRef<HTMLSelectElement>(null)
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    const name = nameRef.current?.value?.trim()
    if (!name) { nameRef.current?.focus(); return }

    const indicator = indicatorRef.current?.value ?? 'rsi_14'
    const operator = operatorRef.current?.value ?? '<='
    const value = Number(valueRef.current?.value) || 30
    const side = sideRef.current?.value === '매도' ? 'sell' : 'buy'
    const qty = Number(qtyRef.current?.value) || 10
    const orderType = orderTypeRef.current?.value === '지정가' ? 'limit' : 'market'

    const conditions = {
      operator: 'AND',
      conditions: [{ type: 'indicator', field: indicator, operator, value }],
    }

    setSaving(true)
    try {
      await cloudRules.create({
        name,
        symbol,
        buy_conditions: side === 'buy' ? conditions : undefined,
        sell_conditions: side === 'sell' ? conditions : undefined,
        order_type: orderType,
        qty,
        is_active: true,
      })
      onSaved()
    } catch {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-bold">{stockName} 규칙 추가</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition text-lg">&times;</button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">규칙 이름</label>
            <input
              ref={nameRef}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 transition"
              placeholder="예: RSI 매수"
              autoFocus
            />
          </div>

          <div>
            <label className="text-xs text-gray-500 mb-1 block">조건</label>
            <div className="flex flex-wrap gap-2">
              <select ref={indicatorRef} defaultValue="rsi_14" className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500">
                {AVAILABLE_INDICATORS.map(ind => (
                  <option key={ind.key} value={ind.key}>{ind.name}</option>
                ))}
              </select>
              <select ref={operatorRef} defaultValue="<=" className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500">
                <option value="<=">{'≤'}</option>
                <option value=">=">{' ≥'}</option>
                <option value="==">{'='}</option>
              </select>
              <input ref={valueRef} defaultValue="30" className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-20 focus:outline-none focus:border-indigo-500" />
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-500 mb-1 block">실행</label>
            <div className="flex flex-wrap gap-2">
              <select ref={sideRef} defaultValue="매수" className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500">
                <option>매수</option><option>매도</option>
              </select>
              <input ref={qtyRef} defaultValue="10" className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm w-20 focus:outline-none focus:border-indigo-500" />
              <span className="text-sm text-gray-500 self-center">주</span>
              <select ref={orderTypeRef} defaultValue="시장가" className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500">
                <option>시장가</option><option>지정가</option>
              </select>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white transition">취소</button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-5 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 disabled:opacity-50 transition"
          >{saving ? '저장 중...' : '저장'}</button>
        </div>
      </div>
    </div>
  )
}

// ── RuleRow 서브컴포넌트 (편집 폼 상태 격리) ──

interface RuleRowProps {
  rule: Rule
  isEditing: boolean
  onToggleEdit: () => void
  onToggle: () => void
  onDelete: () => void
  onSaved: () => void
}

function RuleRow({ rule, isEditing, onToggleEdit, onToggle, onDelete, onSaved }: RuleRowProps) {
  const indicatorRef = useRef<HTMLSelectElement>(null)
  const operatorRef = useRef<HTMLSelectElement>(null)
  const valueRef = useRef<HTMLInputElement>(null)
  const sideRef = useRef<HTMLSelectElement>(null)
  const qtyRef = useRef<HTMLInputElement>(null)
  const orderTypeRef = useRef<HTMLSelectElement>(null)

  const handleSave = async () => {
    const indicator = indicatorRef.current?.value ?? 'rsi_14'
    const operator = operatorRef.current?.value ?? '<='
    const value = Number(valueRef.current?.value) || 30
    const side = sideRef.current?.value === '매도' ? 'sell' : 'buy'
    const qty = Number(qtyRef.current?.value) || 10
    const orderType = orderTypeRef.current?.value === '지정가' ? 'LIMIT' : 'MARKET'

    const script = `IF ${indicator} ${operator} ${value} THEN ${side.toUpperCase()} ${qty}`
    try {
      await cloudRules.update(rule.id, {
        script,
        execution: { order_type: orderType, qty_type: 'FIXED', qty_value: qty },
        buy_conditions: side === 'buy' ? { [indicator]: { op: operator, val: value } } : null,
        sell_conditions: side === 'sell' ? { [indicator]: { op: operator, val: value } } : null,
        qty,
        order_type: orderType.toLowerCase(),
      })
      onSaved()
    } catch { /* 에러 시 무시 */ }
  }

  return (
    <div>
      <div className={`flex items-center justify-between p-4 bg-gray-900 border border-gray-800 rounded-xl transition ${!rule.is_active ? 'opacity-50' : ''} ${isEditing ? 'rounded-b-none border-b-0' : ''}`}>
        <div className="flex items-center gap-3">
          <button
            role="switch"
            aria-checked={rule.is_active}
            aria-label={`규칙 ${rule.is_active ? '활성' : '비활성'}`}
            onClick={onToggle}
            className={`relative w-9 h-5 rounded-full transition-colors ${rule.is_active ? 'bg-green-500' : 'bg-gray-600'}`}
          >
            <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${rule.is_active ? 'left-[18px]' : 'left-0.5'}`} />
          </button>
          <span className="text-sm">{rule.name}</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onToggleEdit}
            className="text-xs text-gray-400 hover:text-indigo-400 transition"
          >
            {isEditing ? '닫기' : '수정'}
          </button>
          <button onClick={onDelete} className="text-xs text-gray-400 hover:text-red-400 transition">삭제</button>
        </div>
      </div>

      {isEditing && (
        <div className="bg-gray-800/50 border border-gray-800 border-t-0 rounded-b-xl p-4">
          <div className="flex flex-wrap gap-2 mb-3">
            <select ref={indicatorRef} defaultValue="rsi_14" className="bg-gray-700 rounded-lg px-3 py-1.5 text-sm border-0 focus:outline-none focus:ring-1 focus:ring-indigo-500">
              {AVAILABLE_INDICATORS.map(ind => (
                <option key={ind.key} value={ind.key}>{ind.name}</option>
              ))}
            </select>
            <select ref={operatorRef} defaultValue="<=" className="bg-gray-700 rounded-lg px-3 py-1.5 text-sm border-0 focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option value="<=">{'<='}</option>
              <option value=">=">{'>='}</option>
              <option value="==">{'=='}</option>
            </select>
            <input ref={valueRef} className="bg-gray-700 rounded-lg px-3 py-1.5 text-sm w-20 border-0 focus:outline-none focus:ring-1 focus:ring-indigo-500" defaultValue="30" />
            <span className="text-gray-500 self-center">→</span>
            <select ref={sideRef} defaultValue="매수" className="bg-gray-700 rounded-lg px-3 py-1.5 text-sm border-0 focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option>매수</option><option>매도</option>
            </select>
            <input ref={qtyRef} className="bg-gray-700 rounded-lg px-3 py-1.5 text-sm w-16 border-0 focus:outline-none focus:ring-1 focus:ring-indigo-500" defaultValue={rule.qty || 10} />
            <span className="text-sm text-gray-500 self-center">주</span>
            <select ref={orderTypeRef} defaultValue={rule.order_type === 'limit' ? '지정가' : '시장가'} className="bg-gray-700 rounded-lg px-3 py-1.5 text-sm border-0 focus:outline-none focus:ring-1 focus:ring-indigo-500">
              <option>시장가</option><option>지정가</option>
            </select>
          </div>
          <div className="flex gap-2">
            <button onClick={handleSave} className="px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition">저장</button>
            <button onClick={onToggleEdit} className="px-4 py-1.5 text-sm text-gray-400 hover:text-white transition">취소</button>
          </div>
        </div>
      )}
    </div>
  )
}
