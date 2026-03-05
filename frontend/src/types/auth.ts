/** 인증 관련 타입 */

export interface User {
  email: string
  role: 'user' | 'admin'
  nickname?: string
  created_at?: string
}

export interface AuthResponse {
  user: User
  jwt: string
  refresh_token: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  nickname?: string
}

export interface VerifyEmailRequest {
  email: string
  code: string
}
