# 보안 점검 보고서

> 점검일: 2026-03-08 | 범위: frontend, cloud_server, local_server

## 중요도 체계

| 등급 | 의미 | 기준 |
|------|------|------|
| **P0 Critical** | 출시 전 반드시 수정 | 인증 없이 자산/계정 탈취 가능 |
| **P1 High** | 출시 전 수정 권장 | 보조 공격 벡터 또는 조건부 탈취 |
| **P2 Medium** | 출시 전 인지, 하드닝 시 수정 | 운영 환경 의존 또는 제한적 영향 |

---

## P0 Critical (4건)

### C1. local_server — 모든 mutation API에 인증 없음

| 항목 | 내용 |
|------|------|
| **위치** | 전체 라우터 (`auth.py`, `config.py`, `trading.py`, `rules.py`) |
| **위험** | 주문 실행, 전략 시작/중단, broker 키 저장, cloud URL 변경 등 전부 인증 없이 호출 가능 |
| **공격 시나리오** | 1) 같은 PC의 악성 프로세스가 `curl localhost:4020/api/trading/order` 호출 → 실매매<br>2) 브라우저 CSRF: `<form action="http://localhost:4020/api/auth/logout">` → 모든 credential 삭제 |
| **영향** | 실거래 주문, credential 탈취/삭제, 전략 엔진 제어 — **전체 시스템 장악** |
| **악용 난이도** | 매우 낮음 (로컬 프로세스는 CORS 무시, 브라우저도 form POST로 우회) |
| **수정 방향** | 프로세스 시작 시 `secrets.token_hex(32)` 생성 → `~/.stockvision/local_secret` 파일에 저장 → 모든 mutation에 `X-Local-Secret` 헤더 검증 Depends 추가. Jupyter/code-server 표준 패턴 |
| **상태** | **즉시 수정 대상** → `spec/security-hardening/plan.md` Step 1. Step 1은 브라우저 CSRF를 완화한다. 같은 사용자 세션의 로컬 악성 프로세스 리스크는 잔존하며 OS 수준 격리가 필요 (plan 위협 모델 참조) |

### C2. local_server — CORS가 CSRF를 막지 못함

| 항목 | 내용 |
|------|------|
| **위치** | `local_server/main.py` CORS 설정 |
| **위험** | `allow_methods=["*"]` + `allow_credentials=True`이지만 CORS는 브라우저 응답 차단일 뿐 **요청 발송 자체는 막지 않음**. form POST는 preflight 없이 도달 |
| **공격 시나리오** | 악성 웹페이지에서 `POST /api/auth/logout` (body 불필요) → credential 전체 삭제 성공 |
| **영향** | C1과 결합 시 모든 state mutation 공격 가능 |
| **악용 난이도** | 낮음 |
| **수정 방향** | C1의 shared secret이 근본 해결. 보조로 `allow_methods` 제한 + Origin 검증 미들웨어 |
| **상태** | **즉시 수정 대상** → C1과 함께 해결 (CSRF 벡터 완화. 로컬 프로세스 리스크는 C1 참조) |

### C3. cloud_server — 이메일 인증/비밀번호 재설정 토큰 평문 저장

| 항목 | 내용 |
|------|------|
| **위치** | `cloud_server/models/user.py` `EmailVerificationToken.token`, `PasswordResetToken.token` |
| **위험** | DB에 raw token 저장. `RefreshToken`은 `hash_token()` 적용 — 불일치 |
| **공격 시나리오** | DB 읽기 접근 (SQL injection, 백업 유출, 관리자 접근) → 활성 reset token 추출 → 비밀번호 변경 → 계정 탈취 |
| **영향** | 비밀번호 재설정 10분 윈도우 내 모든 계정 탈취 가능 |
| **악용 난이도** | 낮음 (DB 읽기만 필요, 크래킹 불필요) |
| **수정 방향** | `RefreshToken`과 동일 패턴 적용: `token_hash = hash_token(token)` 저장, 조회 시 해시 비교 |
| **상태** | 출시 전 필수 — 별도 계획 (DB 마이그레이션 필요) |

