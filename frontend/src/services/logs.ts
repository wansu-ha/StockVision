import client from './localClient'

/** 백엔드 log_db 실제 응답 구조 */
export interface LogEntry {
  id: number
  ts: string
  log_type: string
  symbol: string | null
  message: string
  meta: Record<string, unknown>
}

export interface LogSummary {
  date: string
  signals: number
  fills: number
  orders: number
  errors: number
}

interface LogsResponse {
  success: boolean
  data: { items: LogEntry[]; total: number; limit: number; offset: number }
  count: number
}

interface SummaryResponse {
  success: boolean
  data: LogSummary
  count: number
}

/** 타임라인 데이터 모델 */
export interface TimelineStep {
  state: string
  ts: string
  message: string
  meta?: Record<string, unknown>
}

export interface TimelineEntry {
  intent_id: string
  rule_id: number
  symbol: string
  side: 'BUY' | 'SELL'
  state: 'PROPOSED' | 'SUBMITTED' | 'FILLED' | 'BLOCKED' | 'FAILED' | 'CANCELLED'
  steps: TimelineStep[]
  started_at: string
  ended_at: string | null
  duration_ms: number | null
}

interface TimelineResponse {
  success: boolean
  data: { items: TimelineEntry[]; total: number }
  count: number
}

export const logsApi = {
  getLogs: (params?: {
    log_type?: string
    symbol?: string
    date_from?: string
    limit?: number
    offset?: number
  }) =>
    client.get<LogsResponse>('/logs', { params })
      .then(r => r.data),

  getSummary: (date?: string) =>
    client.get<SummaryResponse>('/logs/summary', { params: date ? { date } : undefined })
      .then(r => r.data),

  getTimeline: (params: {
    date_from: string
    limit?: number
    symbol?: string
    state?: string
  }) =>
    client.get<TimelineResponse>('/logs/timeline', { params })
      .then(r => r.data),
}
