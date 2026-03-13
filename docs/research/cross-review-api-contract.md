# API 계약 교차 정합성 리뷰

> 작성일: 2026-03-05 | 검토 범위: Unit 2 (로컬 서버) × Unit 4 (클라우드 서버) × Unit 6 (프론트엔드 기대)

---

## 1. 로컬 서버 엔드포인트 대조표 (Plan vs 구현)

### 1.1 spec/local-server-core/plan.md 기준 엔드포인트

| 엔드포인트 (Plan) | 구현 여부 | 구현 경로 | 비고 |
|------------------|----------|----------|------|
| POST /api/auth/token | **불일치** | POST /api/auth/token | 요청/응답 시그니처 다름 (아래 상세) |
| GET /api/config | 구현됨 | GET /api/config | 정상 |
| PATCH /api/config | 구현됨 | PATCH /api/config | 정상 |
| POST /api/config/kiwoom | **누락** | — | 구현 없음 |
| GET /api/status | 구현됨 | GET /api/status | 응답 구조 다름 (아래 상세) |
| POST /api/strategy/start | 구현됨 | POST /api/strategy/start | 정상 |
| POST /api/strategy/stop | 구현됨 | POST /api/strategy/stop | 정상 |
| POST /api/strategy/kill | **누락** | — | 구현 없음 |
| POST /api/strategy/unlock | **누락** | — | 구현 없음 |
| POST /api/rules/sync | 구현됨 | POST /api/rules/sync | 요청 형식 확장됨 (호환) |
| GET /api/logs | 구현됨 | GET /api/logs | 응답 구조 다름 (아래 상세) |
| WS /ws | 구현됨 | WS /ws | 메시지 타입명 다름 (아래 상세) |

### 1.2 구현에서 추가된 엔드포인트 (Plan에 없음)

| 엔드포인트 | 라우터 파일 | 설명 |
|-----------|-----------|------|
| POST /api/auth/logout | auth.py | 자격증명 삭제 |
| GET /api/auth/status | auth.py | 인증 상태 확인 |
| GET /api/rules | rules.py | 캐시된 규칙 목록 조회 |
| POST /api/trading/order | trading.py | 수동 주문 발행 |
| GET /health | main.py | 헬스체크 |

---

## 2. 클라우드 서버 엔드포인트 대조표 (Plan vs 구현)

### 2.1 spec/cloud-server/plan.md 기준 엔드포인트

| 엔드포인트 (Plan) | 구현 여부 | 구현 경로 | 비고 |
|------------------|----------|----------|------|
| POST /api/v1/auth/register | 구현됨 | cloud_server/api/auth.py | 정상 |
| GET /api/v1/auth/verify-email | 구현됨 | cloud_server/api/auth.py | 정상 |
| POST /api/v1/auth/login | 구현됨 | cloud_server/api/auth.py | 정상 |
| POST /api/v1/auth/refresh | 구현됨 | cloud_server/api/auth.py | 정상 |
| POST /api/v1/auth/logout | 구현됨 | cloud_server/api/auth.py | 정상 |
| POST /api/v1/auth/forgot-password | 구현됨 | cloud_server/api/auth.py | 정상 |
| POST /api/v1/auth/reset-password | 구현됨 | cloud_server/api/auth.py | 정상 |
| GET /api/v1/rules | 구현됨 | cloud_server/api/rules.py | 정상 |
| POST /api/v1/rules | 구현됨 | cloud_server/api/rules.py | 정상 |
| GET /api/v1/rules/:id | 구현됨 | cloud_server/api/rules.py | 정상 |
| PUT /api/v1/rules/:id | 구현됨 | cloud_server/api/rules.py | 정상 |
| DELETE /api/v1/rules/:id | 구현됨 | cloud_server/api/rules.py | 정상 |
| POST /api/v1/heartbeat | 구현됨 | cloud_server/api/heartbeat.py | 정상 |
| GET /api/v1/version | 구현됨 | cloud_server/api/version.py | 정상 |
| GET /api/v1/admin/users | 구현됨 | cloud_server/api/admin.py | 정상 |
| PATCH /api/v1/admin/users/:id | 구현됨 | cloud_server/api/admin.py | 정상 |
| GET /api/v1/admin/stats | 구현됨 | cloud_server/api/admin.py | 정상 |
| GET /api/v1/admin/service-keys | 구현됨 | cloud_server/api/admin.py | 정상 |
| POST /api/v1/admin/service-keys | 구현됨 | cloud_server/api/admin.py | 정상 |
| DELETE /api/v1/admin/service-keys/:id | 구현됨 | cloud_server/api/admin.py | 정상 |
| GET /api/v1/admin/templates | 구현됨 | cloud_server/api/admin.py | 정상 |
| POST /api/v1/admin/templates | 구현됨 | cloud_server/api/admin.py | 정상 |
| PUT /api/v1/admin/templates/:id | 구현됨 | cloud_server/api/admin.py | 정상 |
| DELETE /api/v1/admin/templates/:id | 구현됨 | cloud_server/api/admin.py | 정상 |
| GET /api/v1/admin/collector-status | 구현됨 | cloud_server/api/admin.py | 정상 |
| GET /api/v1/context | 구현됨 | cloud_server/api/context.py | 정상 |
| GET /api/v1/context/variables | **추가됨** | cloud_server/api/context.py | Plan에 없으나 구현 (spec §9에 언급) |

