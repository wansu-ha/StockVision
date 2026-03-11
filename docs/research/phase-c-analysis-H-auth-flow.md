> 작성일: 2026-03-12 | Phase C 분석 H: 인증/권한 흐름

# H. 인증/권한 흐름 전수 조사

## 요약

3계층 인증 아키텍처:
1. **클라우드**: JWT (HS256, 1시간) + Refresh Token Rotation (30일)
2. **프론트엔드**: sessionStorage (JWT) + localStorage (RT, email)
3. **로컬 서버**: Windows Keyring 암호화 + local_secret (CSRF 방어)

## H-1. 클라우드 인증

### User 모델 (`cloud_server/models/user.py`)
```
id (UUID), email (unique), email_verified, password_hash (Argon2id),
nickname, role ("user"|"admin"), is_active, created_at, last_login_at
```

### RefreshToken 모델
```
id, user_id, token_hash (SHA-256), expires_at (30일), created_at, rotated_at
```
- 평문 아닌 SHA-256 해시만 저장
- Rotation: 사용 시 삭제 → 새 토큰 발급

### 인증 엔드포인트

| 엔드포인트 | 설명 | Rate Limit |
|-----------|------|-----------|
| POST `/api/v1/auth/register` | 회원가입 + 이메일 인증 발송 | 5회/시간/IP |
| GET `/api/v1/auth/verify-email` | 이메일 인증 (24h TTL) | - |
| POST `/api/v1/auth/login` | 로그인 → JWT + RT 발급 | 10회/시간/IP |
| POST `/api/v1/auth/refresh` | JWT 갱신 (RT Rotation) | - |
| POST `/api/v1/auth/logout` | RT 삭제 | - |

### JWT 구조 (HS256)
```json
{ "sub": "user_id", "email": "...", "role": "user|admin", "iat": ..., "exp": +1h }
```
- SECRET_KEY 미설정 시 서버 시작 실패 (SEC-C2)

### 의존성 주입
- `current_user`: JWT 검증 → payload dict (401 if invalid)
- `require_admin`: role != "admin" → 403

## H-2. 프론트엔드 인증

### 토큰 저장소
| 키 | 저장소 | 용도 |
|----|--------|------|
| `sv_jwt` | sessionStorage | JWT (탭 닫으면 삭제) |
| `sv_rt` | localStorage | Refresh Token (영구) |
| `sv_email` | localStorage | 사용자 식별 |

### 마운트 시 복원 (AuthContext useEffect)
1. JWT + RT 있음 → 로컬 서버에 전달
2. JWT 만료, RT 있음 → 클라우드 refresh → 로컬 전달
3. 둘 다 없음 → 로컬 서버에서 restore() 시도

### 401 자동 갱신 (cloudClient 인터셉터)
1단계: `localAuth.restore()` — 로컬 서버 우선
2단계: `cloudAuth.refresh(rt)` — 클라우드 폴백
실패 시: `/login` 리다이렉트

## H-3. 로컬 서버 인증

### local_secret
- 서버 시작 시 `secrets.token_hex(32)` 생성 (메모리 전용)
- 모든 보호 엔드포인트에 `X-Local-Secret` 헤더 검증
- `hmac.compare_digest` (timing attack 방어)

### Keyring 저장 (`local_server/storage/credential.py`)
- 서비스명: `stockvision:{email}` (사용자별 격리)
- Windows Credential Manager DPAPI 암호화
- 키: `sv_cloud_access_token`, `sv_cloud_refresh_token`

### 로컬 인증 API

| 엔드포인트 | 설명 |
|-----------|------|
| POST `/api/auth/token` | JWT 등록 → keyring 저장 + local_secret 반환 |
| POST `/api/auth/restore` | keyring 토큰 반환 (만료 시 자동 refresh) |
| POST `/api/auth/logout` | keyring 전체 삭제 |
| GET `/api/auth/status` | 토큰 존재 여부 (토큰 자체 미노출) |

### /api/auth/restore 주요 로직
- JWT 만료 확인 (60초 leeway)
- 만료 시 `_refresh_lock`으로 동시 갱신 방지
- Double-check: lock 내부에서 재확인 (선행 요청 감지)

