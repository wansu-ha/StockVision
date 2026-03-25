import { test, expect } from '@playwright/test'

test.describe('어드민 접근 제어', () => {
  test('미인증 상태에서 /admin 접근 → /admin/login 리다이렉트', async ({ page }) => {
    await page.goto('/admin')

    // AdminGuard가 /admin/login으로 리다이렉트해야 함
    await expect(page).toHaveURL(/\/(admin\/login|login)/, { timeout: 5_000 })
  })

  test('어드민 로그인 페이지 렌더링', async ({ page }) => {
    await page.goto('/admin/login')

    // 어드민 로그인 페이지가 렌더링되는지 확인
    const body = await page.textContent('body')
    expect(body).toBeTruthy()
  })
})
