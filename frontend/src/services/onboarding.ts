/**
 * 온보딩 서비스 — TODO stub
 * 레거시 백엔드(:8000) 제거. 클라우드 서버 마이그레이션 후 재구현 예정.
 */

export interface OnboardingStatus {
  step_completed: number
  risk_accepted: boolean
  is_complete: boolean
}

const STUB_WARN = (name: string) => console.warn(`[stub] ${name}: 레거시 백엔드 제거됨`)

export const onboardingApi = {
  getStatus: async (): Promise<OnboardingStatus> => {
    STUB_WARN('onboardingApi.getStatus')
    return { step_completed: 0, risk_accepted: false, is_complete: false }
  },
  completeStep: async (_n: number) => { STUB_WARN('onboardingApi.completeStep'); return { success: true } },
  acceptRisk: async () => { STUB_WARN('onboardingApi.acceptRisk'); return { success: true } },
}