### 서버 시작 시 토큰 복원 (`local_server/main.py`)
1. config에서 `auth.last_user` 복원
2. keyring에서 토큰 조회
3. access_token 없으면 refresh_token으로 자동 갱신
4. 실패해도 서버는 시작 (수동 로그인 필요)

## H-4. 하트비트 토큰 갱신

- 30초마다 하트비트 전송 (heartbeat.py)
- 401 감지 시 `_try_refresh()`:
  - `_refresh_lock`으로 동시 갱신 방지
  - `is_jwt_expired(token, leeway=60)` 확인
  - 성공 → keyring 업데이트 + CloudClient 토큰 교체
  - 실패 → 토스트 알림 ("재로그인 필요")

## H-5. 흐름도

### 로그인 → 사용
```
Login → Cloud /login → JWT + RT
  → sessionStorage(JWT) + localStorage(RT)
  → Local /auth/token → keyring 저장 + local_secret 반환
  → API 요청 (Authorization: Bearer JWT, X-Local-Secret)
```

### 401 자동 갱신
```
Cloud API 401
  → localAuth.restore() (로컬 우선)
  → cloudAuth.refresh(rt) (클라우드 폴백)
  → 토큰 갱신 → 원래 요청 재시도
```

### 하트비트 401
```
Heartbeat 401
  → _refresh_lock 획득
  → is_jwt_expired() 확인
  → CloudClient.refresh_access_token(rt)
  → keyring 업데이트 → 하트비트 재시도
```

## H-6. 오픈소스 독립성 관련

### 현재 상태
- 로컬 서버는 클라우드 JWT 없이도 **시작 가능** (토큰 갱신 실패 시 경고만)
- 규칙 sync: body에 rules 직접 제공하면 클라우드 호출 불필요
- CloudClient: `api_token=None`이면 JWT 헤더 미첨부

### JWT 없이 동작 가능한 부분
- 로컬 서버 시작, health check
- 규칙 sync (직접 제공 시)
- 브로커 연결, 엔진 실행

### JWT 필수 부분
- 클라우드 규칙 CRUD
- 하트비트 (버전 감지)
- 시장 데이터 API (current_user 의존)

## H-7. 보안 결정사항

| 항목 | 구현 | 이유 |
|------|------|------|
| 비밀번호 해싱 | Argon2id | OWASP 2023 권장 |
| JWT 만료 | 1시간 | 탈취 위험 감소 |
| RT 만료 | 30일 Sliding | 사용자 편의 |
| RT Rotation | O | 탈취 감지 |
| Token 저장 | SHA-256 해시 | DB 탈취 대응 |
| local_secret | HMAC compare | Timing attack 방어 |
| Keyring | DPAPI | OS 수준 암호화 |

## H-8. 미구현

- JWT revocation list (로그아웃 후 즉시 무효화 없음 — 만료까지 유효)
- 2FA / MFA
- 세션 관리 UI (다기기 로그인)
- Refresh Token 동시 사용 감지 (Rotation만)

## 주요 파일 경로

| 파일 | 역할 |
|------|------|
| `cloud_server/api/auth.py` | 인증 API (register/login/refresh/logout) |
| `cloud_server/models/user.py` | User, RefreshToken 모델 |
| `cloud_server/api/dependencies.py` | current_user, require_admin |
| `cloud_server/core/security.py` | JWT 생성/검증, Argon2id |
| `frontend/src/context/AuthContext.tsx` | 인증 상태 관리, 토큰 복원 |
| `frontend/src/services/cloudClient.ts` | 401 자동 갱신 인터셉터 |
| `frontend/src/services/localClient.ts` | local_secret 관리 |
| `local_server/routers/auth.py` | 로컬 인증 API |
| `local_server/storage/credential.py` | Keyring 저장소 |
| `local_server/core/local_auth.py` | local_secret 생성/검증 |
| `local_server/cloud/heartbeat.py` | 하트비트 + 401 자동 갱신 |
| `local_server/cloud/token_utils.py` | JWT 만료 확인 |
