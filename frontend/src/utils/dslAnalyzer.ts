/**
 * DSL 전략 상태 분석 — 매수/매도 규칙 수, 손절 유무 판정
 */

import { parseDslV2, type DslRule } from './dslParserV2'

export interface DslSummary {
  buyCount: number
  sellCount: number
  hasStopLoss: boolean
}

/**
 * DSL 스크립트를 분석하여 규칙 수와 손절 유무를 반환한다.
 * 파싱 실패 시 모두 0/false 반환.
 */
export function analyzeDsl(script: string | null | undefined): DslSummary {
  if (!script) return { buyCount: 0, sellCount: 0, hasStopLoss: false }

  const { rules } = parseDslV2(script)

  const buyCount = rules.filter(r => r.side === '매수').length
  const sellCount = rules.filter(r => r.side === '매도').length
  const hasStopLoss = rules.some(r => isStopLossRule(r))

  return { buyCount, sellCount, hasStopLoss }
}

/**
 * 손절 규칙 판정: 매도 규칙 중 "수익률" + "<=" + 음수 패턴
 */
function isStopLossRule(rule: DslRule): boolean {
  if (rule.side !== '매도') return false
  return /수익률\s*<=\s*-/.test(rule.condition)
}
