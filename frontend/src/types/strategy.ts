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

export interface Rule {
  id: number
  name: string
  symbol: string
  side: 'BUY' | 'SELL'
  operator: 'AND' | 'OR'
  conditions: Condition[]
  order_settings: OrderSettings
  is_active: boolean
  priority: number
  created_at: string
  updated_at: string
}

export type CreateRulePayload = Omit<Rule, 'id' | 'created_at' | 'updated_at'>
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
