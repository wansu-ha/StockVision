import { test, expect } from '@playwright/test'

test.describe('전략 페이지', () => {
  test('미인증 상태에서 /strategies 접근 → /login 리다이렉트', async ({ page }) => {
    await page.goto('/strategies')

    // ProtectedRoute가 /login으로 리다이렉트
    await expect(page).toHaveURL(/\/login/, { timeout: 5_000 })
  })

  test('미인증 상태에서 /strategy 접근 → /login 리다이렉트', async ({ page }) => {
    await page.goto('/strategy')

    await expect(page).toHaveURL(/\/login/, { timeout: 5_000 })
  })
})
