> 작성일: 2026-03-28 | 상태: 구현 완료

# StrategyBuilder E2E — 구현 계획

## 구현 순서

### Step 1: 인프라 + API mock 헬퍼

- AUTH_BYPASS는 전역 적용하지 않음 (기존 auth E2E가 깨짐)
- strategy-builder.spec.ts 내에서 beforeEach로 localStorage/cookie 토큰 주입 또는
  page.route()로 /api/v1/auth/me mock → 인증 우회
- Playwright `page.route()`로 API 응답을 mock하는 공통 헬퍼 작성

mock 대상 API:
- GET /api/v1/rules → 전략 목록
- POST /api/v1/rules → 전략 생성 (201)
- PUT /api/v1/rules/:id → 전략 수정
- DELETE /api/v1/rules/:id → 전략 삭제
- POST /api/v1/backtest/run → 백테스트 결과

**verify**: mock이 정상 응답 반환

### Step 2: data-testid 추가

StrategyBuilder, RuleList 등 컴포넌트에 테스트 선택자 추가:
- `data-testid="strategy-name-input"`
- `data-testid="strategy-symbol-input"`
- `data-testid="save-strategy-btn"`
- `data-testid="delete-strategy-btn"`
- `data-testid="backtest-btn"`
- `data-testid="strategy-card"`

**verify**: 빌드 성공, 기존 E2E 통과

### Step 3: E2E 시나리오 작성

S1~S5를 `frontend/e2e/strategy-builder.spec.ts`에 구현.

**verify**: 5개 시나리오 통과

### Step 4: 전체 검증

- `npx playwright test` 전체 통과 (기존 11 + 신규 5 = 16)
- `npm run build` 성공

## 위험 요소

- API mock이 실제 응답과 다르면 false positive
  → 실제 API 스키마에서 mock fixture 생성
- ConditionRow 동적 렌더링 → 정확한 selector 필요
  → data-testid로 안정적 선택
