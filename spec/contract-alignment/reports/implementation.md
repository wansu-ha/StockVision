# 계약 정렬 구현 보고서

> 작성일: 2026-03-08 | 상태: 구현 완료

## 변경 파일 목록

### Step 1: RuleCard v2 DSL 전환
- `frontend/src/components/RuleCard.tsx`
  - `rule.conditions`, `rule.operator`, `rule.side` 제거
  - `rule.script` 기반 요약 표시 (RuleList.tsx 패턴 동일)
  - v1 폴백: `buy_conditions`/`sell_conditions` 존재 여부로 '매수/매도 조건 (JSON)' 표시

### Step 2: cloudClient PATCH → PUT
- `frontend/src/services/cloudClient.ts` (line 79)
  - `client.patch` → `client.put` (서버가 PUT만 지원, PATCH는 405)

### Step 3: Auth 응답 키 통일
- `frontend/src/services/cloudClient.ts`
  - refresh 인터셉터: `data.data?.jwt` → `data.data?.access_token`
  - `verifyEmail`: POST(email,code) → GET(token) — 서버 메서드 일치
  - `updateProfile`: TODO stub (서버 엔드포인트 미존재)
- `frontend/src/services/auth.ts`
  - `LoginResponse.jwt` → `data: { access_token, refresh_token, expires_in }` (서버 shape 일치)
- `frontend/src/types/auth.ts`
  - `AuthResponse.jwt` → `data: { access_token, ... }` (미사용이지만 타입 정합)
- `local_server/cloud/auth_client.py` — **삭제** (token.dat 기반 레거시, 어디서도 미사용)

### Step 4: /api/variables 제거
- `frontend/src/services/rules.ts`
  - `variables()` 메서드 및 `VariablesResponse` 타입 제거
  - `local` axios 인스턴스 및 `axios` import 제거
- `frontend/src/pages/StrategyBuilder.tsx`
  - `useQuery(['variables'])` 제거
  - `AVAILABLE_INDICATORS + CONTEXT_FIELDS` 정적 목록으로 대체

### Step 5: TrafficLightStatus 매핑
- `frontend/src/components/TrafficLightStatus.tsx`
  - `broker_connected` (플랫) → `broker?.connected` (중첩) — 서버 응답 shape 정렬

### Step 6: 레거시 서비스 stub
- `frontend/src/services/api.ts` — 전체 rewrite (localhost:8000 → stub, 타입 호환 유지)
- `frontend/src/services/onboarding.ts` — stub (타입 유지, console.warn)
- `frontend/src/services/templates.ts` — stub (타입 유지, console.warn)
- `frontend/src/services/portfolio.ts` — stub (타입 유지, console.warn)

### Step 7: 레거시 dashboard 제거
- `local_server/routers/health.py`
  - `/api/dashboard` 핸들러 제거 (삭제된 `kiwoom.session` import으로 실행 불가)
- `frontend/src/services/dashboard.ts` — stub (더 이상 미사용)
- `frontend/src/components/MarketContext.tsx`
  - `dashboardApi.get` → `cloudContext.get` 전환
  - `kospi_rsi_14` → `kospi_rsi` (MarketContextData 타입 기준)

### Step 8: rules.ts CRUD → cloudRules 통일
- `frontend/src/services/rules.ts`
  - `rulesApi` CRUD 전체 제거, `conditionsToDsl` 유틸 + 타입만 유지
- `frontend/src/pages/StrategyBuilder.tsx`
  - `rulesApi.*` → `cloudRules.*` 전환
  - `rulesData?.data` → `rulesData` (cloudRules.list()가 Rule[] 직접 반환)
  - `rulesApi.toggle()` → `cloudRules.update(id, { is_active })` 통일

## 검증 결과

| 기준 | 결과 |
|------|------|
| `tsc --noEmit` | 0 errors |
| `npm run build` | 기존 12개 에러 유지 (모두 pre-existing, 우리 변경과 무관) |
| `localhost:8000` 코드 참조 | 0건 (주석 1건만 존재) |
| RuleCard conditions/operator/side | 0건 |
| refresh 인터셉터 access_token | 확인 |
| TrafficLightStatus broker.connected | 확인 |
| /api/variables 호출 | 0건 |
| rulesApi 참조 | 0건 |

## Pre-existing 빌드 에러 (미수정 — 범위 외)

| 파일 | 에러 | 원인 |
|------|------|------|
| StockSearch.tsx | Expected 1 arguments, but got 0 | cloudStocks.search() 호출 시 인자 누락 |
| AuthContext.tsx | verbatimModuleSyntax | `import { ReactNode }` → `import type` 필요 |
| AdminDashboard.tsx | Property 'users' not exist | AxiosResponse 타입 미지정 |
| ForgotPassword/Login/Register/ResetPassword.tsx | verbatimModuleSyntax | `import { FormEvent }` → `import type` 필요 |

## 커밋 안내

아래 순서로 커밋 권장:

```
커밋 1: feat(contract-alignment): Step 1-3 — RuleCard v2, PATCH→PUT, auth 키 통일
  - frontend/src/components/RuleCard.tsx
  - frontend/src/services/cloudClient.ts
  - frontend/src/services/auth.ts
  - frontend/src/types/auth.ts
  - local_server/cloud/auth_client.py (삭제)

커밋 2: feat(contract-alignment): Step 4-5 — variables 제거, TrafficLight 매핑
  - frontend/src/services/rules.ts
  - frontend/src/pages/StrategyBuilder.tsx
  - frontend/src/components/TrafficLightStatus.tsx

커밋 3: feat(contract-alignment): Step 6-7 — 레거시 stub + dashboard 전환
  - frontend/src/services/api.ts
  - frontend/src/services/onboarding.ts
  - frontend/src/services/templates.ts
  - frontend/src/services/portfolio.ts
  - frontend/src/services/dashboard.ts
  - frontend/src/components/MarketContext.tsx
  - local_server/routers/health.py

커밋 4: feat(contract-alignment): Step 8 — rules CRUD → cloudRules 통일
  - frontend/src/services/rules.ts
  - frontend/src/pages/StrategyBuilder.tsx
```
