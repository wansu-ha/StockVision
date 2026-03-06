import axios from 'axios'
import type { Rule, CreateRulePayload, UpdateRulePayload } from '../types/strategy'

const CLOUD_URL = import.meta.env.VITE_CLOUD_API_URL || 'http://localhost:4010'
const cloud = axios.create({ baseURL: CLOUD_URL, timeout: 5000 })

// v1 호환용 (로컬 서버)
const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'
const local = axios.create({ baseURL: LOCAL_URL, timeout: 5000 })

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

export interface VariablesResponse {
  market: Variable[]
  price: Variable[]
  operators: string[]
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

export const rulesApi = {
  /** 규칙 목록 (클라우드 서버) */
  list: () =>
    cloud.get<{ success: boolean; data: Rule[]; version: number; count: number }>('/api/v1/rules')
      .then(r => r.data),

  /** 규칙 생성 */
  create: (body: CreateRulePayload) =>
    cloud.post<{ success: boolean; data: Rule }>('/api/v1/rules', body)
      .then(r => r.data),

  /** 규칙 수정 */
  update: (id: number, body: UpdateRulePayload) =>
    cloud.put<{ success: boolean; data: Rule }>(`/api/v1/rules/${id}`, body)
      .then(r => r.data),

  /** 규칙 삭제 */
  remove: (id: number) =>
    cloud.delete(`/api/v1/rules/${id}`).then(r => r.data),

  /** 규칙 토글 (is_active) */
  toggle: (id: number, isActive: boolean) =>
    cloud.put<{ success: boolean; data: Rule }>(`/api/v1/rules/${id}`, { is_active: isActive })
      .then(r => r.data),

  /** 변수 목록 (로컬 서버 — v1 호환) */
  variables: () =>
    local.get<{ success: boolean; data: VariablesResponse }>('/api/variables')
      .then(r => r.data),
}
