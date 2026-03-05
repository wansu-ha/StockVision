/** 어드민 API 클라이언트 — /api/admin/ */
import api from './cloudClient'

// 기존 타입 유지 (하위 호환)
export interface AdminStats {
  users: { total: number; active_30d: number; new_7d: number; onboarding_done: number }
  templates: { total: number; active: number }
}

export interface AdminUser {
  id: string
  email: string
  nickname: string | null
  role: string
  email_verified: boolean
  created_at: string
}

export interface AdminTemplate {
  id: number
  name: string
  category: string | null
  difficulty: string | null
  is_active: boolean
  backtest_summary: { cagr: number; mdd: number; sharpe: number } | null
  tags: string[]
}

export const adminApi = {
  // 통계
  getStats: () => api.get('/api/admin/stats'),

  // 유저
  getUsers: (params?: { page?: number; search?: string }) =>
    api.get('/api/admin/users', { params }),
  updateUser: (id: string, body: Record<string, unknown>) =>
    api.patch(`/api/admin/users/${id}`, body),

  // 접속 통계
  getConnectionStats: (period: string) =>
    api.get('/api/admin/stats/connections', { params: { period } }),

  // 서비스 키
  getServiceKeys: () => api.get('/api/admin/service-keys'),
  createServiceKey: (body: { source: string; key: string; description?: string }) =>
    api.post('/api/admin/service-keys', body),
  deleteServiceKey: (id: number) => api.delete(`/api/admin/service-keys/${id}`),

  // 템플릿
  getTemplates: () => api.get('/api/admin/templates'),
  createTemplate: (body: Record<string, unknown>) => api.post('/api/admin/templates', body),
  updateTemplate: (id: number, body: Record<string, unknown>) =>
    api.put(`/api/admin/templates/${id}`, body),
  deleteTemplate: (id: number) => api.delete(`/api/admin/templates/${id}`),

  // 시세 데이터 상태
  getDataStatus: () => api.get('/api/admin/data/status'),

  // 에러 로그
  getErrors: (params?: { level?: string; limit?: number; offset?: number }) =>
    api.get('/api/admin/errors', { params }),

  // 하위 호환 (기존 코드용)
  listUsers: (page = 1) =>
    api.get(`/api/admin/users?page=${page}`).then((r) => r.data),
  listTemplates: () =>
    api.get('/api/admin/templates').then((r) => r.data.data),
}
