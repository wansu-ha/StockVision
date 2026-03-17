# StockVision v3 보안 리뷰 보고서

> 점검일: 2026-03-17 | 점검 대상: development-plan-v3, relay-infra, remote-ops, production-hardening, auth-extension, security-audit-report
> 점검자: Security Engineer (Opus)

---

## 1. 인증/인가 (JWT WS 인증, 디바이스 인증, OAuth2)

### 판정: ⚠️ 주의

**잘 설계된 부분:**
- WS 인증에서 JWT를 query string이 아닌 첫 메시지로 전송하여 서버 로그 노출 방지 (relay-infra §5.1)
- JWT 만료 시 WS 내 재인증 요구 + 60초 유예 후 세션 종료 (합리적)
- OAuth2 흐름에서 authorization code 방식 채택 (implicit 대비 안전)
- 디바이스별 세션 강제 종료 지원

**발견된 문제:**

| # | 문제 | 심각도 | 근거 |
|---|------|--------|------|
| A1 | **OAuth2 state 파라미터 미언급** | 🔴 High | auth-extension §5.1 OAuth2 흐름에서 CSRF 방지용 `state` 파라미터가 설계에 포함되지 않음. 공격자가 자신의 authorization code를 피해자에게 주입하여 계정 연결 탈취 가능 (OAuth2 Login CSRF). |
| A2 | **OAuth2 callback이 POST인데 PKCE 미언급** | 🟡 Medium | SPA(React) 환경에서 authorization code 가로채기 방지를 위해 PKCE(Proof Key for Code Exchange)가 필요. 서버 사이드 렌더링이면 불필요하나, 프론트가 React SPA이므로 PKCE 적용 권장. |
| A3 | **OAuth2 계정 자동 연동 시 이메일 검증 부재** | 🟡 Medium | "같은 이메일이면 같은 계정" 정책에서, OAuth 제공자가 미인증 이메일을 반환할 수 있음 (예: Kakao는 이메일 비필수). 제공자별 `email_verified` 클레임을 반드시 검증해야 함. 미검증 이메일로 기존 계정 탈취 가능. |
| A4 | **WS 재인증 시 RT 사용 여부 미명시** | 🟡 Medium | JWT 만료 후 `auth_required` 메시지를 보내는데, 클라이언트가 refresh token으로 새 JWT를 얻는 흐름이 WS 컨텍스트에서 어떻게 동작하는지 명시되지 않음. RT가 WS로 전송되면 안 됨 (별도 HTTPS 채널 사용 필요). |
| A5 | **로컬 서버 WS `/ws/relay` 인증 후 사용자 격리 미명시** | 🟢 Low | 연결 레지스트리가 `user_id → WebSocket` 매핑이지만, 다른 사용자의 메시지를 수신하지 않는다는 격리 보장이 설계에 명시되어 있지 않음. 단일 사용자 시스템이라면 무관하나, 멀티테넌트 확장 시 위험. |

**권고:**
1. OAuth2 흐름에 `state` 파라미터 + PKCE 반드시 추가
2. OAuth2 자동 연동 시 제공자의 `email_verified` 클레임 검증 필수
3. WS 재인증은 별도 HTTP `/auth/refresh` 호출 후 새 JWT를 WS `auth` 메시지로 재전송하는 흐름 명시

---

## 2. E2E 암호화 (AES-256-GCM)

### 판정: ✅ 통과 (경미한 주의 1건)

**잘 설계된 부분:**
- AES-256-GCM 선택 적절 (인증 + 암호화 동시, NIST 표준)
- 매 메시지마다 랜덤 12바이트 IV 생성 → IV 재사용 방지
- 디바이스별 별도 키 → 키 분실 시 영향 범위 제한
- 클라우드가 키를 저장하지 않는 진정한 E2E
- 프론트엔드 구현에서 Web Crypto API 사용 (순수 JS 구현 대비 안전)
- ciphertext + auth tag 분리 전송 후 복호화 시 결합 → 올바른 GCM 처리
- 암호화 범위가 명확 (금융 데이터만, 시스템 상태는 평문)

**발견된 문제:**

