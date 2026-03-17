import axios from 'axios'

const CLOUD_URL = import.meta.env.VITE_CLOUD_API_URL || 'http://localhost:4010'
const BASE = `${CLOUD_URL}/api/v1/auth`

export interface LoginResponse {
  success: boolean
  data: {
    access_token: string
    refresh_token: string
    expires_in: number
  }
}

export const authApi = {
  register: (email: string, password: string, nickname?: string, termsAgreed?: boolean, privacyAgreed?: boolean) =>
    axios.post(`${BASE}/register`, { email, password, nickname, terms_agreed: termsAgreed, privacy_agreed: privacyAgreed }),

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
