// 401 인터셉터 ↔ AuthContext 동기화용 커스텀 이벤트
export const AUTH_EVENTS = {
  TOKEN_REFRESHED: 'sv-token-refreshed',
  AUTH_EXPIRED: 'sv-auth-expired',
} as const
