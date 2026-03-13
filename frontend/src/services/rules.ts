/**
 * 규칙 유틸리티 (conditionsToDsl) + 폼 타입
 *
 * CRUD는 cloudRules (cloudClient.ts)로 통일 완료.
 * 이 파일은 폼 변환 유틸과 ConditionRow용 타입만 유지.
 */

export interface Condition {
  variable: string
  operator: '>' | '<' | '>=' | '<=' | '=='
  value: number
}

export interface Variable {
  key: string
  label: string
  current: number | null
}

/** 폼 조건 → DSL script 문자열 변환 (v1 폼 → v2 DSL) */
export function conditionsToDsl(
  buyConditions: Condition[],
  sellConditions: Condition[],
): string {
  const mapCond = (c: Condition) => `${c.variable} ${c.operator} ${c.value}`
  const buy = buyConditions.map(mapCond).join(' AND ') || 'true'
  const sell = sellConditions.map(mapCond).join(' AND ') || 'true'
  return `매수: ${buy}\n매도: ${sell}`
}
