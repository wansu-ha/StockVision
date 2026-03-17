/**
 * DSL ↔ 폼 변환기.
 *
 * parseDsl 결과(ParsedCondition)를 앱의 Condition 타입으로 변환하거나
 * 역방향(Condition[] → DSL 문자열)으로 변환한다.
 *
 * StrategyBuilder에서 사용하는 Condition은 services/rules.ts 기준:
 *   { variable: string, operator: string, value: number }
 */

import { parseDsl, type ParseError } from './dslParser'
import type { Condition } from '../services/rules'
import { conditionsToDsl } from '../services/rules'

export interface DslConvertResult {
  success: boolean
  buyConditions: Condition[]
  sellConditions: Condition[]
  /** 매수/매도 조건 그룹의 논리 연산자 (혼재 시 AND 우선) */
  operator: 'AND' | 'OR'
  errors: ParseError[]
}

/**
 * DSL 문자열 → 폼 Condition 배열 변환.
 * 파싱 오류가 있어도 파싱된 만큼 반환한다 (부분 복원).
 */
export function dslToConditions(script: string): DslConvertResult {
  const result = parseDsl(script)

  const toCondition = (parsed: { field: string; operator: string; value: number }): Condition => ({
    variable: parsed.field,
    operator: parsed.operator as Condition['operator'],
    value: parsed.value,
  })

  const buyConditions = result.buy?.conditions.map(toCondition) ?? []
  const sellConditions = result.sell?.conditions.map(toCondition) ?? []

  // 그룹 연산자: 매수/매도 중 OR이 있으면 OR, 기본 AND
  const operator: 'AND' | 'OR' =
    result.buy?.operator === 'OR' || result.sell?.operator === 'OR' ? 'OR' : 'AND'

  return {
    success: result.success,
    buyConditions,
    sellConditions,
    operator,
    errors: result.errors,
  }
}

/**
 * 폼 Condition 배열 → DSL 문자열 변환.
 * services/rules.ts의 conditionsToDsl을 래핑한다.
 */
export { conditionsToDsl }
