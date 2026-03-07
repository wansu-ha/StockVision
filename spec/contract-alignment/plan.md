# 계약 정렬 구현 계획 — Phase 3 프론트/클라우드/로컬

> 작성일: 2026-03-08 | 상태: 초안

## 배경

Phase 3 아키텍처(3프로세스: 프론트·클라우드·로컬)로 전환하면서
레거시 backend(:8000) 기반 코드와 신규 cloud_server(:4010)/local_server(:4020) 코드가
프론트엔드에서 혼재하고 있다. 타입 정의·API 호출·응답 shape가 레이어마다 어긋나서
주 경로가 불안정하다.

## 목표

1. 규칙 모델 + 인증 응답 타입 통일
2. 상태 모델 통일
3. 레거시(:8000) 의존 제거

**기준**: cloud_server(:4010) + local_server(:4020) 코드가 유일한 진실의 원천.
legacy backend(:8000)에 맞추지 않는다.

---

## 현황 분석 (코드 기반)

### A. 규칙 모델 — v1/v2 혼재

| 레이어 | 현황 |
|--------|------|
| **DB 모델** (`cloud_server/models/rule.py`) | v2 필드(script, execution, trigger_policy, priority, version) + v1 필드(buy/sell_conditions, order_type, qty, max_position_count, budget_ratio) 공존. 정상 — 마이그레이션 호환. |
| **API 스키마** (`cloud_server/api/rules.py`) | v2 + v1 모두 수용. 응답은 `_rule_to_dict()`로 전체 필드 반환. PUT 메서드 사용. |
| **프론트 타입** (`frontend/src/types/strategy.ts`) | `Rule` 인터페이스에 v2(script, execution, trigger_policy) + v1(buy/sell_conditions, order_type, qty, max_position_count, budget_ratio) 공존. |
| **프론트 서비스 — rules.ts** | cloudClient로 CRUD 호출. **`/api/variables` 호출이 localhost:4020으로 가지만 해당 엔드포인트가 local_server에 존재하지 않음** → 런타임 404. |
| **프론트 서비스 — cloudClient.ts** | `cloudRules.update`가 `PATCH`인데, cloud_server는 `PUT`만 제공 → 405 에러. |
| **RuleCard.tsx** | `rule.conditions` (존재하지 않는 필드), `rule.operator`, `rule.side` 참조 → **TS 빌드 에러**. Rule 타입에 이 세 필드가 없어서 `tsc --noEmit`에서 에러가 난다. 현재 전체 빌드가 통과하는 것은 이 컴포넌트가 StrategyList 경로에서만 사용되고 Vite dev 서버가 타입 에러를 무시하기 때문이며, 엄격 빌드(`tsc`)에서는 실패한다. |
| **StrategyList.tsx** | `cloudRules.list()` 반환값이 `Rule[]`인데, `cloudRules.list`는 `r.data.data ?? r.data`로 언랩 → 반환 타입 불확실. |
| **StrategyBuilder.tsx** | `rulesApi.variables()` 호출 → 존재하지 않는 엔드포인트. `conditionsToDsl` 폼 변환기는 동작하나, 변수 목록 없이 폼이 무의미. |
| **엔진** (`local_server/engine/evaluator.py`) | v2 DSL + v1 JSON 폴백 모두 지원. 정상. |

### B. 인증 응답 타입 — 키 이름 불일치

| 위치 | 응답 shape |
|------|-----------|
| **cloud_server/api/auth.py** login/refresh | `{ success, data: { access_token, refresh_token, expires_in } }` |
| **frontend/src/services/auth.ts** `LoginResponse` | `{ success, jwt, refresh_token, expires_in }` — **`jwt` 키 기대, 서버는 `data.access_token`** |
| **frontend/src/services/cloudClient.ts** refresh 인터셉터 | `data.data?.jwt ?? data.jwt` — **서버가 보내는 `access_token`을 읽지 못함** |
| **frontend/src/context/AuthContext.tsx** | `res.data.access_token` 사용 — **정상** (cloudAuth가 `r.data` 반환) |

| **frontend/src/services/cloudClient.ts** `cloudAuth.verifyEmail` | POST 사용 — **서버는 GET만 수용** |
| **frontend/src/services/cloudClient.ts** `cloudAuth.updateProfile` | PATCH `/api/v1/auth/profile` — **서버에 해당 엔드포인트 없음** |

**결론**: AuthContext는 올바르게 작동하나, `auth.ts`의 `LoginResponse`와 cloudClient의 refresh 인터셉터가 잘못된 키를 참조함. 추가로 verifyEmail 메서드 불일치와 updateProfile 미존재 엔드포인트 문제가 있음.

