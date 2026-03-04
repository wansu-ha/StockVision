import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000' })

export interface BacktestSummary {
  cagr: number
  mdd: number
  sharpe: number
}

export interface TemplateCondition {
  variable: string
  operator: string
  value: number
}

export interface StrategyTemplate {
  id: number
  name: string
  description: string | null
  category: string | null
  difficulty: string | null
  rule_json: { side: string; conditions: TemplateCondition[] } | null
  backtest_summary: BacktestSummary | null
  tags: string[]
}

export const templatesApi = {
  list: () => api.get<{ success: boolean; data: StrategyTemplate[] }>('/api/templates').then(r => r.data.data),
  get: (id: number) => api.get<{ success: boolean; data: StrategyTemplate }>(`/api/templates/${id}`).then(r => r.data.data),
}