| # | 문제 | 심각도 | 근거 |
|---|------|--------|------|
| E1 | **키 생성 엔트로피 소스 미명시** | 🟢 Low | auth-extension §5.5에서 "AES-256 키 생성 (32바이트)"만 언급. Python 측에서 `os.urandom(32)` 또는 `secrets.token_bytes(32)` 사용을 명시해야 함. `random.randbytes()` 사용 시 예측 가능. |
| E2 | **QR 페어링 시 키 전송 채널 보안** | 🟢 Low | QR코드로 32바이트 키를 표시하는 것은 같은 물리 공간에서만 안전. "복사 가능한 문자열"을 클립보드에 넣는 경우, 클립보드 모니터링 멀웨어에 노출 가능. 초기 방법 1(로컬 PC)만 지원하므로 위험도는 낮음. |

**판단 근거:**
- IV: 12바이트 랜덤, 매 메시지 새로 생성 → IV 재사용 확률 극히 낮음 (2^96 공간)
- 인증 태그: tag를 별도 필드로 전송하고 복호화 시 ciphertext에 append → Web Crypto API가 자동 검증
- 키 관리: 클라우드 미저장, IndexedDB 저장 (origin-scoped), 디바이스 해제 시 폐기
- 등록 디바이스 5대 제한 → 성능/보안 균형 적절

---

## 3. SSRF/Injection (Config PATCH allowlist)

### 판정: ⚠️ 주의

**현재 상태 분석:**
- `local_server/routers/config.py`의 `patch_configuration()`이 `body.updates`를 `update_config()`에 그대로 전달
- `require_local_secret` Depends가 이미 적용됨 (C1 수정 완료)
- **그러나 allowlist가 아직 구현되지 않음** — production-hardening M1에서 계획만 존재

**발견된 문제:**

| # | 문제 | 심각도 | 근거 |
|---|------|--------|------|
| S1 | **Config PATCH allowlist 미구현** | 🔴 High | `MUTABLE_CONFIG_KEYS` allowlist가 spec에만 있고 코드에 없음. `require_local_secret`이 있어 외부 공격은 차단되나, XSS/악성 확장 프로그램이 local_secret을 탈취하면 `cloud.url` 변경 → SSRF 체인 가능. |
| S2 | **`_detect_mock_kiwoom` SSRF 잠재** | 🟡 Medium | `register_broker_keys`에서 외부 API(`mockapi.kiwoom.com`, `api.kiwoom.com`)에 사용자 제공 credentials로 요청. URL은 하드코딩이라 SSRF는 아니지만, 사용자가 입력한 `app_key`/`app_secret`이 외부로 전송됨. 올바른 동작이나, 실패 시 상세 에러 메시지에 내부 정보 노출 가능. |
| S3 | **rules injection (H2) 미해결** | 🟡 Medium | `/api/rules/sync`가 `list[dict[str, Any]]` 수용. `require_local_secret`으로 완화되었으나, 서명 검증 없이 임의 규칙 주입 가능. spec에 언급되어 있으나 구현 계획이 T2 이후. |

**권고:**
1. M1 allowlist를 T1 이전으로 당겨서 구현 — `local_secret` 탈취 시나리오 대비
2. `update_config()`에서 nested key validation 추가 (예: `cloud.*` 블록 전체 거부)

---

## 4. Rate Limiting (WS + HTTP)

### 판정: ⚠️ 주의

**잘 설계된 부분:**
- Redis ZSET 슬라이딩 윈도우 구현 완료 (`rate_limit.py`)
- Redis 불가 시 인메모리 폴백 존재
- X-Forwarded-For rightmost-N 방식으로 스푸핑 방지 (S1 완료)
- WS rate limit 설계: 명령 10건/분, 상태 30건/분, 전체 60건/분

**발견된 문제:**