### C4. frontend — refresh token을 localStorage에 저장

| 항목 | 내용 |
|------|------|
| **위치** | `frontend/src/context/AuthContext.tsx` `localStorage.setItem('sv_rt', ...)` |
| **위험** | `localStorage`는 같은 origin의 모든 JS에서 접근 가능. XSS 한 줄로 탈취 |
| **공격 시나리오** | npm supply chain 공격 (Recharts/HeroUI 등 transitive dep) → `localStorage.getItem('sv_rt')` → 공격자 서버로 전송 → 무한 refresh로 영구 세션 탈취 |
| **영향** | 전체 계정 영구 탈취 (refresh token으로 무한 갱신) |
| **악용 난이도** | 낮음 (XSS 벡터만 있으면 1줄) |
| **수정 방향** | refresh token을 `Set-Cookie: HttpOnly; Secure; SameSite=Strict`로 전환. `/auth/refresh`가 cookie에서 읽도록 백엔드 수정 필요 |
| **상태** | 출시 전 필수 — 별도 계획 (백엔드+프론트 동시 수정 필요) |

---

## P1 High (7건)

### H1. local_server — refresh token을 `token.dat` 평문 파일로 저장

| 항목 | 내용 |
|------|------|
| **위치** | `local_server/cloud/auth_client.py` `_TOKEN_DAT` |
| **위험** | `%APPDATA%\StockVision\token.dat`에 평문 저장. broker key는 Keyring(DPAPI)인데 refresh token만 파일 — 불일치 |
| **공격** | 같은 Windows 사용자 세션의 모든 프로세스가 파일 읽기 가능 |
| **수정** | `credential.py`의 `save_credential(KEY_CLOUD_REFRESH_TOKEN, ...)` 사용으로 통일 |
| **상태** | **즉시 수정 대상** → `spec/security-hardening/plan.md` Step 2 |

### H2. local_server — `/api/rules/sync`가 임의 규칙 주입 허용

| 항목 | 내용 |
|------|------|
| **위치** | `local_server/routers/rules.py` `body.rules` |
| **위험** | `list[dict[str, Any]]` 그대로 설치. 서명 검증 없음. C1과 결합 시 → 규칙 주입 → 전략 시작 → 실매매 |
| **수정** | body.rules 직접 주입 경로 제거. cloud에서만 fetch하거나 서명 검증 |
| **상태** | 출시 전 수정 → C1 해결 시 위험도 대폭 감소 |

### H3. local_server — WebSocket에 인증/Origin 검증 없음

| 항목 | 내용 |
|------|------|
| **위치** | `local_server/routers/ws.py` |
| **위험** | 악성 웹페이지가 `new WebSocket("ws://localhost:4020/ws")` → 체결/포지션 데이터 실시간 수신 |
| **수정** | WebSocket handshake 시 Origin 헤더 검증 + shared secret 검증 |
| **상태** | 출시 전 수정 |

### H4. cloud_server — rate limiter X-Forwarded-For 스푸핑 우회

| 항목 | 내용 |
|------|------|
| **위치** | `cloud_server/core/rate_limit.py` `_get_ip()` |
| **위험** | 클라이언트가 `X-Forwarded-For: 임의IP`를 보내면 rate limit 완전 우회 → 무제한 로그인 시도 |
| **수정** | `TRUSTED_PROXY_IPS` 설정 도입. 신뢰 프록시가 아니면 헤더 무시 |
| **상태** | 출시 전 수정 |

### H5. cloud_server — 비밀번호 최소 길이/복잡도 검증 없음

| 항목 | 내용 |
|------|------|
| **위치** | `cloud_server/api/auth.py` `RegisterBody`, `ResetPasswordBody` |
| **위험** | 빈 문자열 `""` 비밀번호로 가입 가능. H4와 결합 시 brute force 즉시 성공 |
| **수정** | Pydantic `field_validator`로 최소 8자 검증 |
| **상태** | **즉시 수정 대상** → `spec/security-hardening/plan.md` Step 3 |

### H6. frontend — 비밀번호 재설정 토큰이 URL 쿼리 파라미터에 노출

