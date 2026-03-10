/** 어드민 API 클라이언트 — /api/v1/admin/ */
import api from './cloudClient'

export const adminApi = {
  // 통계
  getStats: () => api.get('/api/v1/admin/stats'),

  // 유저
  getUsers: (params?: { page?: number; search?: string }) =>
    api.get('/api/v1/admin/users', { params }),
  updateUser: (id: string, body: Record<string, unknown>) =>
    api.patch(`/api/v1/admin/users/${id}`, body),

  // 접속 통계
  getConnectionStats: (period: string) =>
    api.get('/api/v1/admin/stats/connections', { params: { period } }),

  // 서비스 키
  getServiceKeys: () => api.get('/api/v1/admin/service-keys'),
  createServiceKey: (body: { api_key: string; api_secret: string; app_name?: string }) =>
    api.post('/api/v1/admin/service-keys', body),
  deleteServiceKey: (id: number) => api.delete(`/api/v1/admin/service-keys/${id}`),

  // 템플릿
  getTemplates: () => api.get('/api/v1/admin/templates'),
  createTemplate: (body: Record<string, unknown>) => api.post('/api/v1/admin/templates', body),
  updateTemplate: (id: number, body: Record<string, unknown>) =>
    api.put(`/api/v1/admin/templates/${id}`, body),
  deleteTemplate: (id: number) => api.delete(`/api/v1/admin/templates/${id}`),

  // 클라우드 서버 상태
  getCollectorStatus: () => api.get('/api/v1/admin/collector-status'),

  // AI 분석
  getAiStats: () => api.get('/api/v1/admin/ai/stats'),
  getAiRecent: (limit = 10) => api.get('/api/v1/admin/ai/recent', { params: { limit } }),

  // 에러 로그
  getErrors: (params?: { level?: string; limit?: number; offset?: number }) =>
    api.get('/api/v1/admin/errors', { params }),

}
