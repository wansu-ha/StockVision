/**
 * E2E 테스트용 API mock 헬퍼.
 *
 * 전역 AUTH_BYPASS 없이 개별 spec 파일에서 인증 및 API를 mock한다.
 * 기존 auth E2E(미인증 리다이렉트 테스트)가 깨지지 않도록
 * 이 헬퍼는 명시적으로 호출하는 spec에서만 동작한다.
 */
import type { Page, Route } from '@playwright/test'

const CLOUD_URL = 'http://localhost:4010'

/** 가짜 Rule fixture */
export const MOCK_RULES = [
  {
    id: 1,
    name: 'RSI 과매도 전략',
    symbol: '005930',
    script: 'buy_if: kospi_rsi_14 < 30\nsell_if: kospi_rsi_14 > 70',
    execution: { order_type: 'MARKET', qty_type: 'FIXED', qty_value: 10 },
    trigger_policy: { frequency: 'ONCE_PER_DAY' },
    qty: 10,
    is_active: true,
    priority: 0,
    version: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: null,
    buy_conditions: null,
    sell_conditions: null,
    order_type: 'MARKET',
    max_position_count: 1,
    budget_ratio: 0.1,
  },
]

/** 백테스트 결과 fixture */
export const MOCK_BACKTEST_RESULT = {
  success: true,
  data: {
    id: 42,
    summary: {
      total_return_pct: 12.5,
      cagr: 8.3,
      max_drawdown_pct: -5.2,
      win_rate: 0.6,
      profit_factor: 1.8,
      sharpe_ratio: 1.2,
      avg_hold_bars: 3,
      trade_count: 10,
      total_commission: 5000,
      total_tax: 2000,
      total_slippage: 1000,
    },
    equity_curve: [100, 105, 103, 108, 112],
    trades: [],
  },
}

/**
 * 인증 mock 설정.
 * sessionStorage에 가짜 JWT를 주입해 isAuthenticated = true로 만들고,
 * ConsentGate를 통과하도록 consent/status도 mock한다.
 */
export async function setupAuthMock(page: Page): Promise<void> {
  // ConsentGate API mock (모든 동의 최신 상태로 응답)
  await page.route(`${CLOUD_URL}/api/v1/legal/consent/status`, (route: Route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          terms:      { agreed_version: '1.0', agreed_at: '2026-01-01', latest_version: '1.0', up_to_date: true },
          privacy:    { agreed_version: '1.0', agreed_at: '2026-01-01', latest_version: '1.0', up_to_date: true },
          disclaimer: { agreed_version: '1.0', agreed_at: '2026-01-01', latest_version: '1.0', up_to_date: true },
        },
      }),
    })
  })

  // 페이지 이동 전 sessionStorage에 가짜 JWT 주입 (addInitScript는 다음 navigation에 적용)
  await page.addInitScript(() => {
    sessionStorage.setItem('sv_jwt', 'mock-jwt-token-for-e2e')
  })
}

/**
 * Rules API mock 설정.
 * CRUD 전 엔드포인트를 가로채 고정된 fixture를 반환한다.
 * 생성/수정 후 목록이 갱신되는 흐름을 시뮬레이션하기 위해
 * 내부 상태를 클로저로 관리한다.
 */
export async function setupRulesMock(page: Page): Promise<void> {
  // 내부 상태 (클로저)
  let rules = [...MOCK_RULES]
  let nextId = 2

  // GET /api/v1/rules, POST /api/v1/rules
  await page.route(`${CLOUD_URL}/api/v1/rules`, async (route: Route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: rules, count: rules.length }),
      })
    } else if (route.request().method() === 'POST') {
      const body = JSON.parse(route.request().postData() ?? '{}')
      const newRule = { ...MOCK_RULES[0], ...body, id: nextId++ }
      rules = [...rules, newRule]
      route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: newRule }),
      })
    } else {
      route.continue()
    }
  })

  // PUT /api/v1/rules/:id, DELETE /api/v1/rules/:id
  await page.route(`${CLOUD_URL}/api/v1/rules/**`, async (route: Route) => {
    const method = route.request().method()
    const url = route.request().url()
    const idMatch = url.match(/\/api\/v1\/rules\/(\d+)/)
    const id = idMatch ? parseInt(idMatch[1]) : null

    if (method === 'PUT' && id !== null) {
      const body = JSON.parse(route.request().postData() ?? '{}')
      rules = rules.map(r => r.id === id ? { ...r, ...body } : r)
      const updated = rules.find(r => r.id === id)
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: updated }),
      })
    } else if (method === 'DELETE' && id !== null) {
      rules = rules.filter(r => r.id !== id)
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      })
    } else {
      route.continue()
    }
  })
}

/**
 * 백테스트 API mock 설정.
 */
export async function setupBacktestMock(page: Page): Promise<void> {
  await page.route(`${CLOUD_URL}/api/v1/backtest/run`, (route: Route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_BACKTEST_RESULT),
    })
  })
}

/**
 * 전체 mock 설정 (인증 + Rules + Backtest).
 * strategy-builder.spec.ts의 beforeEach에서 호출.
 */
export async function setupAllMocks(page: Page): Promise<void> {
  await setupAuthMock(page)
  await setupRulesMock(page)
  await setupBacktestMock(page)

  // 로컬 서버 요청 차단 (flaky 방지)
  await page.route('http://localhost:4020/**', (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ success: true }) })
  })
}
