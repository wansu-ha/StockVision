/** 온보딩 완료 상태 관리 (localStorage 기반). */

const ONBOARDING_KEY = 'stockvision:onboarding_completed'

export function useOnboarding() {
  const completed = localStorage.getItem(ONBOARDING_KEY) === 'true'
  const complete = () => localStorage.setItem(ONBOARDING_KEY, 'true')
  const reset = () => localStorage.removeItem(ONBOARDING_KEY)
  return { completed, complete, reset }
}
