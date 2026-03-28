/** 규칙 카드 — 5블록 구조 (조건/실행/리스크/최근결과/백테스트) */
import type { Rule } from '../types/strategy'
import { parseDirection } from '../types/strategy'
import type { LastRuleResult } from '../types/rule-result'
import type { BacktestSummary } from '../services/backtest'

interface Props {
  rule: Rule
  symbolName?: string
  engineRunning?: boolean
  lastResult?: LastRuleResult | null
  backtestSummary?: BacktestSummary | null
  onToggle: (id: number, enabled: boolean) => void
  onEdit: (id: number) => void
  onDelete: (id: number) => void
  onBacktest?: (id: number) => void
}

const DIRECTION_STYLE: Record<string, string> = {
  '매수': 'text-blue-400 bg-blue-900/30',
  '매도': 'text-red-400 bg-red-900/30',
  '양방향': 'text-purple-400 bg-purple-900/30',
}

const RESULT_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  SUCCESS: { bg: 'bg-green-100', text: 'text-green-700', label: '성공' },
  BLOCKED: { bg: 'bg-orange-100', text: 'text-orange-700', label: '차단' },
  FAILED: { bg: 'bg-red-100', text: 'text-red-700', label: '실패' },
}

/** script 파싱 또는 JSON 조건 요약 */
function summarizeConditions(rule: Rule): string {
  if (rule.script) {
    const lines = rule.script
      .split('\n')
      .map(l => l.trim())
      .filter(l => l && !l.startsWith('--'))
    return lines.length > 0 ? lines.join(' | ') : '조건 없음'
  }
  const parts: string[] = []
  if (rule.buy_conditions) {
    const keys = Object.keys(rule.buy_conditions)
    parts.push(`매수: ${keys.length}개 조건`)
  }
  if (rule.sell_conditions) {
    const keys = Object.keys(rule.sell_conditions)
    parts.push(`매도: ${keys.length}개 조건`)
  }
  return parts.length > 0 ? parts.join(', ') : '조건 없음'
}

/** trigger_policy 표시 텍스트 */
function triggerLabel(rule: Rule): string {
  const freq = rule.trigger_policy?.frequency
  if (freq === 'ONCE') return '1회'
  if (freq === 'ONCE_PER_DAY') return '일 1회'
  return '일 1회'
}

export default function RuleCard({ rule, symbolName, engineRunning, lastResult, backtestSummary, onToggle, onEdit, onDelete, onBacktest }: Props) {
  const direction = parseDirection(rule)
  const isRunning = engineRunning && rule.is_active
  const orderType = rule.execution?.order_type ?? rule.order_type ?? 'MARKET'
  const qty = rule.execution?.qty_value ?? rule.qty ?? 1

  return (
    <div className={`bg-white rounded-xl border p-4 transition-colors ${rule.is_active ? 'border-green-200' : 'border-gray-200'}`}>
      {/* 헤더: 종목명, 방향배지, ON/OFF, 수정/삭제 */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{rule.name}</h3>
          <p className="text-sm text-gray-500">
            {symbolName ? `${symbolName} ${rule.symbol}` : rule.symbol}
          </p>
          <div className="flex items-center gap-2 mt-1">
            {direction !== '없음' && (
              <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${DIRECTION_STYLE[direction]}`}>
                {direction}
              </span>
            )}
            {isRunning ? (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" />
                실행 중
              </span>
            ) : (
              <span className="text-xs text-gray-500">OFF</span>
            )}
          </div>
        </div>
        <button
          onClick={() => onToggle(rule.id, !rule.is_active)}
          className={`relative w-10 h-5 rounded-full transition-colors ${rule.is_active ? 'bg-green-400' : 'bg-gray-300'}`}
        >
          <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${rule.is_active ? 'translate-x-5' : 'translate-x-0.5'}`} />
        </button>
      </div>

      {/* 블록 1: 조건 */}
      <div className="mb-2">
        <p className="text-[11px] font-medium text-gray-400 uppercase mb-0.5">조건</p>
        <p className="text-xs text-gray-600 truncate">{summarizeConditions(rule)}</p>
      </div>

      {/* 블록 2: 실행 */}
      <div className="mb-2">
        <p className="text-[11px] font-medium text-gray-400 uppercase mb-0.5">실행</p>
        <div className="flex items-center gap-2 text-xs text-gray-600">
          <span>{orderType === 'LIMIT' ? '지정가' : '시장가'}</span>
          <span className="text-gray-300">|</span>
          <span>{qty}주</span>
          <span className="text-gray-300">|</span>
          <span>{triggerLabel(rule)}</span>
        </div>
      </div>

      {/* 블록 3: 리스크 */}
      <div className="mb-2">
        <p className="text-[11px] font-medium text-gray-400 uppercase mb-0.5">리스크</p>
        <div className="flex items-center gap-2 text-xs text-gray-600">
          <span>최대 {rule.max_position_count ?? '-'}종목</span>
          <span className="text-gray-300">|</span>
          <span>예산 {rule.budget_ratio != null ? `${(rule.budget_ratio * 100).toFixed(0)}%` : '-'}</span>
        </div>
      </div>

      {/* 블록 4: 최근 결과 */}
      <div className="mb-3">
        <p className="text-[11px] font-medium text-gray-400 uppercase mb-0.5">최근 결과</p>
        {lastResult ? (
          <div className="flex items-center gap-2">
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${RESULT_STYLE[lastResult.status]?.bg ?? 'bg-gray-100'} ${RESULT_STYLE[lastResult.status]?.text ?? 'text-gray-600'}`}>
              {RESULT_STYLE[lastResult.status]?.label ?? lastResult.status}
            </span>
            {lastResult.reason && (
              <span className="text-xs text-gray-500 truncate">{lastResult.reason}</span>
            )}
          </div>
        ) : (
          <span className="text-xs text-gray-400">미실행</span>
        )}
      </div>

      {/* 블록 5: 백테스트 */}
      <div className="mb-3">
        <p className="text-[11px] font-medium text-gray-400 uppercase mb-0.5">백테스트</p>
        {backtestSummary ? (
          <div className="flex items-center gap-3 text-xs">
            <span className={backtestSummary.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}>
              수익 {backtestSummary.total_return_pct}%
            </span>
            <span className="text-red-400">MDD -{backtestSummary.max_drawdown_pct}%</span>
            <span className="text-gray-300">승률 {backtestSummary.win_rate}%</span>
          </div>
        ) : (
          <span className="text-xs text-gray-500">미검증</span>
        )}
      </div>

      {/* 수정/삭제/백테스트 */}
      <div className="flex items-center gap-2">
        <button onClick={() => onEdit(rule.id)} className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
          수정
        </button>
        {onBacktest && (
          <button onClick={() => onBacktest(rule.id)} className="text-xs text-indigo-400 hover:text-indigo-300 font-medium">
            백테스트
          </button>
        )}
        <button onClick={() => onDelete(rule.id)} className="text-xs text-red-500 hover:text-red-700 font-medium">
          삭제
        </button>
      </div>
    </div>
  )
}