### C. 상태 모델 — 구조 불일치

| 위치 | 현황 |
|------|------|
| **local_server/routers/status.py** | `{ success, data: { server, broker: { connected, has_credentials }, strategy_engine: { running } } }` |
| **TrafficLightStatus.tsx** | `localRes?.data?.broker_connected` — **중첩 구조 무시**, `broker.connected`가 아닌 `broker_connected` 참조 → 항상 `undefined` → 항상 red |
| **frontend/src/types/ui.ts** | `ServerStatus`에 engine 필드 없음 — cloud/local/broker만 정의 |
| **dashboard.ts** | `DashboardData.broker_connected` — 로컬 서버에 `/api/dashboard` 존재하나 레거시 코드(kiwoom.session import) → 실행 불가 |

### D. 레거시 의존 — localhost:8000

| 파일 | 의존 내용 |
|------|----------|
| **services/api.ts** | `localhost:8000` 하드코딩, stockApi·aiAnalysisApi·tradingApi·healthApi |
| **services/onboarding.ts** | `localhost:8000`, `/api/onboarding/*` — cloud/local에 없는 API |
| **services/templates.ts** | `localhost:8000`, `/api/templates/*` — cloud/local에 없는 API |
| **services/portfolio.ts** | `localhost:8000`, `/api/v1/portfolio/*` — cloud/local에 없는 API |
| **pages/StockDetail.tsx** | `stockApi` (api.ts) import |
| **pages/Trading.tsx** | `tradingApi, stockApi` (api.ts) import |
| **components/AIStockAnalysis.tsx** | `aiAnalysisApi` (api.ts) import |
| **pages/Portfolio.tsx** | `portfolioApi` (portfolio.ts) import |
| **pages/Templates.tsx** | `templatesApi` (templates.ts) import |
| **pages/Onboarding.tsx** | `onboardingApi` (onboarding.ts) import |
| **components/MarketContext.tsx** | `dashboardApi` (dashboard.ts) → localhost:4020 `/api/dashboard` (레거시 핸들러) |
| **routers/health.py** `/api/dashboard` | `from kiwoom.session import get_session` 등 레거시 import → 실행 불가 |

---

## 구현 계획

### Step 1: RuleCard.tsx 빌드 브레이킹 수정 (즉시)

**문제**: `rule.conditions`, `rule.operator`, `rule.side` 참조 — Rule 타입에 없는 필드.
**조치**: v2 기준으로 RuleCard 렌더링 로직 교체.

```
수정 파일:
  frontend/src/components/RuleCard.tsx
```

변경 내용:
- `rule.conditions.length` → `rule.script` 유무로 요약 표시
- `rule.operator` → 제거
- `rule.side` → 제거 (v2에서는 script가 매수/매도 모두 포함)
- script가 있으면 첫 줄 미리보기, 없으면 "(JSON 조건)" 표시
- RuleList.tsx와 동일한 패턴 사용

**verify**: `tsc --noEmit` 통과, 런타임 에러 없음

### Step 2: cloudClient.ts PATCH → PUT 수정

**문제**: `cloudRules.update`가 PATCH를 보내지만 서버는 PUT만 수용.
**조치**: `.patch` → `.put` 변경.

```
수정 파일:
  frontend/src/services/cloudClient.ts (79행)
```

**verify**: `cloudRules.update` 호출 시 405 에러 제거

### Step 3: 인증 응답 키 통일

**문제**: auth.ts의 LoginResponse와 cloudClient의 refresh 인터셉터가 `jwt` 키를 기대하지만, 서버는 `data.access_token`을 반환.

```
수정 파일:
  frontend/src/services/auth.ts
  frontend/src/services/cloudClient.ts (38-39행)
```

변경 내용:
- `auth.ts`: `LoginResponse` 타입을 `{ success: boolean; data: { access_token: string; refresh_token: string; expires_in: number } }`로 수정
- `cloudClient.ts` 인터셉터: `data.data?.jwt ?? data.jwt` → `data.data?.access_token` 수정
- `cloudClient.ts` `cloudAuth.verifyEmail`: POST → GET + query param 방식으로 수정 (서버는 GET만 수용)
- `cloudClient.ts` `cloudAuth.updateProfile`: 서버에 `/api/v1/auth/profile` 엔드포인트 없음 → TODO 주석 처리
- `types/auth.ts`: `AuthResponse`의 `jwt` → `access_token` 수정 (현재 미사용이지만 타입 정합성)
- `local_server/cloud/auth_client.py`: token.dat 기반 레거시, 어디서도 미사용 → 삭제