| 항목 | 내용 |
|------|------|
| **위치** | `frontend/src/pages/ResetPassword.tsx`, `frontend/src/services/auth.ts` |
| **위험** | `?token=...`이 브라우저 히스토리, Referer 헤더, 서버 액세스 로그에 남음 |
| **수정** | URL fragment (`#token=...`) 사용 또는 POST body 전환 |
| **상태** | 출시 전 수정 |

### H7. cloud_server — `/auth/refresh`, `/auth/logout`에 rate limit 없음

| 항목 | 내용 |
|------|------|
| **위치** | `cloud_server/api/auth.py` |
| **위험** | 인증 불필요 엔드포인트에 무제한 요청 → DB DoS 벡터 |
| **수정** | `/auth/refresh`, `/auth/logout`에 60회/시간/IP rate limit 적용 |
| **상태** | 출시 전 수정 |

---

## P2 Medium (6건)

| ID | 위치 | 이슈 | 수정 방향 | 상태 |
|----|------|------|----------|------|
| **M1** | local_server `config.py` | `PATCH /api/config`로 `cloud.url` 변경 가능 → SSRF + credential 유출 체인 | config key allowlist 또는 C1 shared secret | C1 해결 시 완화 |
| **M2** | local_server `auth.py` | `GET /api/auth/status`에서 토큰 앞 12자 노출 | `has_cloud_token: bool`로 변경 | 프로덕션 하드닝 |
| **M3** | cloud_server `rate_limit.py` | in-memory rate limiter가 multi-worker 시 분산 → 보호 무력화 | 프로덕션 배포 전 Redis 전환 (이미 TODO) | 프로덕션 하드닝 |
| **M4** | cloud_server `config.py` | `CONFIG_ENCRYPTION_KEY` 미설정 시 시작은 되지만 service-key 암호화 실패 | `validate_settings()`에 추가 | 프로덕션 하드닝 |
| **M5** | cloud_server `email.py` | dev 모드에서 토큰이 포함된 이메일 본문을 INFO 로그에 출력 | 토큰 제외 로깅 | 프로덕션 하드닝 |
| **M6** | frontend `onboarding.ts` | `localStorage.getItem('jwt')` — 사용되지 않는 키 → 항상 null → 인증 우회 | `sessionStorage.getItem('sv_jwt')`로 수정 | 출시 전 수정 |

---

## 잘 되어 있는 부분

- **Argon2id** 비밀번호 해싱 (OWASP 권장 파라미터)
- **RefreshToken** SHA-256 해시 저장 + 회전
- `is_active`, `email_verified` 로그인 게이트
- 이메일 열거 방지 (`forgot-password` 동일 응답)
- 모든 cloud_server data mutation에 JWT 인증
- admin 엔드포인트 별도 `require_admin` 의존성
- `SECRET_KEY` 시작 시 검증
- `generate_token()`에 `secrets.token_urlsafe` 사용
- broker 키/cloud JWT를 Windows Keyring(DPAPI)에 저장

---

## 수정 순서 요약

### 즉시 수정 (3건)
1. C1+C2: local_server shared secret 인증
2. H1: token.dat → Keyring 통일
3. H5: 비밀번호 최소 8자 검증

### 출시 전 필수 (7건)
4. C3: 이메일/리셋 토큰 해싱
5. C4: refresh token httpOnly cookie 전환
6. H4: rate limiter XFF 검증
7. H2: rules injection 차단
8. H3: WebSocket Origin 검증
9. H6: reset token URL 노출
10. H7: refresh/logout rate limit

### 프로덕션 하드닝
- M1~M6, Redis rate limiter, HTTPS 강제, CSP 헤더, dependency audit CI

---

## 관련 문서

- `spec/security-hardening/plan.md` — 즉시 수정 구현 계획
- `docs/architecture.md` — 3프로세스 아키텍처
- `spec/local-server-core/spec.md` — 로컬 서버 명세
- `spec/cloud-server/spec.md` — 클라우드 서버 명세
- `spec/frontend/spec.md` — 프론트엔드 명세
