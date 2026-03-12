# 인증 확장 구현 계획

> 작성일: 2026-03-12 | 상태: 초안 | Phase C (C6-b)

## 아키텍처

```
프론트엔드                      클라우드 서버                    로컬 서버
┌──────────────┐              ┌─────────────────┐           ┌──────────────┐
│ LoginPage    │──── REST ───►│ /auth/oauth/*    │           │              │
│ (Google/Kakao│              │ OAuthService     │           │              │
│  버튼 추가)  │              │   → JWT 발급     │           │              │
│              │              │                  │           │              │
│ Settings     │──── REST ───►│ /devices/*       │           │ /api/devices │
│ (디바이스    │              │ DeviceService    │◄── WS ───│ /pair/init   │
│  관리 UI)    │              │   → 메타데이터   │           │ /pair/complete│
│              │              │                  │           │ E2ECrypto    │
│ QR Scanner   │──── local ──►│                  │           │ (키 생성)    │
│ (페어링)     │              │ EmailService     │           │              │
└──────────────┘              └─────────────────┘           └──────────────┘
```

## 수정 파일 목록

### 클라우드 서버 (신규 5, 수정 4)

| 파일 | 변경 | 내용 |
|------|------|------|
| `cloud_server/models/oauth_account.py` | 신규 | `OAuthAccount` 모델 (provider, provider_user_id) |
| `cloud_server/models/device.py` | 신규 | `Device` 모델 (id, user_id, name, platform, last_seen) |
| `cloud_server/services/oauth_service.py` | 신규 | Google/Kakao OAuth2 처리, 코드 교환, 사용자 연동 |
| `cloud_server/services/email_service.py` | 신규 | SendGrid 기반 이메일 발송 (인증, 비밀번호 재설정, 디바이스 알림) |
| `cloud_server/api/devices.py` | 신규 | 디바이스 관리 REST API |
| `cloud_server/api/auth.py` | 수정 | OAuth2 엔드포인트 추가, 이메일 발송 연동 |
| `cloud_server/core/config.py` | 수정 | OAuth2 + 이메일 환경변수 |
| `cloud_server/core/init_db.py` | 수정 | 신규 모델 import |
| `cloud_server/main.py` | 수정 | devices 라우터 등록 |

### 로컬 서버 (신규 1, 수정 1)

| 파일 | 변경 | 내용 |
|------|------|------|
| `local_server/routers/devices.py` | 신규 | 페어링 엔드포인트 (init, complete) |
| `local_server/main.py` | 수정 | 디바이스 라우터 등록 |

### 프론트엔드 (신규 3, 수정 3)

| 파일 | 변경 | 내용 |
|------|------|------|
| `frontend/src/components/OAuthButtons.tsx` | 신규 | Google/Kakao 로그인 버튼 |
| `frontend/src/components/DeviceManager.tsx` | 신규 | 디바이스 목록 + QR 페어링 + 해제 |
| `frontend/src/components/QRPairingDialog.tsx` | 신규 | QR코드 표시/스캔 다이얼로그 |
| `frontend/src/pages/Login.tsx` | 수정 | OAuth 버튼 추가 |
| `frontend/src/pages/Settings.tsx` | 수정 | 디바이스 관리 섹션 추가 |
| `frontend/src/services/cloudClient.ts` | 수정 | OAuth, 디바이스 API 호출 추가 |

## 구현 순서

### Step 1: OAuthAccount 모델 + DB

**파일**:
1. `cloud_server/models/oauth_account.py` — 모델 정의
2. `cloud_server/core/init_db.py` — import 추가

**verify**: 클라우드 서버 시작 → `oauth_accounts` 테이블 생성 확인

---

### Step 2: Google OAuth2 백엔드

**파일**:
1. `cloud_server/services/oauth_service.py`
   - `OAuthService` 클래스
   - `get_google_auth_url(redirect_uri) → str` — 인증 URL 생성
   - `exchange_google_code(code, redirect_uri) → dict` — code → access_token 교환
   - `get_google_profile(access_token) → dict` — email, name 조회
   - `login_or_register(provider, provider_user_id, email, name, db) → dict` — 사용자 조회/생성 → JWT 발급
   - 라이브러리: `httpx` (외부 의존성 없이 HTTP 호출)

2. `cloud_server/api/auth.py` 수정
   - `GET /api/v1/auth/oauth/google/login` → 인증 URL 반환
   - `POST /api/v1/auth/oauth/google/callback` → code 교환 → JWT 발급
   - 기존 로그인과 동일 응답 형식

