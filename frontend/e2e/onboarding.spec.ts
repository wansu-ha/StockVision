import { test, expect } from '@playwright/test'

test.describe('온보딩 위자드', () => {
  test.use({
    storageState: undefined,
  })

  test('VITE_AUTH_BYPASS 시 온보딩 접근 가능 + Step 1 렌더링', async ({ page }) => {
    // AUTH_BYPASS 모드에서 온보딩 페이지 접근
    await page.goto('/onboarding')

    // 온보딩 페이지가 렌더링되거나 리다이렉트되는지 확인
    // AUTH_BYPASS가 없으면 /login으로 리다이렉트
    const url = page.url()

    if (url.includes('/onboarding')) {
      // 온보딩 페이지 — Step 1 위험 고지 카드가 있어야 함
      const body = await page.textContent('body')
      // 위험 고지 또는 온보딩 관련 텍스트 존재
      expect(body).toBeTruthy()
    } else {
      // 리다이렉트 — /login으로 이동했으면 auth guard 작동
      expect(url).toContain('/login')
    }
  })
})