| # | 문제 | 심각도 | 근거 |
|---|------|--------|------|
| R1 | **WS rate limit 구현 부재** | 🟡 Medium | relay-infra §5.8에서 WS rate limit을 정의했으나 구현은 T2. WS 연결 자체에 대한 connection rate limit (연결 시도 횟수/IP)이 설계에 없음. 악의적 클라이언트가 WS 연결을 반복 생성하여 서버 리소스 고갈 가능. |
| R2 | **인메모리 폴백의 multi-worker 분산 문제** | 🟡 Medium | Redis 폴백 시 인메모리 카운터 사용 → multi-worker 환경에서 worker 수 배로 허용량 증가. production-hardening M3에서 인지하고 있으나, 폴백 전략이 "요청 허용 + 경고 로그"도 옵션으로 포함됨. DDoS 상황에서 Redis 장애와 동시에 rate limit 무력화되는 최악 시나리오. |
| R3 | **`/auth/refresh`, `/auth/logout` rate limit 미구현** | 🟡 Medium | security-audit H7에서 지적. 현재 코드에 해당 엔드포인트용 limiter가 없음. DB DoS 벡터로 유효. |
| R4 | **WS ping/pong 30초 무응답 세션 종료가 DDoS에 불충분** | 🟢 Low | Slowloris 스타일 공격 — 유효한 JWT로 연결 후 데이터를 극소량만 전송하여 연결 유지. 동시 연결 수 제한(per-user) + 전체 연결 수 상한이 필요. |

**권고:**
1. Redis 폴백 시 "요청 거부 + 경고"가 "요청 허용 + 경고"보다 안전 (fail-closed)
2. WS connection rate limit 추가 (IP당 분당 N회)
3. `/auth/refresh`, `/auth/logout` limiter를 Phase A 잔여에 포함

---

## 5. 킬스위치 안전성 (오프라인 큐 지연)

### 판정: ✅ 통과

**설계 분석:**
- 로컬 온라인: WS로 즉시 전달 → 지연 최소 (네트워크 레이턴시만)
- 로컬 오프라인: `pending_commands` DB에 저장 → 재연결 시 flush
- 사용자에게 "로컬 서버 복귀 시 즉시 적용됩니다" 명시적 고지
- arm(재개)은 로컬 오프라인 시 금지 → 비대칭 안전장치 (정지는 쉽게, 재개는 어렵게)

**평가:**
- 오프라인 킬스위치 지연은 **허용 가능**. 로컬 서버가 오프라인이면 매매 엔진도 동작하지 않으므로, 킬스위치 자체가 불필요한 상태.
- 단, 로컬 서버가 클라우드 WS만 끊기고 브로커 연결은 유지되는 시나리오(네트워크 파티션)에서는 매매가 계속되면서 킬스위치가 전달되지 않는 위험 존재.

| # | 문제 | 심각도 | 근거 |
|---|------|--------|------|
| K1 | **네트워크 파티션 시나리오 미고려** | 🟡 Medium | 클라우드 WS 끊김 ≠ 브로커 연결 끊김. 로컬→클라우드 WS만 단절된 상태에서 브로커 연결은 유지되어 매매가 지속될 수 있음. 로컬 서버의 자체 안전장치(loss_lock 등)가 이를 보완하나, WS 끊김 시 자동 킬스위치 발동 옵션이 있으면 더 안전. |

**권고:**
1. 로컬 서버에 `ws_disconnect_timeout` 설정 추가 — 클라우드 WS가 N분 이상 끊기면 자동 킬스위치 발동 옵션 제공 (기본 비활성, 사용자 선택)

---

## 6. 토큰 관리 (JWT, RT rotation, 노출 방지)

### 판정: ⚠️ 주의

**잘 되어 있는 부분:**
- Argon2id 비밀번호 해싱 (OWASP 권장)
- RefreshToken SHA-256 해시 저장 + 회전
- JWT는 sessionStorage 저장 (탭 종료 시 소멸)
- RT는 "로그인 유지" 선택 시에만 localStorage, 아니면 sessionStorage (S3 구현 완료)
- `generate_token()`에 `secrets.token_urlsafe` 사용

**미해결 문제:**