### 2.2 구현에서 추가된 엔드포인트 (Plan에 없음)

| 엔드포인트 | 라우터 파일 | 설명 |
|-----------|-----------|------|
| GET /api/v1/templates | sync.py | 공개 템플릿 목록 (로컬 서버 fetch용) |
| GET /api/v1/admin/quotes/:symbol/daily | admin.py | 일봉 데이터 (어드민 전용) |
| GET /api/v1/admin/quotes/:symbol/latest | admin.py | 최신 시세 (어드민 전용) |
| GET /health | main.py | 헬스체크 |
| GET / | main.py | 루트 엔드포인트 |

---

## 3. 응답 형식 통일성 검토 (`{ success, data, count }`)

### 3.1 로컬 서버 응답 형식

| 엔드포인트 | success | data | count | 비고 |
|-----------|---------|------|-------|------|
| POST /api/auth/token | O | O | O (=1) | 규격 준수 |
| POST /api/auth/logout | O | O | O (=0) | 규격 준수 |
| GET /api/auth/status | O | O | O (=1) | 규격 준수 |
| GET /api/config | O | O | O (=1) | 규격 준수 |
| PATCH /api/config | O | O | O (=1) | 규격 준수 |
| GET /api/status | O | O | O (=1) | 규격 준수 |
| POST /api/strategy/start | O | O | O (=1) | 규격 준수 |
| POST /api/strategy/stop | O | O | O (=1) | 규격 준수 |
| POST /api/trading/order | O | O | O (=1) | 규격 준수 |
| POST /api/rules/sync | O | O | O (=len) | 규격 준수 |
| GET /api/rules | O | O | O (=len) | 규격 준수 |
| GET /api/logs | O | O (중첩) | O (=len) | **data 구조 불일치** (아래 상세) |
| WS /ws | — | — | — | WS, 해당 없음 |
| GET /health | **없음** | **없음** | **없음** | `{"status": "ok"}` — 규격 미준수 |

**로컬 서버 불일치 항목:**
- `GET /health`: `{"status": "ok"}` 형식 — `{ success, data, count }` 미준수
- `GET /api/logs`: 응답 data가 `{"items": [...], "total": ..., "limit": ..., "offset": ...}` 중첩 구조 — plan은 `data: [...]` 플랫 배열 기대

### 3.2 클라우드 서버 응답 형식

