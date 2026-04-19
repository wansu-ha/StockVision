# 프론트엔드 테스트 커버리지 확대 (v2)

> 작성일: 2026-04-19 | 상태: 초안 | 선행: `spec/frontend-test-expansion/` (구현 완료, FT-1~FT-5)

---

## 목표

`frontend-test-expansion` v1에서 핵심 유틸리티 4건 + StrategyBuilder E2E 1건을 구축했다.
이 spec은 그 위에 **MainDashboard/Settings E2E + 핵심 hooks/components unit test + services 에러 핸들링**을
추가하여 회귀 감지 영역을 넓힌다.

---

## 배경

현황 (2026-04-19):

| 영역 | 파일 수 | 커버 대상 |
|---|---|---|
| E2E (Playwright) | 7 | admin, auth, backtest, onboarding, strategy, strategy-v2, strategy-builder |
| Unit (Vitest) | 4 | dslConverter, dslParser, dslParserV2, e2eCrypto |

**사각지대**:
- 메인 화면(MainDashboard) — 사용자가 가장 많이 보는 페이지인데 E2E 없음
- Settings — 증권사 연동 + 법적 동의 복합 플로우, E2E 없음
- Hooks — 실시간 데이터(`useLocalBridgeWS`, `useAccountStatus`) 등 핵심 로직이 unit test 없음
- Components — 큰 컴포넌트(`PriceChart` 454줄, `ListView` 442줄, `DetailView` 504줄) unit test 없음
- Services — `cloudClient`/`localClient` 에러 핸들링(`apiError`) test 없음
- Stores — Zustand 스토어(`alertStore`, `toastStore`) test 없음

이 중 ROI 기준 우선순위가 높은 것만 이 spec 범위에 포함.

---

## 범위

### 포함

1. **FT2-1: MainDashboard E2E** — 로그인 → 대시보드 → 종목 상세 → 관심종목 토글
2. **FT2-2: Settings E2E** — 증권사 키 등록 → 연결 확인 → 해제
3. **FT2-3: 핵심 hooks unit test** — `useAccountStatus`, `useStockData`, `useLocalBridgeWS`
4. **FT2-4: 큰 컴포넌트 unit test** — `PriceChart`, `ListView`, `DetailView` 중 2개 이상
5. **FT2-5: services 에러 핸들링** — `apiError` util + `cloudClient`/`localClient` 타임아웃/4xx/5xx
6. **FT2-6: Zustand store** — `alertStore`, `toastStore` 상태 전이

### 미포함

- 비주얼 리그레션 (스크린샷 diff) — 별도 논의
- 성능 테스트 (Lighthouse) — 별도 논의
- 모바일 뷰포트 E2E — 별도 논의
- Admin 페이지 심화 E2E — `admin.spec.ts`로 스모크 확보됨

---

## FT2-1: MainDashboard E2E

**수용 기준**:
- [ ] 로그인 → `/`로 리디렉션 → `UnifiedLayout` 렌더링
- [ ] 종목 리스트(`ListView`) 로딩 확인 (data-testid 필요)
- [ ] 종목 클릭 → `DetailView` 전환 + 차트(`PriceChart`) 표시
- [ ] 관심종목 하트 토글 → 낙관적 UI 업데이트 확인
- [ ] 헤더 네비 전환 (종목/전략/체결/설정)

**예상 테스트 수**: 6~8개

**파일**:
- `frontend/e2e/dashboard.spec.ts` (신규)
- data-testid 추가: `ListView`, `DetailView`, `PriceChart`

---

## FT2-2: Settings E2E

**수용 기준**:
- [ ] `/settings` 접근 → 증권사 키 폼 렌더링
- [ ] 잘못된 키 입력 → 에러 표시 (`ApiError` 처리)
- [ ] 올바른 키 입력 → 로컬 서버에 암호화 저장 (E2E 모드에선 mock)
- [ ] 연결 상태 배지 업데이트
- [ ] 키 해제 → 상태 초기화

**예상 테스트 수**: 5~7개

**파일**:
- `frontend/e2e/settings.spec.ts` (신규)
- data-testid 추가: `BrokerKeyForm`, `ConnectionStatus`

---

## FT2-3: 핵심 hooks unit test

**설명**: 실시간 상태/서버 상태 훅은 컴포넌트보다 실패 확률이 높고, mock으로 test 가능.

**수용 기준**:
- [ ] `useAccountStatus` — 연결/미연결/로딩 상태
- [ ] `useStockData` — 캐시, refetch, 에러 상태
- [ ] `useLocalBridgeWS` — WS 연결/재연결/메시지 수신 (mock ws)
- [ ] React Query mock 패턴 확립 (재사용 가능)