| # | 문제 | 심각도 | 근거 |
|---|------|--------|------|
| T1 | **RT가 여전히 JS 접근 가능 (C4 미해결)** | 🔴 High | security-audit C4에서 "httpOnly cookie 전환" 권고. 현재 RT가 localStorage/sessionStorage에 저장되어 XSS 1줄로 탈취 가능. "로그인 유지" 선택 시 localStorage → 더 넓은 공격 표면. spec에 인지되어 있으나 구현 계획이 없음. |
| T2 | **JWT HS256 알고리즘** | 🟢 Low | 단일 서버에서는 문제없으나, 마이크로서비스 확장 시 RS256/ES256 전환 필요. 현재는 적절. |
| T3 | **비밀번호 검증 API brute-force 보호** | 🟢 Low | remote-ops §5.3에서 5회 실패 시 10분 잠금 설계. 잠금 상태를 어디에 저장하는지 미명시 (Redis? DB? 인메모리?). 인메모리면 multi-worker 문제 재발. |

**권고:**
1. C4 (httpOnly cookie RT) 구현을 T2 이전으로 당기기 — 원격 제어 기능이 추가되면 XSS 영향 범위가 확대됨
2. `verify-password` 잠금 카운터는 Redis 사용 명시

---

## 7. M1~M6 우선순위 평가

### 판정: ⚠️ 주의 (우선순위 재조정 필요)

| ID | 현재 등급 | 재평가 | 근거 |
|----|----------|--------|------|
| M1 | P2 Medium | **P1 High로 격상 권고** | `require_local_secret`이 있으나 allowlist 없이는 secret 탈취 시 SSRF 체인 완성. T2에서 원격 접근이 추가되면 공격 표면 확대. |
| M2 | P2 Medium | P2 유지 | 토큰 12자 노출. `require_local_secret` 뒤이므로 영향 제한적. |
| M3 | P2 Medium | P2 유지 | Redis 폴백 문제. 프로덕션 배포 전 해결 필요하나 개발 단계에서는 수용 가능. |
| M4 | P2 Medium | **P1 High로 격상 권고** | `CONFIG_ENCRYPTION_KEY` 미검증으로 서비스키가 평문 저장될 수 있음. 프로덕션에서 조용히 실패하면 금융 데이터 유출 가능. |
| M5 | P2 Medium | P2 유지 | dev 모드 한정. 프로덕션 영향 없음. |
| M6 | P2 Medium | ✅ 해결됨 | production-hardening spec에서 확인. |

**추가 의견:**
- C4 (RT httpOnly cookie)가 "출시 전 필수"로 분류되어 있으나 구현 계획에 포함되지 않음. T3에 포함시켜야 함.
- H7 (`/auth/refresh`, `/auth/logout` rate limit)도 구현 계획 미배정.

---

## 8. 미발견 위협 (현재 spec에서 다루지 않은 보안 위협)

### 8.1 ❌ WS 메시지 replay 공격

**위험도: 🟡 Medium**

relay-infra의 메시지 프로토콜에 `id`(uuid)와 `ts`(타임스탬프)가 있으나, **replay 방지 메커니즘이 명시되지 않음**. 공격자가 네트워크에서 캡처한 `command` 메시지(예: arm 명령)를 재전송할 수 있음.

**권고:** 메시지 수신 측에서 `id` 중복 검사 + `ts` 유효 윈도우(예: 30초) 검증 추가.

### 8.2 ❌ IndexedDB 키 보호 부재

**위험도: 🟡 Medium**

E2E 키가 IndexedDB에 평문 base64로 저장됨 (`e2eCrypto.ts` line 40). IndexedDB는 같은 origin의 모든 JS에서 접근 가능 → XSS 시 E2E 키 탈취. 이는 RT XSS 탈취(C4)와 동일한 공격 표면이나, E2E 키는 rotation 없이 장기간 유효하므로 영향이 더 큼.

**권고:** Web Crypto API의 `extractable: false` CryptoKey 객체를 IndexedDB에 저장하면 JS에서 raw key 추출 불가. (현재 구현은 raw base64 저장)

### 8.3 ⚠️ pending_commands 무결성

**위험도: 🟢 Low**

오프라인 명령 큐가 클라우드 DB에 평문 저장. 클라우드 DB 접근 권한이 있는 공격자가 `pending_commands`에 kill/arm 명령 삽입 가능. 명령 서명이 없으므로 로컬 서버가 정당한 명령으로 처리.