3. `cloud_server/core/config.py` 수정
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`

**verify**: curl로 `/oauth/google/login` → URL 반환 → 브라우저에서 Google 로그인 → 콜백 → JWT 수신

---

### Step 3: Google OAuth2 프론트엔드

**파일**:
1. `frontend/src/components/OAuthButtons.tsx`
   - Google 로그인 버튼 (Google 가이드라인 스타일)
   - 클릭 → `GET /api/v1/auth/oauth/google/login` → 리다이렉트
   - 콜백 처리 → JWT 저장 → 대시보드 이동

2. `frontend/src/pages/Login.tsx` 수정
   - 기존 이메일/비밀번호 폼 아래 구분선 + OAuthButtons 추가

3. `frontend/src/services/cloudClient.ts` 수정
   - `oauth.getGoogleLoginUrl()`, `oauth.googleCallback(code)`

**verify**: 로그인 페이지 → "Google로 로그인" → Google 인증 → 자동 가입/로그인 → 대시보드

---

### Step 4: 이메일 발송 인프라

**파일**:
1. `cloud_server/services/email_service.py`
   - `EmailService` 클래스
   - `send_verification(to, token)` — 인증 메일 (HTML 템플릿)
   - `send_password_reset(to, token)` — 비밀번호 재설정 메일
   - `send_device_alert(to, device_name)` — 새 디바이스 등록 알림
   - SendGrid HTTP API 사용 (`httpx`)

2. `cloud_server/api/auth.py` 수정
   - `register()` — 기존 stub → `EmailService.send_verification()` 호출
   - `forgot_password()` — 기존 stub → `EmailService.send_password_reset()` 호출

3. `cloud_server/core/config.py` 수정
   - `EMAIL_PROVIDER`, `EMAIL_API_KEY`, `EMAIL_FROM`

**verify**: 가입 → 인증 메일 수신 → 링크 클릭 → email_verified=True 확인

---

### Step 5: Kakao OAuth2

Step 2-3과 동일 패턴. Google과 병렬 구현 가능.

**파일**:
1. `cloud_server/services/oauth_service.py` 수정
   - `get_kakao_auth_url()`, `exchange_kakao_code()`, `get_kakao_profile()`
   - Kakao REST API 엔드포인트 사용

2. `cloud_server/api/auth.py` 수정
   - `GET /api/v1/auth/oauth/kakao/login`
   - `POST /api/v1/auth/oauth/kakao/callback`

3. `frontend/src/components/OAuthButtons.tsx` 수정
   - Kakao 로그인 버튼 추가

4. `cloud_server/core/config.py` 수정
   - `KAKAO_CLIENT_ID`, `KAKAO_CLIENT_SECRET`, `KAKAO_REDIRECT_URI`

**verify**: "카카오로 로그인" → 카카오 인증 → JWT 발급 → 기존 Google 계정과 같은 이메일이면 계정 연동

---

### Step 6: Device 모델 + 관리 API

**파일**:
1. `cloud_server/models/device.py` — 모델 정의
2. `cloud_server/api/devices.py`
   - `GET /api/v1/devices` — 디바이스 목록 (user_id 기준)
   - `POST /api/v1/devices/register` — 메타데이터 등록
   - `DELETE /api/v1/devices/{device_id}` — 해제 (+ 로컬에 키 폐기 WS 명령)
3. `cloud_server/core/init_db.py` — Device import
4. `cloud_server/main.py` — devices 라우터 등록

**verify**: curl로 디바이스 CRUD 테스트

---

### Step 7: 로컬 서버 페어링

**파일**:
1. `local_server/routers/devices.py`
   - `POST /api/devices/pair/init` → E2ECrypto.generate_key() → { device_id, qr_data }
   - `POST /api/devices/pair/complete` → 클라우드에 디바이스 등록 요청 + 이메일 알림

2. `local_server/main.py` — 라우터 등록

**verify**: 로컬 프론트에서 "새 디바이스 추가" → QR 데이터 반환 → 클라우드 DB에 디바이스 등록

---

### Step 8: 디바이스 관리 UI

**파일**:
1. `frontend/src/components/DeviceManager.tsx`
   - 디바이스 목록 (이름, 플랫폼, 마지막 접속, 해제 버튼)
   - "새 디바이스 추가" 버튼 → QRPairingDialog

2. `frontend/src/components/QRPairingDialog.tsx`
   - QR코드 표시 (라이브러리: `qrcode.react`)
   - 복사 가능한 텍스트
   - "완료" 버튼 → pair/complete 호출

3. `frontend/src/pages/Settings.tsx` 수정
   - "연결된 디바이스" 섹션 추가

**verify**: Settings → 디바이스 목록 표시 → "추가" → QR → "해제" → 목록에서 제거

## 의존성 그래프

```
Step 1 (OAuthAccount 모델)
  └→ Step 2 (Google OAuth 백엔드)
       └→ Step 3 (Google OAuth 프론트)
  └→ Step 5 (Kakao OAuth) — Step 2와 병렬 가능

Step 4 (이메일 인프라) — 독립

Step 1 → Step 6 (Device 모델 + API)
  └→ Step 7 (로컬 페어링) — C6-a Step 6 (E2ECrypto) 의존
       └→ Step 8 (디바이스 관리 UI)
```

## 검증 방법

- OAuth2: 실제 Google/Kakao 로그인 플로우 테스트 (개발용 OAuth 앱 필요)
- 이메일: SendGrid sandbox 모드 또는 실제 발송 테스트
- 디바이스: 로컬 페어링 → QR → 클라우드 등록 → 해제 E2E 테스트
- 빌드: `npm run build` 통과