```
수정 파일:
  frontend/src/services/auth.ts
  frontend/src/services/cloudClient.ts (38-39행)
  frontend/src/types/auth.ts
삭제 파일:
  local_server/cloud/auth_client.py
```

**verify**: 로그인 → 토큰 만료 → 자동 갱신 흐름에서 에러 없음

### Step 4: /api/variables 제거 + StrategyBuilder 조건 편집기 정리

**문제**: `rulesApi.variables()`가 호출하는 `/api/variables`가 local_server에 존재하지 않음.
ConditionRow 컴포넌트가 변수 목록에 의존하나, 변수 목록을 공급하는 API가 없음.

**선택지**:
A) local_server에 `/api/variables` 신규 추가 — 과도, 현재 필요 없음
B) 프론트에서 정적 변수 목록 사용 (types/strategy.ts의 AVAILABLE_INDICATORS 활용)
C) variables 관련 코드 제거, DSL 직접 편집으로 전환

**조치**: (B) 프론트 정적 변수 + fallback. rulesApi.variables() 호출 제거, AVAILABLE_INDICATORS를 ConditionRow에 직접 공급. StrategyBuilder의 useQuery(['variables']) 제거.

```
수정 파일:
  frontend/src/services/rules.ts — variables() 제거, Variable/VariablesResponse 유지(타입 호환)
  frontend/src/pages/StrategyBuilder.tsx — 정적 변수 목록 사용
```

**verify**: StrategyBuilder 페이지 렌더 시 404 에러 없음

### Step 5: TrafficLightStatus 상태 매핑 수정

**문제**: `localRes?.data?.broker_connected` 참조하나, 실제 응답은 `broker.connected` (중첩 객체).

```
수정 파일:
  frontend/src/components/TrafficLightStatus.tsx (53, 56행)
```

변경 내용:
- `localRes?.data?.broker_connected` → `localRes?.data?.broker?.connected`
- engine 상태 표시: ui.ts의 ServerStatus에 engine 필드 추가는 미래 작업으로 보류 (현재 3등 신호등만 유지)

**verify**: TrafficLightStatus가 서버 응답 shape(`broker.connected`)를 올바르게 참조. 현재 `broker.connected`는 하드코딩 `false`이므로 신호등은 red로 표시되는 것이 정상 — 실제 연결 상태 반영은 Unit 1 연동 후 별도 작업.

### Step 6: 레거시 서비스 파일 정리

**문제**: api.ts, onboarding.ts, templates.ts, portfolio.ts가 localhost:8000에 의존.
cloud/local에 대응 API가 없는 기능들.

**조치**: 각 서비스 파일을 stub으로 교체. 실제 API 없이 빈 데이터/에러 메시지를 반환하는 TODO 래퍼.
이렇게 하면 import하는 페이지들이 빌드 에러 없이 동작하면서, localhost:8000 의존이 제거됨.

```
수정 파일:
  frontend/src/services/api.ts — stockApi·aiAnalysisApi·tradingApi·healthApi를 TODO stub으로 교체
  frontend/src/services/onboarding.ts — TODO stub
  frontend/src/services/templates.ts — TODO stub
  frontend/src/services/portfolio.ts — TODO stub
```

각 stub 함수는:
- `console.warn('[TODO] 이 API는 아직 Phase 3에서 구현되지 않았습니다')`
- 빈 배열/빈 객체/null 반환 (기존 타입 호환)
- localhost:8000 참조 완전 제거

페이지 컴포넌트(StockDetail, Trading, Portfolio, Templates, Onboarding)는 import 구조를 유지하되,
stub 서비스를 통해 "미구현" 상태로 안전하게 렌더링.

**트레이드오프**: 이것은 "기능 이전 완료"가 아니라 "의존 제거 + 임시 안전화"다. 해당 페이지들은 빈 데이터로 렌더되며, 실제 기능 복원은 Phase 3 cloud/local API 구현 후 별도 작업이 필요하다.

**verify**: `npm run build` 성공, localhost:8000 참조 0건

### Step 7: 레거시 dashboard 라우터 정리

**문제**: `local_server/routers/health.py`의 `/api/dashboard` 핸들러가 `kiwoom.session` 등 삭제된 모듈 import → 실행 시 ImportError.
`frontend/src/services/dashboard.ts`와 `MarketContext.tsx`가 이 엔드포인트에 의존.

**조치**:
- health.py에서 `/api/dashboard` 핸들러 제거 (레거시, 동작 불가)
- dashboard.ts를 local_server의 현재 `/api/status` 기반으로 교체
- MarketContext.tsx는 cloud_server의 `/api/v1/context` 사용으로 전환

