/**
 * 전략 엔진 v2 E2E 테스트.
 *
 * 프리셋 선택, DSL 직접 편집, 모니터링 카드 렌더링을 검증한다.
 * 실제 엔진 실행은 백엔드가 필요하므로 테스트하지 않는다.
 */
import { test, expect } from '@playwright/test'
import { setupAllMocks } from './helpers/mock-auth'

test.describe('Strategy Engine v2', () => {
  test.beforeEach(async ({ page }) => {
    await setupAllMocks(page)
    await page.goto('/strategy')
    await expect(page.getByText('전략 빌더')).toBeVisible({ timeout: 10_000 })
  })

  // ------------------------------------------------------------------ V1
  test('V1: 프리셋 패널 — 템플릿 버튼 클릭 → 7개 프리셋 표시', async ({ page }) => {
    // 새 전략 폼 열기
    await page.getByText('+ 새 전략').click()
    await expect(page.getByTestId('strategy-name-input')).toBeVisible()

    // 프리셋 패널 열기
    await page.getByText('템플릿에서 시작').click()

    // 7개 프리셋 이름 모두 확인
    await expect(page.getByText('추세 추종')).toBeVisible()
    await expect(page.getByText('다단계 청산 + 트레일링')).toBeVisible()
    await expect(page.getByText('DCA (분할 매수)')).toBeVisible()
    await expect(page.getByText('브레이크이븐 + 트레일링')).toBeVisible()
    await expect(page.getByText('시간 필터 + 순차 조건')).toBeVisible()
    await expect(page.getByText('ATR 동적 청산')).toBeVisible()
    await expect(page.getByText('거래량 + 이격도 반등')).toBeVisible()
  })

  // ------------------------------------------------------------------ V2
  test('V2: 프리셋 선택 → DSL 에디터에 스크립트 반영', async ({ page }) => {
    await page.getByText('+ 새 전략').click()
    await expect(page.getByTestId('strategy-name-input')).toBeVisible()

    // 프리셋 패널 열기
    await page.getByText('템플릿에서 시작').click()
    await expect(page.getByText('추세 추종')).toBeVisible()

    // 추세 추종 프리셋 선택
    await page.getByText('추세 추종').click()

    // 프리셋 패널 닫힘 확인
    await expect(page.getByText('추세 추종')).not.toBeVisible({ timeout: 3_000 })

    // DSL 모드로 전환됨 — DslEditor textarea에 스크립트 반영
    const dslTextarea = page.locator('textarea').first()
    await expect(dslTextarea).toBeVisible()
    const value = await dslTextarea.inputValue()
    // 추세 추종 preset의 핵심 DSL 요소 확인
    expect(value).toContain('RSI')
    expect(value).toContain('→')

    // DSL 모드 버튼이 활성화 상태
    const dslToggle = page.locator('button', { hasText: 'DSL' })
    await expect(dslToggle).toHaveClass(/bg-indigo-600/)
  })

  // ------------------------------------------------------------------ V3
  test('V3: 프리셋 선택 → DCA 스크립트 내용 검증', async ({ page }) => {
    await page.getByText('+ 새 전략').click()
    await page.getByText('템플릿에서 시작').click()
    await expect(page.getByText('DCA (분할 매수)')).toBeVisible()

    await page.getByText('DCA (분할 매수)').click()

    const dslTextarea = page.locator('textarea').first()
    await expect(dslTextarea).toBeVisible()
    const value = await dslTextarea.inputValue()
    // DCA 프리셋 핵심 요소: 분할 진입 비율 두 개
    expect(value).toContain('50%')
    expect(value).toContain('30%')
  })

  // ------------------------------------------------------------------ V4
  test('V4: 프리셋 패널 닫기 — 템플릿 닫기 버튼 동작', async ({ page }) => {
    await page.getByText('+ 새 전략').click()

    // 열기
    await page.getByText('템플릿에서 시작').click()
    await expect(page.getByText('추세 추종')).toBeVisible()

    // 닫기 — 토글 버튼 텍스트가 '템플릿 닫기'로 바뀜
    await page.getByText('템플릿 닫기').click()
    await expect(page.getByText('추세 추종')).not.toBeVisible({ timeout: 3_000 })

    // 다시 열기 버튼 복원 확인
    await expect(page.getByText('템플릿에서 시작')).toBeVisible()
  })

  // ------------------------------------------------------------------ V5
  test('V5: DSL 직접 편집 — 폼 모드에서 DSL 모드 전환 후 텍스트 입력', async ({ page }) => {
    await page.getByText('+ 새 전략').click()
    await expect(page.getByTestId('strategy-name-input')).toBeVisible()

    // 초기 상태는 폼 모드
    const formToggle = page.locator('button', { hasText: '폼' })
    await expect(formToggle).toHaveClass(/bg-indigo-600/)

    // DSL 모드로 전환
    const dslToggle = page.locator('button', { hasText: 'DSL' })
    await dslToggle.click()

    // textarea 표시 확인
    const dslTextarea = page.locator('textarea').first()
    await expect(dslTextarea).toBeVisible()

    // v2 DSL 문법 입력
    await dslTextarea.fill('RSI(14) < 30 → 매수 100%\n수익률 >= 5 → 매도 전량')
    const entered = await dslTextarea.inputValue()
    expect(entered).toContain('RSI(14) < 30 → 매수 100%')
    expect(entered).toContain('수익률 >= 5 → 매도 전량')
  })

  // ------------------------------------------------------------------ V6
  test('V6: DSL 편집 후 저장 — 이름·종목 입력 시 저장 버튼 활성화', async ({ page }) => {
    await page.getByText('+ 새 전략').click()

    // 프리셋으로 DSL 채우기
    await page.getByText('템플릿에서 시작').click()
    await page.getByText('추세 추종').click()

    // 이름, 종목 입력
    await page.getByTestId('strategy-name-input').fill('v2 추세 추종 전략')
    await page.getByTestId('strategy-symbol-input').fill('005930')

    // 저장 버튼 활성화 확인
    const saveBtn = page.getByTestId('save-strategy-btn')
    await expect(saveBtn).not.toBeDisabled()
  })

  // ------------------------------------------------------------------ V7
  test('V7: 모니터링 — 기존 전략 카드 표시 (엔진 미실행 상태)', async ({ page }) => {
    // 초기 규칙 목록 (mock: RSI 과매도 전략 1개)
    await expect(page.getByTestId('strategy-card')).toHaveCount(1)
    await expect(page.getByText('RSI 과매도 전략')).toBeVisible()

    // 전략 카드에 수정/삭제 버튼 존재
    await expect(page.getByTestId('edit-strategy-btn').first()).toBeVisible()
    await expect(page.getByTestId('delete-strategy-btn').first()).toBeVisible()
  })

  // ------------------------------------------------------------------ V8
  test('V8: 프리셋 선택 후 취소 → 폼 초기화', async ({ page }) => {
    await page.getByText('+ 새 전략').click()
    await page.getByText('템플릿에서 시작').click()
    await page.getByText('ATR 동적 청산').click()

    // DSL 텍스트가 채워진 상태
    const dslTextarea = page.locator('textarea').first()
    await expect(dslTextarea).toBeVisible()

    // 취소 버튼 클릭
    await page.getByText('취소').click()

    // 폼 닫힘 — textarea 사라짐
    await expect(dslTextarea).not.toBeVisible({ timeout: 3_000 })

    // + 새 전략 버튼 복원
    await expect(page.getByText('+ 새 전략')).toBeVisible()
  })
})
