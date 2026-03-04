import axios from 'axios'

const local = axios.create({ baseURL: 'http://127.0.0.1:8765', timeout: 5000 })

export interface Condition {
  variable: string
  operator: '>' | '<' | '>=' | '<=' | '=='
  value: number
}

export interface TradingRule {
  id: number
  name: string
  stock_code: string
  side: 'BUY' | 'SELL'
  conditions: Condition[]
  quantity: number
  is_active: boolean
}

export type RuleBody = Omit<TradingRule, 'id'>

export interface Variable {
  key: string
  label: string
  current: number | null
}

export interface VariablesResponse {
  market: Variable[]
  price: Variable[]
  operators: string[]
}

export const rulesApi = {
  list: () =>
    local.get<{ success: boolean; data: TradingRule[]; count: number }>('/api/rules')
      .then(r => r.data),

  create: (body: RuleBody) =>
    local.post<{ success: boolean; data: TradingRule }>('/api/rules', body)
      .then(r => r.data),

  update: (id: number, body: RuleBody) =>
    local.put<{ success: boolean; data: TradingRule }>(`/api/rules/${id}`, body)
      .then(r => r.data),

  remove: (id: number) =>
    local.delete(`/api/rules/${id}`).then(r => r.data),

  toggle: (id: number) =>
    local.patch<{ success: boolean; data: { is_active: boolean } }>(`/api/rules/${id}/toggle`)
      .then(r => r.data),

  variables: () =>
    local.get<{ success: boolean; data: VariablesResponse }>('/api/variables')
      .then(r => r.data),
}
