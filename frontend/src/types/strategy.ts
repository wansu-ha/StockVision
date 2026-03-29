/** 전략/규칙 관련 타입 */

export interface Condition {
  type: 'price' | 'indicator' | 'volume' | 'context'
  field: string
  operator: '>' | '>=' | '<' | '<=' | '==' | '!='
  value: number
}

export interface OrderSettings {
  order_type: 'market' | 'limit'
  qty: number
  budget_ratio: number
  max_positions: number
  limit_price?: number
}

/** v2 주문 설정 (execution JSON) */
export interface Execution {
  order_type: 'MARKET' | 'LIMIT'
  qty_type: 'FIXED'
  qty_value: number
  limit_price?: number | null
}

/** v2 트리거 정책 */
export interface TriggerPolicy {
  frequency: 'ONCE_PER_DAY' | 'ONCE'
  cooldown_minutes?: number | null
}

export interface Rule {
  id: number
  name: string
  symbol: string
  is_active: boolean
  priority: number
  version: number
  created_at: string
  updated_at: string | null
  // v2 DSL
  script: string | null
  execution: Execution | null
  trigger_policy: TriggerPolicy | null
  // v1 하위 호환
  buy_conditions: Record<string, unknown> | null
  sell_conditions: Record<string, unknown> | null
  order_type: string
  qty: number
  max_position_count: number
  budget_ratio: number
}

export type CreateRulePayload = Pick<Rule, 'name' | 'symbol'> & {
  script?: string | null
  execution?: Execution | null
  trigger_policy?: TriggerPolicy | null
  priority?: number
  buy_conditions?: Record<string, unknown> | null
  sell_conditions?: Record<string, unknown> | null
  order_type?: string
  qty?: number
  is_active?: boolean
}
export type UpdateRulePayload = Partial<CreateRulePayload>

export interface Indicator {
  key: string
  name: string
  description?: string
}

/** 프론트엔드 조건 편집기에서 사용할 지표 목록 */
export const AVAILABLE_INDICATORS: Indicator[] = [
  { key: 'price', name: '현재가' },
  { key: 'rsi_14', name: 'RSI (14)' },
  { key: 'ema_20', name: 'EMA (20)' },
  { key: 'ema_60', name: 'EMA (60)' },
  { key: 'macd', name: 'MACD' },
  { key: 'macd_signal', name: 'MACD Signal' },
  { key: 'volume_ratio', name: '거래량 배수' },
  { key: 'bb_upper', name: '볼린저 상단' },
  { key: 'bb_lower', name: '볼린저 하단' },
]

/** AI 컨텍스트 조건에서 사용할 필드 목록 */
export const CONTEXT_FIELDS: Indicator[] = [
  { key: 'sentiment_score', name: '시장 감성 점수' },
  { key: 'fear_greed', name: '공포/탐욕 지수' },
  { key: 'sector_score', name: '섹터 점수' },
]

export interface DslMeta {
  constants: { name: string; value: number | string }[]
  custom_functions: { name: string; body: string }[]
  rules: { index: number; condition: string; side: string; qty: string }[]
  parse_status: 'ok' | 'error'
  is_v2: boolean
  errors: { line: number; column: number; message: string }[]
}

export interface DslSchema {
  version: string
  fields: string[]
  compound_fields: Record<string, string>
  functions: Record<string, { min_args: number; max_args: number; return_type: string }>
  patterns: Record<string, { definition: string }>
}

/** rule.script 또는 v1 조건 필드에서 매매 방향을 파싱 */
export function parseDirection(rule: Rule): '매수' | '매도' | '양방향' | '없음' {
  if (rule.script) {
    const hasBuy = /^매수:/m.test(rule.script)
    const hasSell = /^매도:/m.test(rule.script)
    if (hasBuy && hasSell) return '양방향'
    if (hasBuy) return '매수'
    if (hasSell) return '매도'
    return '없음'
  }
  const hasBuy = rule.buy_conditions != null
  const hasSell = rule.sell_conditions != null
  if (hasBuy && hasSell) return '양방향'
  if (hasBuy) return '매수'
  if (hasSell) return '매도'
  return '없음'
}
