import { test, expect } from '@playwright/test'

test.describe('로그인 페이지', () => {
  test('로그인 폼 렌더링 확인', async ({ page }) => {
    await page.goto('/login')

    // 폼 요소 존재 확인
    await expect(page.getByTestId('login-email')).toBeVisible()
    await expect(page.getByTestId('login-password')).toBeVisible()
    await expect(page.getByTestId('login-submit')).toBeVisible()
    await expect(page.getByTestId('login-submit')).toHaveText('로그인')
  })

  test('빈 폼 제출 시 HTML5 validation', async ({ page }) => {
    await page.goto('/login')

    // 빈 상태로 제출 시도 — required 필드로 인해 제출 안 됨
    await page.getByTestId('login-submit').click()

    // URL 변경 없음 (로그인 페이지 유지)
    expect(page.url()).toContain('/login')
  })

  test('잘못된 자격증명 시 에러 표시', async ({ page }) => {
    await page.goto('/login')

    await page.getByTestId('login-email').fill('wrong@test.com')
    await page.getByTestId('login-password').fill('wrongpass')
    await page.getByTestId('login-submit').click()

    // API 에러 또는 네트워크 에러 메시지 표시 (cloud_server 미실행 시)
    // 에러 영역이 나타나는지 확인 (정확한 메시지는 서버 상태에 따라 다름)
    const errorArea = page.locator('.text-red-400')
    await expect(errorArea).toBeVisible({ timeout: 10_000 })
  })

  test('회원가입 링크 동작', async ({ page }) => {
    await page.goto('/login')

    await page.getByText('회원가입').click()
    await expect(page).toHaveURL(/\/register/)
  })
})
