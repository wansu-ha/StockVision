# 계약 정렬 명세서 — Phase 3 프론트/클라우드/로컬

> 작성일: 2026-03-08 | 상태: 초안

## 목적

Phase 3 아키텍처(프론트·클라우드·로컬) 간 API 계약을 정렬하고,
레거시 backend(:8000) 의존을 제거하여 주 경로를 안정화한다.

## 범위

프론트엔드 → cloud_server(:4010) / local_server(:4020) 간 **타입·경로·응답 shape** 정합.
서버 측 비즈니스 로직(DB 모델, 서비스, 엔진)은 변경하지 않는다.
단, **동작 불가능한 레거시 서버 코드 제거**(삭제된 모듈 import 등)는 범위에 포함한다.

## 계약 정의

### C1. 규칙(Rule) 모델 계약

**진실의 원천**: `cloud_server/api/rules.py` + `cloud_server/models/rule.py`

#### C1-1. 규칙 CRUD API

| 메서드 | 경로 | 요청 | 응답 |
|--------|------|------|------|
| GET | `/api/v1/rules` | `?version=N` (선택) | `{ success, data: Rule[], version, count }` |
| POST | `/api/v1/rules` | `RuleCreateBody` | `{ success, data: Rule }` |
| GET | `/api/v1/rules/{id}` | — | `{ success, data: Rule }` |
| PUT | `/api/v1/rules/{id}` | `RuleUpdateBody` | `{ success, data: Rule }` |
| DELETE | `/api/v1/rules/{id}` | — | `{ success }` |

- **PUT** (PATCH 아님). 프론트엔드가 PATCH를 보내면 405.

#### C1-2. Rule 응답 shape

```typescript
interface Rule {
  id: number
  name: string
  symbol: string
  is_active: boolean
  priority: number
  version: number
  created_at: string
  updated_at: string | null
  // v2 DSL (신규 규칙의 주 경로)
  script: string | null
  execution: Execution | null
  trigger_policy: TriggerPolicy | null
  // v1 하위 호환 (마이그레이션 완료 전까지 유지)
  buy_conditions: Record<string, unknown> | null
  sell_conditions: Record<string, unknown> | null
  order_type: string
  qty: number
  max_position_count: number
  budget_ratio: number
}
```

- **v2 주 경로**: script + execution + trigger_policy
- **v1 폴백**: buy/sell_conditions + order_type/qty 등
- `conditions`, `operator`, `side` 필드는 **존재하지 않음**

#### C1-3. 규칙 동기화 (local_server)

| 메서드 | 경로 | 요청 | 응답 |
|--------|------|------|------|
| POST | `/api/rules/sync` | `{ rules: Rule[] \| null }` | `{ success, data: { synced_count }, count }` |
| GET | `/api/rules` | — | `{ success, data: Rule[], count }` |

- 프론트에서 cloud CRUD 후 `localRules.sync(rules)` 호출

#### C1-4. /api/variables 폐기

- local_server에 `/api/variables` 엔드포인트 **없음**
- 프론트에서 호출하면 404
- 조건 편집기는 프론트 정적 변수 목록(`AVAILABLE_INDICATORS`)으로 대체

### C2. 인증 응답 계약

**진실의 원천**: `cloud_server/api/auth.py`

#### C2-1. 로그인/리프레시 응답

```typescript
// POST /api/v1/auth/login
// POST /api/v1/auth/refresh
{
  success: true,
  data: {
    access_token: string,   // JWT (키 이름: access_token, jwt 아님)
    refresh_token: string,
    expires_in: number       // 초 단위 (3600 = 1시간)
  }
}
```

- 프론트 전체에서 `access_token` 키 통일
- `jwt`, `data.jwt`, `data.data?.jwt` 참조 **금지**

#### C2-1a. 인증 API 경로·메서드 정합

| cloudClient.ts 호출 | 서버 실제 | 불일치 |
|---------------------|----------|--------|
| `POST /api/v1/auth/verify-email` | `GET /api/v1/auth/verify-email?token=` | **메서드 불일치** (POST vs GET) |
| `PATCH /api/v1/auth/profile` | 없음 | **엔드포인트 미존재** |

- `verifyEmail`: GET으로 수정하거나, 프론트 호출부가 query param 방식으로 변경
- `updateProfile`: 서버에 없는 엔드포인트 → 호출 제거 또는 TODO stub 처리

#### C2-2. 토큰 저장 위치

