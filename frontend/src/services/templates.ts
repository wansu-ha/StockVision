/**
 * 전략 템플릿 서비스 — TODO stub
 * 레거시 백엔드(:8000) 제거. 클라우드 서버 마이그레이션 후 재구현 예정.
 */

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

const STUB_WARN = (name: string) => console.warn(`[stub] ${name}: 레거시 백엔드 제거됨`)

export const templatesApi = {
  list: async (): Promise<StrategyTemplate[]> => { STUB_WARN('templatesApi.list'); return [] },
  get: async (_id: number): Promise<StrategyTemplate> => { STUB_WARN('templatesApi.get'); return {} as StrategyTemplate },
}