**권고:** 명령에 디바이스 서명(HMAC with device key) 추가. 로컬 서버가 디바이스 키로 서명 검증 후 실행.

### 8.4 ⚠️ OAuth2 토큰 저장 및 scope 관리

**위험도: 🟢 Low**

auth-extension에서 Google/Kakao OAuth2 access_token을 서버에서 사용자 프로필 조회 후 어떻게 처리하는지 미명시. access_token을 DB에 저장하면 불필요한 위험. 프로필 조회 후 즉시 폐기해야 함.

**권고:** OAuth2 provider access_token은 callback 처리 후 메모리에서 즉시 폐기, DB 저장 금지 명시.

### 8.5 ⚠️ Service Worker 업데이트 무결성

**위험도: 🟢 Low**

PWA의 `sw.js`와 `firebase-messaging-sw.js`가 공격자에 의해 교체되면 전체 트래픽 가로채기 가능. CDN 또는 호스팅 침해 시나리오.

**권고:** CSP(H2)의 `script-src 'self'` + SRI(Subresource Integrity)로 완화. 프로덕션 배포 파이프라인에서 SW 파일 해시 검증.

### 8.6 ❌ 로컬 서버 자체의 WS 인증 부재 (새 발견)

**위험도: 🟡 Medium**

현재 코드 상태: `local_server/routers/ws.py`에 대한 H3(WS Origin 검증)이 security-audit에서 지적됨. 그러나 production-hardening spec의 M1~M6과 A2(S6: WS Origin 검증)에서 **cloud_server의 WS Origin 검증만** 완료된 것으로 보임. 로컬 서버 WS에 `require_local_secret` + Origin 검증이 적용되었는지 확인 필요.

---

## 종합 판정 요약

| 기준 | 판정 | 핵심 근거 |
|------|------|----------|
| 인증/인가 | ⚠️ 주의 | OAuth2 state/PKCE 누락, 이메일 미검증 계정 연동 위험 |
| E2E 암호화 | ✅ 통과 | AES-256-GCM 설계 건전, IV 관리 올바름, 키 분리 적절 |
| SSRF/Injection | ⚠️ 주의 | Config allowlist 미구현 (spec만 존재), rules injection 잔존 |
| Rate Limiting | ⚠️ 주의 | WS rate limit 미구현, 폴백 전략 개선 필요, /refresh /logout 미보호 |
| 킬스위치 안전성 | ✅ 통과 | 오프라인 지연 허용 가능, 네트워크 파티션 시나리오만 보완 권고 |
| 토큰 관리 | ⚠️ 주의 | C4 (httpOnly cookie RT) 미구현이 최대 리스크 |
| M1~M6 우선순위 | ⚠️ 주의 | M1, M4 격상 권고 |
| 미발견 위협 | 6건 발견 | WS replay, IndexedDB 키 보호, 명령 서명, OAuth2 토큰 폐기, SW 무결성, 로컬 WS 인증 |

---

## 우선 조치 권고 (T2 착수 전)

1. **OAuth2 state + PKCE** 설계에 반영 (auth-extension spec 수정)
2. **Config allowlist** 구현을 T1으로 당기기 (M1)
3. **C4 (httpOnly cookie RT)** 구현 계획 수립 — T2에서 원격 접근 추가 시 XSS 영향 확대
4. **IndexedDB 키를 non-extractable CryptoKey로 저장** (e2eCrypto.ts 수정)
5. **WS replay 방지** 메시지 프로토콜에 추가 (relay-infra spec 수정)
6. **`/auth/refresh`, `/auth/logout` rate limit** 추가
7. **OAuth2 provider email_verified 검증** 로직 명시

---

## 관련 문서

| 문서 | 역할 |
|------|------|
| `docs/research/security-audit-report.md` | 원본 보안 감사 |
| `spec/production-hardening/spec.md` | M1~M6 + H1~H3 |
| `spec/relay-infra/spec.md` | WS + E2E 설계 |
| `spec/remote-ops/spec.md` | 킬스위치 + arm + FCM |
| `spec/auth-extension/spec.md` | OAuth2 + 디바이스 관리 |
| `docs/development-plan-v3.md` | 전체 구현 백로그 |
