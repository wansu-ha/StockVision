import axios from 'axios'

const BASE = 'http://localhost:8000/api/auth'

export interface LoginResponse {
  success: boolean
  jwt: string
  refresh_token: string
  expires_in: number
}

export const authApi = {
  register: (email: string, password: string, nickname?: string) =>
    axios.post(`${BASE}/register`, { email, password, nickname }),

  verifyEmail: (token: string) =>
    axios.get(`${BASE}/verify-email`, { params: { token } }),

  login: (email: string, password: string) =>
    axios.post<LoginResponse>(`${BASE}/login`, { email, password }),

  refresh: (refresh_token: string) =>
    axios.post<LoginResponse>(`${BASE}/refresh`, { refresh_token }),

  logout: (refresh_token: string) =>
    axios.post(`${BASE}/logout`, { refresh_token }),

  forgotPassword: (email: string) =>
    axios.post(`${BASE}/forgot-password`, { email }),

  resetPassword: (token: string, new_password: string) =>
    axios.post(`${BASE}/reset-password`, { token, new_password }),
}
