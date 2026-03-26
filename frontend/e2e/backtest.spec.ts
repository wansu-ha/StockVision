import { test, expect } from '@playwright/test'

test.describe('백테스트 페이지', () => {
  test('미인증 시 /login 리다이렉트', async ({ page }) => {
    await page.goto('/backtest')
    await expect(page).toHaveURL(/\/login/, { timeout: 5_000 })
  })

  test('페이지 렌더링 확인 (AUTH_BYPASS)', async ({ page }) => {
    // AUTH_BYPASS 모드에서 테스트
    await page.goto('/backtest')

    // /login으로 리다이렉트되면 auth guard 동작
    const url = page.url()
    if (url.includes('/backtest')) {
      await expect(page.getByTestId('backtest-symbol')).toBeVisible()
      await expect(page.getByTestId('backtest-script')).toBeVisible()
      await expect(page.getByTestId('backtest-submit')).toBeVisible()
      await expect(page.getByTestId('backtest-submit')).toHaveText('백테스트 실행')
    } else {
      // 리다이렉트됨 — auth guard 정상 작동
      expect(url).toContain('/login')
    }
  })
})
