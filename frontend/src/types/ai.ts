/** AI 코어 서비스 타입 */

export interface AIChatRequest {
  conversation_id?: string | null
  message: string
  current_dsl?: string | null
  mode: 'builder' | 'assistant'
  thinking?: boolean
}

export interface SSEEvent {
  event: 'status' | 'thinking' | 'token' | 'dsl' | 'error' | 'done'
  data: Record<string, unknown>
}

export interface SSEStatusData {
  step: string
  message: string
}

export interface SSEDslData {
  script: string
  valid: boolean
}

export interface SSEDoneData {
  conversation_id: string
  credit_remaining: number
  credit_estimate: string
  tokens_used: number
}

export interface SSEErrorData {
  code: string
  message: string
}

export interface CreditBalance {
  tokens_used: number
  tokens_limit: number
  remaining_percent: number
  estimate_turns: number
  resets_at: string
  has_byo_key: boolean
}

export interface ConversationSummary {
  id: string
  title: string | null
  mode: string
  strategy_id: number | null
  updated_at: string
}

export interface ConversationDetail extends ConversationSummary {
  messages: Array<{ role: string; content: string; timestamp: string }>
  current_dsl: string | null
}

export interface StrategyVersionSummary {
  version: number
  message: string | null
  created_by: string
  created_at: string
}
