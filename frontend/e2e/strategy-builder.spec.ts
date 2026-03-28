/**
 * StrategyBuilder E2E 테스트.
 *
 * 전역 AUTH_BYPASS를 사용하지 않고 page.route()로 인증 및 API를 mock한다.
 * 기존 auth E2E(미인증 리다이렉트 테스트)가 깨지지 않는다.
 */
import { test, expect } from '@playwright/test'
import { setupAllMocks } from './helpers/mock-auth'

test.describe('StrategyBuilder E2E', () => {
  test.beforeEach(async ({ page }) => {
    await setupAllMocks(page)
    await page.goto('/strategy')
    // 인증 우회 후 페이지가 렌더링될 때까지 대기
    await expect(page.getByText('전략 빌더')).toBeVisible({ timeout: 10_000 })
  })

  // ------------------------------------------------------------------ S1
  test('S1: 전략 생성 — 폼 입력 → 저장 → 목록 표시', async ({ page }) => {
    // "새 전략" 버튼 클릭
    await page.getByText('+ 새 전략').click()

    // 폼 표시 확인
    await expect(page.getByTestId('strategy-name-input')).toBeVisible()
    await expect(page.getByTestId('strategy-symbol-input')).toBeVisible()

    // 이름, 종목 입력
    await page.getByTestId('strategy-name-input').fill('신규 테스트 전략')
    await page.getByTestId('strategy-symbol-input').fill('000660')

    // 저장 버튼 활성화 확인 후 클릭
    const saveBtn = page.getByTestId('save-strategy-btn')
    await expect(saveBtn).not.toBeDisabled()
    await saveBtn.click()

    // 저장 후 폼 닫힘 (저장 버튼 사라짐)
    await expect(saveBtn).not.toBeVisible({ timeout: 5_000 })

    // 목록에 전략 카드 표시
    await expect(page.getByTestId('strategy-card').first()).toBeVisible()
  })

  // ------------------------------------------------------------------ S2
  test('S2: 전략 편집 — 카드 수정 버튼 → 폼 열림 → 이름 수정 → 저장', async ({ page }) => {
    // 기존 전략 카드 수정 버튼 클릭
    await page.getByText('수정').first().click()

    // 폼이 열리고 기존 값이 입력돼 있어야 함
    await expect(page.getByTestId('strategy-name-input')).toBeVisible()
    const nameInput = page.getByTestId('strategy-name-input')
    await expect(nameInput).toHaveValue('RSI 과매도 전략')

    // 이름 수정
    await nameInput.fill('수정된 전략 이름')

    // 저장
    const saveBtn = page.getByTestId('save-strategy-btn')
    await expect(saveBtn).not.toBeDisabled()
    await saveBtn.click()

    // 폼 닫힘 확인
    await expect(saveBtn).not.toBeVisible({ timeout: 5_000 })
  })

  // ------------------------------------------------------------------ S3
  test('S3: 전략 삭제 — 삭제 버튼 → 목록에서 사라짐', async ({ page }) => {
    // 초기에 전략 카드 1개 존재
    await expect(page.getByTestId('strategy-card')).toHaveCount(1)

    // 삭제 버튼 클릭
    await page.getByTestId('delete-strategy-btn').first().click()

    // 삭제 후 카드 0개 (또는 "저장된 전략이 없습니다" 텍스트)
    await expect(page.getByTestId('strategy-card')).toHaveCount(0, { timeout: 5_000 })
  })

  // ------------------------------------------------------------------ S4
  test('S4: 유효성 검증 — 빈 이름/종목 시 저장 버튼 비활성화', async ({ page }) => {
    // 폼 열기
    await page.getByText('+ 새 전략').click()
    await expect(page.getByTestId('strategy-name-input')).toBeVisible()

    const saveBtn = page.getByTestId('save-strategy-btn')

    // 이름, 종목 모두 비어 있으면 저장 버튼 비활성화
    await expect(saveBtn).toBeDisabled()

    // 이름만 입력해도 종목 없으면 비활성화
    await page.getByTestId('strategy-name-input').fill('테스트')
    await expect(saveBtn).toBeDisabled()

    // 종목까지 입력하면 활성화
    await page.getByTestId('strategy-symbol-input').fill('005930')
    await expect(saveBtn).not.toBeDisabled()
  })

  // ------------------------------------------------------------------ S5
  test('S5: 백테스트 버튼 — 클릭 시 인라인 결과 표시', async ({ page }) => {
    // 기존 전략 수정 폼 열기
    await page.getByText('수정').first().click()
    await expect(page.getByTestId('backtest-btn')).toBeVisible()

    // 백테스트 실행
    await page.getByTestId('backtest-btn').click()

    // 결과 패널 확인 (총 수익률 MetricCard 표시)
    await expect(page.getByText('총 수익률')).toBeVisible({ timeout: 10_000 })
  })
})