| 토큰 | 저장소 | 키 |
|------|--------|---|
| access_token | `sessionStorage` | `sv_jwt` |
| refresh_token | `localStorage` | `sv_rt` |
| email | `localStorage` | `sv_email` |

#### C2-3. 로컬 서버 토큰 전달

| 메서드 | 경로 | 요청 | 응답 |
|--------|------|------|------|
| POST | `/api/auth/token` | `{ access_token, refresh_token }` | `{ success, data: { message } }` |
| POST | `/api/auth/logout` | — | `{ success, data: { message } }` |

### C3. 상태 모델 계약

**진실의 원천**: `local_server/routers/status.py`

#### C3-1. 로컬 서버 상태 API

```typescript
// GET /api/status → 응답
{
  success: true,
  data: {
    server: "running",
    broker: {
      connected: boolean,
      has_credentials: boolean
    },
    strategy_engine: {
      running: boolean
    }
  }
}
```

#### C3-2. TrafficLightStatus 매핑

| 신호등 | 판정 기준 |
|--------|----------|
| cloud | `cloudHealth.check()` 성공 여부 |
| local | `localStatus.get()` 응답 존재 여부 |
| broker | `localRes.data.broker.connected` |

- `broker_connected` (플랫) 아닌 `broker.connected` (중첩)
- engine 상태는 현재 신호등에 미표시 (3등 유지)

#### C3-3. 헬스 체크

| 서버 | 경로 | 응답 |
|------|------|------|
| cloud | `/health` | `{ status, version? }` |
| local | `/health` | `{ status, version }` |

### C4. 레거시 의존 제거

#### C4-1. 제거 대상

| 서비스 파일 | 의존 | 대체 |
|------------|------|------|
| `services/api.ts` | localhost:8000 | TODO stub (빈 데이터 반환) |
| `services/onboarding.ts` | localhost:8000 | TODO stub |
| `services/templates.ts` | localhost:8000 | TODO stub |
| `services/portfolio.ts` | localhost:8000 | TODO stub |

- stub = 기존 타입 호환, `console.warn` + 빈 반환값
- localhost:8000 참조 0건 달성

#### C4-2. 레거시 dashboard 핸들러

- `local_server/routers/health.py`의 `/api/dashboard` — 삭제된 모듈 import, 실행 불가 → 제거
- `dashboard.ts` → `/api/status` 기반으로 교체
- `MarketContext.tsx` → `cloudContext` 사용으로 전환

#### C4-3. auth_client.py 레거시

- `local_server/cloud/auth_client.py` — token.dat 기반, 어디서도 미사용 → 삭제

#### C4-4. 규칙 서비스 통일

- `services/rules.ts` CRUD → `cloudClient.ts`의 `cloudRules`로 통일
- `rules.ts`는 `conditionsToDsl` 유틸만 유지
- StrategyBuilder/StrategyList 모두 `cloudRules` 단일 진입점

## 수용 기준

- [ ] C1-1: cloudRules가 PUT 사용 (PATCH 아님)
- [ ] C1-2: RuleCard가 Rule 타입의 실제 필드만 참조 (conditions/operator/side 없음)
- [ ] C1-3: 규칙 CRUD 후 localRules.sync 호출
- [ ] C1-4: /api/variables 호출 0건
- [ ] C2-1: 인증 응답에서 access_token 키만 사용 (jwt 키 참조 0건)
- [ ] C2-1a: cloudAuth.verifyEmail이 서버 GET 메서드에 맞게 호출
- [ ] C2-1b: cloudAuth.updateProfile 미존재 엔드포인트 호출 제거 또는 TODO 처리
- [ ] C2-2: cloudClient refresh 인터셉터가 access_token 키 사용
- [ ] C2-3: 로컬 서버 토큰 전달이 access_token/refresh_token 필드 사용
- [ ] C3-1: TrafficLightStatus가 broker.connected (중첩) 참조 — 응답 shape 정렬 (broker.connected는 현재 하드코딩 false이므로, 실제 연결 상태 반영은 Unit 1 연동 후 별도 작업)
- [ ] C3-2: 3등 신호등(cloud/local/broker)이 서버 응답 shape에 맞게 매핑됨
- [ ] C4-1: frontend에서 localhost:8000 참조 0건
- [ ] C4-2: 레거시 서비스가 TODO stub으로 대체, 빌드 에러 없음
- [ ] C4-3: auth_client.py 삭제
- [ ] C4-4: rules.ts CRUD 제거, cloudRules 단일 진입점
- [ ] 빌드: `npm run build` 성공
- [ ] 타입: `tsc --noEmit` 에러 0건
