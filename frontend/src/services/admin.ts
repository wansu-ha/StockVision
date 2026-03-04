import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000' })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('jwt')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

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
  getStats: () => api.get<{ success: boolean; data: AdminStats }>('/api/admin/stats').then(r => r.data.data),
  listUsers: (page = 1) =>
    api.get<{ success: boolean; data: AdminUser[]; total: number }>(`/api/admin/users?page=${page}`).then(r => r.data),
  listTemplates: () =>
    api.get<{ success: boolean; data: AdminTemplate[] }>('/api/admin/templates').then(r => r.data.data),
  deleteTemplate: (id: number) =>
    api.delete(`/api/admin/templates/${id}`).then(r => r.data),
}
