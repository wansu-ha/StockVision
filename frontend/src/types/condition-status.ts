export interface ConditionDetail {
  index: number
  expr: string
  result: boolean | null
  details: Record<string, number | boolean | string | null>
}

export interface PositionInfo {
  status: string
  entry_price: number
  highest_price: number
  pnl_pct: number
  bars_held: number
  days_held: number
  remaining_ratio: number
}

export interface TriggerEntry {
  at: string
  index: number
  action: string
}

export interface ConditionStatus {
  rule_id: number
  cycle: string
  position: PositionInfo | null
  conditions: ConditionDetail[]
  action: { side: string; quantity: string } | null
  triggered_history: TriggerEntry[]
}
