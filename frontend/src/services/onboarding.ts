import axios from 'axios'

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000' })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('jwt')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

export interface OnboardingStatus {
  step_completed: number
  risk_accepted: boolean
  is_complete: boolean
}

export const onboardingApi = {
  getStatus: () => api.get<{ success: boolean; data: OnboardingStatus }>('/api/onboarding/status').then(r => r.data.data),
  completeStep: (n: number) => api.post(`/api/onboarding/step/${n}`).then(r => r.data),
  acceptRisk: () => api.post('/api/onboarding/accept-risk').then(r => r.data),
}
