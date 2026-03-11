/** 규칙 최근 실행 결과 타입 */
export interface LastRuleResult {
  rule_id: number
  status: 'SUCCESS' | 'BLOCKED' | 'FAILED'
  reason: string
  at: string
}