| 엔드포인트 | success | data | count | 비고 |
|-----------|---------|------|-------|------|
| POST /api/v1/auth/register | O | **없음** | **없음** | `{"success": True, "message": "..."}` — data/count 누락 |
| GET /api/v1/auth/verify-email | O | **없음** | **없음** | `{"success": True, "message": "..."}` — data/count 누락 |
| POST /api/v1/auth/login | O | O | **없음** | count 누락 |
| POST /api/v1/auth/refresh | O | O | **없음** | count 누락 |
| POST /api/v1/auth/logout | O | **없음** | **없음** | `{"success": True}` — data/count 누락 |
| POST /api/v1/auth/forgot-password | O | **없음** | **없음** | `{"success": True, "message": "..."}` — data/count 누락 |
| POST /api/v1/auth/reset-password | O | **없음** | **없음** | `{"success": True, "message": "..."}` — data/count 누락 |
| GET /api/v1/rules | O | O | O | 정상 |
| POST /api/v1/rules | O | O | **없음** | count 누락 |
| GET /api/v1/rules/:id | O | O | **없음** | count 누락 |
| PUT /api/v1/rules/:id | O | O | **없음** | count 누락 |
| DELETE /api/v1/rules/:id | O | **없음** | **없음** | `{"success": True}` — data/count 누락 |
| POST /api/v1/heartbeat | O | O | **없음** | count 누락 |
| GET /api/v1/version | O | O | **없음** | count 누락 |
| GET /api/v1/admin/users | O | **spread** | **없음** | `{"success": True, **data}` — data 키 없음 |
| PATCH /api/v1/admin/users/:id | O | **없음** | **없음** | `{"success": True}` |
| GET /api/v1/admin/stats | O | O | **없음** | count 누락 |
| GET /api/v1/admin/service-keys | O | O | O | 정상 |
| POST /api/v1/admin/service-keys | O | O | **없음** | count 누락 |
| DELETE /api/v1/admin/service-keys/:id | O | **없음** | **없음** | `{"success": True}` |
| GET /api/v1/admin/templates | O | O | O | 정상 |
| POST /api/v1/admin/templates | O | O | **없음** | count 누락 |
| PUT /api/v1/admin/templates/:id | O | O | **없음** | count 누락 |
| DELETE /api/v1/admin/templates/:id | O | **없음** | **없음** | `{"success": True}` |
| GET /api/v1/admin/collector-status | O | O | **없음** | count 누락 |
| GET /api/v1/context | O | O | **없음** | count 누락 |
| GET /api/v1/context/variables | O | O | O | 정상 |
| GET /api/v1/templates | O | O | O | 정상 |
| GET /api/v1/admin/quotes/:symbol/daily | O | O | O | 정상 |
| GET /api/v1/admin/quotes/:symbol/latest | O | O | **없음** | count 누락 |
| GET /health | O | **없음** | **없음** | 규격 밖 (헬스체크 용도상 허용 가능) |

---

## 4. 프론트엔드 기대 vs 실제 구현 불일치

frontend/plan.md §3에서 로컬 서버(Unit 2)와 클라우드 서버(Unit 4)에 기대하는 엔드포인트와 실제 구현 비교.

### 4.1 로컬 서버 (localClient 기대)

| 프론트엔드 기대 API | 실제 구현 | 불일치 |
|--------------------|----------|--------|
| POST /api/auth/token (JWT + Refresh Token 전달) | 구현됨 — 단, **요청 형식 불일치** | plan: `{access_token, refresh_token}` / 구현: `{app_key, app_secret}` — 목적 자체가 다름 |
| POST /api/config/kiwoom (API Key 등록) | **누락** | 구현 없음 |
| GET /api/config | 구현됨 | 정상 |
| PATCH /api/config (모드 전환) | 구현됨 | 정상 |
| POST /api/rules/sync | 구현됨 | 정상 |
| GET /api/status | 구현됨 | 응답 구조 다름 (아래 상세) |
| GET /api/logs | 구현됨 | 응답 구조 다름 (아래 상세) |
| POST /api/strategy/start | 구현됨 | 정상 |
| POST /api/strategy/stop | 구현됨 | 정상 |
| WS /ws | 구현됨 | 메시지 타입명 다름 (아래 상세) |

### 4.2 클라우드 서버 (cloudClient 기대)