**예상 테스트 수**: 20~25개

**파일**:
- `frontend/src/hooks/__tests__/useAccountStatus.test.tsx` (신규)
- `frontend/src/hooks/__tests__/useStockData.test.tsx` (신규)
- `frontend/src/hooks/__tests__/useLocalBridgeWS.test.tsx` (신규)

---

## FT2-4: 큰 컴포넌트 unit test

**우선순위**: `ListView` > `DetailView` > `PriceChart` (PriceChart는 `lightweight-charts`라 테스트 난이도 ↑)

**수용 기준**:
- [ ] `ListView` — 빈 상태, 종목 렌더링, 클릭 핸들러, 정렬
- [ ] `DetailView` (선택) — 종목 데이터 렌더링, 빈 상태
- [ ] `@testing-library/react` 기반

**예상 테스트 수**: 10~15개

**파일**:
- `frontend/src/components/main/__tests__/ListView.test.tsx` (신규)
- `frontend/src/components/main/__tests__/DetailView.test.tsx` (신규, 선택)

---

## FT2-5: services 에러 핸들링

**수용 기준**:
- [ ] `apiError.ts` — HTTP 상태별 `ApiError` 생성, 메시지 포매팅
- [ ] `cloudClient` — 401 → 로그아웃, 5xx → Sentry 리포트, 타임아웃 처리
- [ ] `localClient` — 오프라인 폴백, 재시도 정책
- [ ] `MSW` 또는 `fetch mock`로 모의 응답

**예상 테스트 수**: 15~20개

**파일**:
- `frontend/src/utils/__tests__/apiError.test.ts` (신규)
- `frontend/src/services/__tests__/cloudClient.test.ts` (신규)
- `frontend/src/services/__tests__/localClient.test.ts` (신규)

---

## FT2-6: Zustand store

**수용 기준**:
- [ ] `alertStore` — 추가/제거/읽음 처리/자동 만료
- [ ] `toastStore` — 토스트 큐, 타임아웃, 중복 방지
- [ ] Store 초기화 패턴 확립

**예상 테스트 수**: 10~12개

**파일**:
- `frontend/src/stores/__tests__/alertStore.test.ts` (신규)
- `frontend/src/stores/__tests__/toastStore.test.ts` (신규)

---

## 커버리지 목표

| 영역 | 현재 (v1 이후) | 목표 (v2 이후) |
|------|------|------|
| Unit 테스트 파일 | 4 | 13+ |
| E2E 시나리오 | 7 | 9+ |
| 전체 페이지 E2E 커버 | 4/25 (이전) | 6/25 |
| Hooks 커버 | 0 | 3 (핵심) |
| Services 커버 | 0 | 2 + apiError util |
| Stores 커버 | 0 | 2 |

---

## 비포함 사항 (명시적으로)

- `OpsPanel`, `RuleCard`, `ConsentGate` 등 중간 크기 컴포넌트 — 다음 iteration
- `PriceChart` — `lightweight-charts` canvas 모킹 난이도로 인해 보류
- Visual regression — Playwright 스크린샷 비교는 별도 spec
- 접근성(a11y) 테스트 — 별도 spec
- 성능 예산 — Lighthouse CI 별도 설정

---

## 진행 순서 제안

1. **FT2-5** (services 에러 핸들링) → 가장 안정적 산출, mock 패턴 확립
2. **FT2-6** (Zustand store) → 순수 JS 로직, 빠른 성과
3. **FT2-3** (hooks) → React Query mock 패턴 재사용
4. **FT2-4** (컴포넌트) → 위 기반 활용
5. **FT2-1, FT2-2** (E2E) → Playwright 실행 환경 필요, 상대적으로 느림

단계마다 `npm run test` + `npm run e2e` 통과 확인.

---

## 위험 요소

- **WS mock 복잡도**: `useLocalBridgeWS`는 WebSocket mock이 까다로움 — `mock-socket` 라이브러리 고려
- **Playwright CI**: 현재 CI 설정과 충돌 확인 필요
- **lightweight-charts**: canvas 기반이라 JSDOM/happy-dom에서 동작 안 함 — `PriceChart` test 보류 이유

---

## 참고

- 선행: `spec/frontend-test-expansion/` (구현 완료) — 유틸 4종 + StrategyBuilder E2E 기반 구축
- `memory/MEMORY.md` — 사용자 선호(spec/plan 셀프 리뷰 필수)