```
수정 파일:
  local_server/routers/health.py — dashboard 핸들러 제거
  frontend/src/services/dashboard.ts — /api/status 기반으로 교체
  frontend/src/components/MarketContext.tsx — cloudContext 사용으로 변경
```

**verify**: MarketContext 컴포넌트가 cloud context API 응답으로 렌더

### Step 8: rules.ts 중복 제거 + 통일

**문제**: 규칙 API 호출이 두 곳에 분산.
- `services/rules.ts` — `rulesApi` (cloudClient + local axios 혼재)
- `services/cloudClient.ts` — `cloudRules` (cloudClient 사용)
- `StrategyBuilder.tsx`는 rulesApi 사용, `StrategyList.tsx`는 cloudRules 사용 → 이중 관리

**조치**: rules.ts의 CRUD를 cloudClient의 cloudRules로 통일. rules.ts는 conditionsToDsl 유틸만 유지.

```
수정 파일:
  frontend/src/services/rules.ts — CRUD 제거, 유틸만 유지
  frontend/src/pages/StrategyBuilder.tsx — cloudRules + localRules 사용
```

**verify**: StrategyBuilder/StrategyList 모두 같은 cloudRules API 사용

---

## 수정 대상 파일 요약

| # | 파일 | Step |
|---|------|------|
| 1 | `frontend/src/components/RuleCard.tsx` | 1 |
| 2 | `frontend/src/services/cloudClient.ts` | 2, 3 |
| 3 | `frontend/src/services/auth.ts` | 3 |
| 4 | `frontend/src/types/auth.ts` | 3 |
| 5 | `local_server/cloud/auth_client.py` (삭제) | 3 |
| 6 | `frontend/src/services/rules.ts` | 4, 8 |
| 7 | `frontend/src/pages/StrategyBuilder.tsx` | 4, 8 |
| 8 | `frontend/src/components/TrafficLightStatus.tsx` | 5 |
| 9 | `frontend/src/services/api.ts` | 6 |
| 10 | `frontend/src/services/onboarding.ts` | 6 |
| 11 | `frontend/src/services/templates.ts` | 6 |
| 12 | `frontend/src/services/portfolio.ts` | 6 |
| 13 | `local_server/routers/health.py` | 7 |
| 14 | `frontend/src/services/dashboard.ts` | 7 |
| 15 | `frontend/src/components/MarketContext.tsx` | 7 |

## 건드리지 않는 파일

- `cloud_server/api/rules.py` — v2+v1 양립 구조 정상
- `cloud_server/api/auth.py` — 응답 shape 올바름
- `cloud_server/models/rule.py` — DB 모델 정상
- `cloud_server/services/rule_service.py` — 서비스 로직 정상
- `local_server/engine/evaluator.py` — v2 DSL + v1 폴백 정상
- `local_server/routers/auth.py` — 토큰 수신 정상
- `local_server/routers/rules.py` — sync 정상
- `local_server/routers/status.py` — 응답 구조 정상
- `frontend/src/context/AuthContext.tsx` — 이미 올바르게 동작
- `frontend/src/services/localClient.ts` — 정상
- `frontend/src/types/strategy.ts` — v2+v1 필드 공존, 정상 (v1 필드는 나중에 제거)
- `frontend/src/types/ui.ts` — 현재 구조 유지
- `frontend/src/components/RuleList.tsx` — v2 기준 이미 정상
- 레거시 페이지(StockDetail, Trading, Portfolio, Templates, Onboarding) — import만 stub으로 연결, 페이지 코드는 유지

## 완료 기준

1. `cd frontend && npm run build` 성공
2. `cd frontend && npx tsc --noEmit` 에러 0건
3. `grep -r "localhost:8000" frontend/src/` 결과 0건
4. RuleCard 런타임 에러 제거 (rule.conditions/operator/side 참조 없음)
5. cloudClient refresh 인터셉터가 `access_token` 키를 올바르게 읽음
6. TrafficLightStatus broker 상태가 서버 응답 shape(`broker.connected`)에 맞게 매핑됨
7. StrategyBuilder에서 404(/api/variables) 에러 없음

## 미래 작업 (이 계획 범위 밖)

- types/strategy.ts에서 v1 필드(buy/sell_conditions, order_type, qty, max_position_count, budget_ratio) 완전 제거 → DB 마이그레이션과 동시 진행 필요
- ServerStatus에 engine 필드 추가 (4등 신호등)
- 레거시 페이지(StockDetail, Trading 등)를 Phase 3 cloud/local API로 완전 재구현
- onboarding 흐름을 Phase 3 아키텍처에 맞게 재설계
- templates 기능을 cloud_server에 신규 구현