| 프론트엔드 기대 API | 실제 구현 | 불일치 |
|--------------------|----------|--------|
| POST /api/v1/auth/register | 구현됨 | 정상 |
| POST /api/v1/auth/login | 구현됨 | **응답 필드명 다름**: plan은 `access_token` 반환, 구현은 `jwt` 반환 |
| POST /api/v1/auth/refresh | 구현됨 | **응답 필드명 다름**: plan은 `access_token` 반환, 구현은 `jwt` 반환 |
| GET /api/v1/rules | 구현됨 | 정상 |
| POST /api/v1/rules | 구현됨 | 정상 |
| PUT /api/v1/rules/:id | 구현됨 | 정상 |
| DELETE /api/v1/rules/:id | 구현됨 | 정상 |
| GET /api/v1/context | 구현됨 | 정상 |
| GET /api/v1/admin/* | 구현됨 | 정상 |
| GET /health | 구현됨 | 정상 |

---

## 5. 세부 불일치 항목

### 5.1 [Critical] POST /api/auth/token — 로컬 서버 목적 불일치

**Plan (local-server-core/plan.md Step 3):**
```json
// 요청 — 프론트엔드가 클라우드 로그인 후 JWT를 로컬 서버로 전달
{ "access_token": "...", "refresh_token": "..." }
// 응답
{ "success": true, "data": {"message": "Token stored"} }
// 동작: Refresh Token → Credential Manager, access_token → 메모리
```

**실제 구현 (auth.py):**
```json
// 요청 — 키움 API Key를 로컬 서버로 전달 (전혀 다른 목적)
{ "app_key": "...", "app_secret": "..." }
// 응답
{ "success": true, "data": {"token": "stub_token", "note": "..."} }
// 동작: API Key → keyring, 더미 토큰 발급
```

**영향**: 프론트엔드 `localClient.setAuthToken(jwt, refreshToken)`이 이 엔드포인트를 호출 → **완전 실패**. 프론트엔드가 기대하는 JWT 전달 로직이 구현되지 않음.

**해결책**: Plan에서 의도한 JWT 전달 기능이 `POST /api/config/kiwoom`(API Key)과 `POST /api/auth/token`(JWT)으로 분리되어 있음. 구현은 두 목적을 혼합했음. `POST /api/auth/token`이 JWT 수신용으로 재구현되어야 하고, API Key 등록은 별도 엔드포인트로 분리 필요.

---

### 5.2 [Critical] POST /api/config/kiwoom — 누락

**Plan (local-server-core/plan.md Step 3):**
```
POST /api/config/kiwoom
  요청: { "app_key": "...", "app_secret": "..." }
  응답: { "success": true }
  동작: CredentialStore에 저장
```

**실제 구현**: 해당 엔드포인트 없음. API Key 저장 기능이 `POST /api/auth/token`으로 이전됨.

**영향**: 프론트엔드 `localClient.setKiwoomKeys(appKey, appSecret)`의 호출 대상 없음.

---

### 5.3 [High] GET /api/status — 응답 구조 불일치

**Plan (local-server-core/plan.md Step 3):**
```json
{
  "success": true,
  "data": {
    "server": "running",
    "uptime_sec": 3600,
    "kiwoom": "connected",
    "engine": "idle",
    "cloud_server": "ok",
    "last_heartbeat": "2026-03-05T10:00:00Z"
  }
}
```

**실제 구현 (status.py):**
```json
{
  "success": true,
  "data": {
    "server": "running",
    "broker": {
      "connected": false,
      "has_credentials": false
    },
    "strategy_engine": {
      "running": false
    }
  },
  "count": 1
}
```

**불일치 목록**:
- `uptime_sec` 누락
- `kiwoom` (문자열) → `broker.connected` (객체 내 bool)로 구조 변경
- `engine` (문자열) → `strategy_engine.running` (객체 내 bool)로 구조 변경
- `cloud_server` 필드 누락
- `last_heartbeat` 필드 누락

**영향**: 프론트엔드 TrafficLightStatus 컴포넌트가 `data.kiwoom`, `data.engine` 필드를 기대할 경우 undefined 반환.

---

### 5.4 [High] GET /api/logs — 응답 data 구조 불일치

**Plan (local-server-core/plan.md Step 3):**
```json
{
  "success": true,
  "data": [ { "id": 1, "timestamp": "...", "type": "execution", ... } ],
  "count": 100
}
```

**실제 구현 (logs.py):**
```json
{
  "success": true,
  "data": {
    "items": [ { ... } ],
    "total": 100,
    "limit": 100,
    "offset": 0
  },
  "count": 10
}
```

**불일치**: `data`가 배열이 아니라 페이지네이션 메타데이터를 포함한 객체. Plan의 프론트엔드 코드가 `response.data`를 배열로 가정할 경우 타입 오류.

**영향**: 프론트엔드 `localClient.getLogs(filters)`의 반환값 처리 로직이 이 구조와 맞지 않을 수 있음.

---

### 5.5 [High] POST /api/v1/auth/login — 응답 토큰 필드명 불일치

**Plan (cloud-server/plan.md Step 2) / 프론트엔드 기대:**
```json
{
  "success": true,
  "data": {
    "access_token": "...",
    "refresh_token": "...",
    "expires_in": 3600
  }
}
```

**실제 구현 (auth.py):**
```json
{
  "success": true,
  "data": {
    "jwt": "...",
    "refresh_token": "...",
    "expires_in": 3600
  }
}
```

**불일치**: 토큰 필드명이 `access_token` → `jwt`로 변경됨.

**영향**: 프론트엔드 `cloudClient.login()` 이후 `response.data.access_token`으로 접근하는 코드가 `undefined`를 반환. `POST /api/v1/auth/refresh`도 동일 문제.

---

### 5.6 [Medium] WS /ws — 메시지 타입명 불일치

**Plan (local-server-core/plan.md Step 4):**
```json
{ "type": "quote", "symbol": "...", "price": ..., "volume": ..., "timestamp": "..." }
{ "type": "fill", "rule_id": ..., "symbol": "...", "side": "BUY", ... }
{ "type": "status", "kiwoom": "connected", "engine": "running" }
```

**프론트엔드 기대 (frontend/plan.md Step 5):**
```json
{ "type": "price_update", "symbol": "...", "price": ..., "changePercent": ..., "volume": ... }
{ "type": "execution", "timestamp": "...", "symbol": "...", "side": "buy", ... }
{ "type": "status_change", "server": "running", "kiwoom_connected": true }
```

**실제 구현 (ws.py):**
```json
{ "type": "system", "data": {"message": "...", "connections": ...} }
{ "type": "pong", "data": {} }
{ "type": "ping", "data": {} }
```

**불일치**:
1. Plan의 `type: "quote"` vs 프론트엔드 기대 `type: "price_update"` — 불일치
2. Plan의 `type: "fill"` vs 프론트엔드 기대 `type: "execution"` — 불일치
3. Plan의 `side: "BUY"` vs 프론트엔드 기대 `side: "buy"` (대소문자) — 불일치
4. 현재 구현은 `system`, `pong`, `ping`만 구현 — 시세/체결 브로드캐스트 미구현 (stub)

---

### 5.7 [Medium] POST /api/strategy/kill, /api/strategy/unlock — 누락

**Plan:**
```
POST /api/strategy/kill    → 신규 주문 차단 + TradingEnabled=OFF
POST /api/strategy/unlock  → 손실 락 해제 (수동만 허용)
```

**실제 구현**: 해당 엔드포인트 없음.

**영향**: 긴급 정지(kill switch) 기능 프론트엔드에서 호출 불가.

---

### 5.8 [Low] GET /api/v1/admin/users — 응답 형식 불일치

**실제 구현 (admin.py):**
```python
return {"success": True, **data}
# data = {"items": [...], "total": ..., "page": ...}
# 결과: {"success": True, "items": [...], "total": ..., "page": ...}
```

**기대 형식:**
```json
{"success": true, "data": {"items": [...], "total": ..., "page": ...}}
```

`data` 키 없이 spread됨 — `{ success, data, count }` 규격 미준수.

---

## 6. 누락된 엔드포인트 요약

### 6.1 로컬 서버 누락

| 엔드포인트 | 우선순위 | 설명 |
|-----------|---------|------|
| POST /api/config/kiwoom | Critical | API Key 등록 (프론트 Settings 페이지 핵심) |
| POST /api/strategy/kill | High | 긴급 정지 기능 |
| POST /api/strategy/unlock | High | 손실 락 해제 |

### 6.2 클라우드 서버 누락

없음 — Plan에 명시된 모든 엔드포인트 구현됨.

---

## 7. 수정 필요 사항 우선순위

### Critical (즉시 수정)

1. **로컬 서버 POST /api/auth/token 재설계**
   - 현재: API Key 저장 용도 (`{app_key, app_secret}` 수신)
   - Plan/프론트엔드 기대: JWT 전달 용도 (`{access_token, refresh_token}` 수신)
   - 해결: `POST /api/auth/token`을 JWT 수신 전용으로 재구현, API Key는 `POST /api/config/kiwoom`으로 이전

2. **로컬 서버 POST /api/config/kiwoom 추가**
   - 프론트엔드 Settings 페이지의 API Key 등록 기능 동작 불가
   - `local_server/routers/config.py`에 `/kiwoom` POST 엔드포인트 추가

3. **클라우드 서버 로그인/갱신 응답 필드명 수정**
   - `data.jwt` → `data.access_token` 변경
   - `cloud_server/api/auth.py` login, refresh 핸들러 응답 수정

### High (다음 이터레이션)

4. **로컬 서버 GET /api/status 응답 구조 정렬**
   - 프론트엔드가 기대하는 `kiwoom`, `engine` 플랫 필드 추가 또는 문서화로 프론트엔드 수정
   - 선택: 구현 측 응답 구조 변경 or 프론트엔드가 새 구조에 맞게 수정

5. **로컬 서버 GET /api/logs 응답 구조 정렬**
   - `data`가 중첩 객체 → 프론트엔드가 `data.items`로 접근하도록 문서화 or 구현 측 `data`를 배열로 변경 후 페이지네이션은 별도 필드로

6. **로컬 서버 POST /api/strategy/kill 추가**
   - 긴급 정지 기능

7. **로컬 서버 POST /api/strategy/unlock 추가**
   - 손실 락 해제

### Medium (정합성 유지)

8. **WS 메시지 타입명 통일**
   - 로컬 서버 plan: `quote`, `fill`, `status`
   - 프론트엔드 기대: `price_update`, `execution`, `status_change`
   - 어느 쪽이 정본인지 결정 후 통일 필요
   - side 값 대소문자 통일: `BUY`/`SELL` vs `buy`/`sell`

### Low (규격 준수)

9. **클라우드 서버 응답 형식 통일**
   - 인증 엔드포인트 (register, logout 등) `data`, `count` 필드 추가
   - GET /api/v1/admin/users `**data` spread 제거 → `data` 키로 감싸기

10. **로컬 서버 GET /health 응답 형식**
    - `{"status": "ok"}` → `{"success": true, "data": {"status": "ok"}}` (선택적)

---

## 8. 로컬 서버 cloud_client 기대 엔드포인트 vs 클라우드 서버 구현

로컬 서버 내부 `cloud/client.py`가 클라우드 서버에 호출하는 엔드포인트 검증.

| 로컬 cloud_client 호출 (plan.md Step 6) | 클라우드 서버 구현 | 상태 |
|----------------------------------------|-----------------|------|
| POST /api/v1/auth/refresh | 구현됨 | 정상 |
| GET /api/v1/rules | 구현됨 | 정상 |
| POST /api/v1/heartbeat | 구현됨 | 정상 |
| GET /api/v1/context | 구현됨 | 정상 |
| PUT /api/v1/rules/:id (로컬 sync_local) | 구현됨 | 정상 |

모든 로컬 서버가 클라우드에 호출하는 엔드포인트는 클라우드에 구현되어 있음. 단, `POST /api/v1/auth/refresh` 응답의 `data.access_token` 필드명이 `data.jwt`로 되어 있어 로컬 cloud_client의 파싱 로직이 실패할 수 있음 (5.5 참조).

---

## 9. 결론

| 구분 | 총 엔드포인트 | 정상 구현 | 누락 | 불일치 |
|------|------------|---------|------|--------|
| 로컬 서버 (Plan 기준) | 11개 | 7개 | 3개 | 1개 |
| 클라우드 서버 (Plan 기준) | 27개 | 27개 | 0개 | 0개 |
| 응답 형식 (로컬) | 12개 | 11개 | — | 1개 (logs) |
| 응답 형식 (클라우드) | 27개 | 4개 | — | 23개 (count 누락 등) |
| 프론트엔드 기대 vs 구현 | 20개 | 16개 | 1개 | 3개 |

**가장 긴급한 수정**: 로컬 서버 `POST /api/auth/token`의 목적 재설계 + `POST /api/config/kiwoom` 추가 + 클라우드 서버 JWT 응답 필드명 `jwt` → `access_token` 변경.
