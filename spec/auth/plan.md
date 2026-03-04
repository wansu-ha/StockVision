# 인증 기능 구현 계획서 (auth)

> 작성일: 2026-03-04 | 상태: 초안 | 브랜치: `feat/auth`

---

## 0. 전제 조건

- 의존: `spec/auth/spec.md` 확정 (2026-03-04)
- 법적 근거: `docs/legal.md` 참조
- 구현 대상: 클라우드 백엔드 API + 클라이언트(로컬 서버 + React) 연동
- 로컬 서버는 클라우드 API 클라이언트로 동작 (인증 서버 역할 없음)

---

## 1. 구현 단계 개요

| 단계 | 내용 | 검증 |
|------|------|------|
| Step 1 | 클라우드 DB 스키마 + 암호화 유틸 | pytest 단위 테스트 |
| Step 2 | 회원가입 + 이메일 인증 API | Postman / pytest |
| Step 3 | 로그인 + JWT + Refresh Token API | pytest |
| Step 4 | 설정 blob CRUD API (서버사이드 암호화) | pytest |
| Step 5 | 비밀번호 재설정 API | pytest |
| Step 6 | 로컬 서버 연동 (token.dat 관리 + 자동 재시작) | 통합 테스트 |
| Step 7 | React 로그인 UI + 인증 플로우 | 브라우저 확인 |

---

## 2. 상세 구현 계획

### Step 1 — DB 스키마 + 암호화 유틸

**목표:** 인증 관련 테이블 생성 + AES-256-GCM 암호화 유틸 구현

#### 1-1. DB 마이그레이션

파일: `backend/app/models/auth.py`

```python
class User(Base):
    __tablename__ = "users"
    id            = Column(UUID, primary_key=True, default=uuid4)
    email         = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)       # Argon2id
    email_verified = Column(Boolean, default=False)
    nickname      = Column(String, nullable=True)
    created_at    = Column(DateTime, default=utcnow)

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id         = Column(UUID, primary_key=True, default=uuid4)
    user_id    = Column(UUID, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, index=True)  # SHA-256(token)
    expires_at = Column(DateTime, nullable=False)            # 30일
    created_at = Column(DateTime, default=utcnow)

class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    id         = Column(UUID, primary_key=True, default=uuid4)
    user_id    = Column(UUID, ForeignKey("users.id"), nullable=False)
    token      = Column(String, nullable=False, index=True)  # urlsafe_token
    expires_at = Column(DateTime, nullable=False)            # 24시간
    used       = Column(Boolean, default=False)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id         = Column(UUID, primary_key=True, default=uuid4)
    user_id    = Column(UUID, ForeignKey("users.id"), nullable=False)
    token      = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)            # 10분
    used       = Column(Boolean, default=False)

class ConfigBlob(Base):
    __tablename__ = "config_blobs"
    user_id    = Column(UUID, ForeignKey("users.id"), primary_key=True)
    blob       = Column(LargeBinary, nullable=True)  # AES-256-GCM 암호화
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
```

#### 1-2. 암호화 유틸

파일: `backend/app/core/encryption.py`

```python
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_KEY = bytes.fromhex(os.environ["CONFIG_ENCRYPTION_KEY"])  # 32바이트 (64 hex chars)

def encrypt_blob(data: bytes) -> bytes:
    """평문 바이트 → nonce(12B) + ciphertext"""
    nonce = os.urandom(12)
    return nonce + AESGCM(_KEY).encrypt(nonce, data, None)

def decrypt_blob(blob: bytes) -> bytes:
    """nonce(12B) + ciphertext → 평문 바이트"""
    return AESGCM(_KEY).decrypt(blob[:12], blob[12:], None)
```

#### 1-3. 비밀번호 해싱 유틸

파일: `backend/app/core/password.py`

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

def hash_password(password: str) -> str:
    return _ph.hash(password)

def verify_password(hash: str, password: str) -> bool:
    try:
        return _ph.verify(hash, password)
    except VerifyMismatchError:
        return False
```

**검증 포인트:**
- [ ] `encrypt_blob(decrypt_blob(x)) == x` 단위 테스트
- [ ] Argon2id 해싱/검증 단위 테스트
- [ ] DB 마이그레이션 적용 확인 (`alembic upgrade head`)

---

### Step 2 — 회원가입 + 이메일 인증 API

**목표:** `POST /api/auth/register` → 이메일 인증 메일 발송

파일: `backend/app/api/auth.py`

```
POST /api/auth/register
  Body: { email, password, nickname? }
  → 중복 이메일 체크
  → Argon2id(password) → users 테이블 INSERT
  → urlsafe_token(32B) → email_verification_tokens INSERT (24h TTL)
  → SMTP: 인증 메일 발송 (링크: /api/auth/verify-email?token=...)
  → 200 { success: true, message: "인증 메일을 확인하세요" }

GET /api/auth/verify-email?token=...
  → token 조회 + 만료/사용 여부 확인
  → users.email_verified = true
  → email_verification_tokens.used = true
  → 200 { success: true }
```

**검증 포인트:**
- [ ] 중복 이메일 409 반환
- [ ] 만료 토큰 400 반환
- [ ] 이미 사용된 토큰 400 반환
- [ ] 이메일 미인증 사용자 로그인 시 403 반환

---

### Step 3 — 로그인 + JWT + Refresh Token API

**목표:** `POST /api/auth/login` → JWT(24h) + Refresh Token(30d) 반환

```
POST /api/auth/login
  Body: { email, password }
  → users 조회 + Argon2id.verify
  → 이메일 미인증 시 → 403 { message: "이메일 인증이 필요합니다" }
  → JWT 생성 (payload: user_id, email, exp=24h, iat)
  → urlsafe_token(32B) → SHA-256 → refresh_tokens INSERT (30d TTL)
  → 200 { jwt, refresh_token, expires_in: 86400 }

POST /api/auth/refresh
  Body: { refresh_token }
  → SHA-256(refresh_token) → refresh_tokens 조회
  → 만료/없음 → 401
  → 기존 토큰 삭제 (Rotation) + 새 토큰 INSERT
  → 새 JWT + 새 Refresh Token 반환

POST /api/auth/logout
  Body: { refresh_token }
  → SHA-256(refresh_token) → refresh_tokens 삭제
  → 200 { success: true }
```

**JWT 페이로드:**
```json
{ "sub": "user-uuid", "email": "user@example.com", "iat": 1234567890, "exp": 1234654290 }
```

**Rate Limit:** 로그인 실패 IP당 10회/시간 (SlowAPI 또는 Redis 기반)

**검증 포인트:**
- [ ] 잘못된 비밀번호 → 401 (실패 횟수 증가)
- [ ] 만료 Refresh Token → 401
- [ ] Token Rotation 동작 (이전 토큰 재사용 → 401)
- [ ] JWT 서명 검증 단위 테스트

---

### Step 4 — 설정 blob CRUD (서버사이드 암호화)

**목표:** `PUT/GET /api/v1/config` — 투명한 암호화/복호화

```
GET /api/v1/config
  Header: Authorization: Bearer {jwt}
  → JWT 검증 (FastAPI Depends)
  → config_blobs 조회 (user_id)
  → blob 없음 → 200 { success: true, data: {}, count: 0 }
  → decrypt_blob(blob) → JSON 파싱
  → 200 { success: true, data: {...설정...}, count: 1 }

PUT /api/v1/config
  Header: Authorization: Bearer {jwt}
  Body: { ...설정 JSON... }
  → JWT 검증
  → json.dumps(body) → encrypt_blob()
  → config_blobs UPSERT (user_id)
  → 200 { success: true }
```

**검증 포인트:**
- [ ] 빈 config → `{}` 반환 (오류 아님)
- [ ] 잘못된 JWT → 401
- [ ] 설정 업로드 후 조회 → 동일 JSON 반환
- [ ] CONFIG_ENCRYPTION_KEY 환경변수 없을 때 서버 시작 실패 (fast-fail)

---

### Step 5 — 비밀번호 재설정 API

```
POST /api/auth/forgot-password
  Body: { email }
  → 이메일 존재 여부 무관하게 200 반환 (이메일 열거 방지)
  → 이메일 존재 시: urlsafe_token → password_reset_tokens INSERT (10분 TTL)
  → SMTP: 재설정 메일 발송 (링크: https://stockvision.app/reset-password?token=...)

POST /api/auth/reset-password
  Body: { token, new_password }
  → token 조회 + 만료/사용 여부 확인
  → Argon2id(new_password) → users.password_hash UPDATE
  → password_reset_tokens.used = true
  → 해당 user의 모든 refresh_tokens 삭제 (세션 무효화)
  → 200 { success: true }
```

**검증 포인트:**
- [ ] 10분 후 토큰 만료 확인
- [ ] 재설정 후 기존 Refresh Token 전부 무효화
- [ ] 새 비밀번호로 로그인 가능 확인
- [ ] 이메일 열거 방지 (존재하지 않는 이메일도 200)

---

### Step 6 — 로컬 서버 연동

**목표:** `token.dat` 관리 + 자동 재시작 플로우

파일: `local_server/cloud/auth_client.py`

```python
TOKEN_DAT = Path(os.environ.get("APPDATA")) / "StockVision" / "token.dat"

class AuthClient:
    def load_refresh_token(self) -> str | None:
        if TOKEN_DAT.exists():
            return TOKEN_DAT.read_text().strip()
        return None

    def save_refresh_token(self, token: str):
        TOKEN_DAT.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_DAT.write_text(token)

    def refresh_jwt(self) -> str:
        """토큰 파일에서 Refresh Token 읽기 → 새 JWT + 새 RT 저장"""
        rt = self.load_refresh_token()
        if not rt:
            raise NeedsLoginError("token.dat 없음")
        resp = httpx.post(CLOUD_URL + "/api/auth/refresh", json={"refresh_token": rt})
        if resp.status_code == 401:
            TOKEN_DAT.unlink(missing_ok=True)
            raise NeedsLoginError("Refresh Token 만료")
        data = resp.json()
        self.save_refresh_token(data["refresh_token"])
        return data["jwt"]

    def get_config(self, jwt: str) -> dict:
        resp = httpx.get(CLOUD_URL + "/api/v1/config",
                         headers={"Authorization": f"Bearer {jwt}"})
        resp.raise_for_status()
        return resp.json()["data"]
```

**자동 시작 흐름:**
```
exe 시작
    ↓
AuthClient.refresh_jwt()
  → 성공: 새 JWT 획득 + token.dat 갱신
  → 실패 (NeedsLoginError): 트레이 알림 "재로그인 필요"
    ↓ (성공 시)
AuthClient.get_config(jwt)
    ↓
전략 엔진 시작 (사용자 개입 없음)
```

**React → 로컬 서버 JWT 전달 (token.dat 없을 때):**
```
POST /api/config/unlock  Body: { jwt }
  → 로컬 서버가 jwt로 GET /api/v1/config 호출
  → 설정 로드 → "잠금 해제" 완료
```

**검증 포인트:**
- [ ] 정상 token.dat → 자동 시작 (사용자 입력 없음)
- [ ] token.dat 없음 → 트레이 알림
- [ ] Refresh Token 만료 → token.dat 삭제 + 트레이 알림
- [ ] Refresh Token Rotation 동작 (매 갱신마다 새 token.dat)

---

### Step 7 — React 로그인 UI

파일 목록:
- `frontend/src/pages/Login.tsx` — 이메일 + 비밀번호 로그인 폼
- `frontend/src/pages/Register.tsx` — 회원가입 폼
- `frontend/src/pages/ForgotPassword.tsx` — 비밀번호 재설정 요청
- `frontend/src/pages/ResetPassword.tsx` — 새 비밀번호 입력
- `frontend/src/services/auth.ts` — Auth API 클라이언트

**인증 상태 관리:**
- React Context or Zustand: `{ jwt, user, isAuthenticated }`
- JWT 만료 전 자동 갱신: 24h TTL → 액세스 만료 5분 전 silent refresh
- 로컬 서버 연결 감지 → JWT 전달 (`POST /api/config/unlock`)

**검증 포인트:**
- [ ] 로그인 성공 → 대시보드 리다이렉트
- [ ] 이메일 미인증 → 인증 메일 재발송 안내
- [ ] 잘못된 자격증명 → 에러 메시지
- [ ] 로컬 서버 연결 감지 → 자동 JWT 전달

---

## 3. 파일 생성/수정 목록

### 신규 생성 (클라우드 백엔드)
| 파일 | 내용 |
|------|------|
| `backend/app/models/auth.py` | User, RefreshToken, EmailVerificationToken, PasswordResetToken, ConfigBlob 모델 |
| `backend/app/core/encryption.py` | AES-256-GCM encrypt_blob / decrypt_blob |
| `backend/app/core/password.py` | Argon2id hash_password / verify_password |
| `backend/app/api/auth.py` | register, verify-email, login, refresh, logout, forgot-password, reset-password |
| `backend/app/api/config.py` | GET/PUT /api/v1/config |
| `backend/app/core/jwt.py` | create_jwt / verify_jwt |
| `backend/app/core/email.py` | SMTP 발송 유틸 |

### 신규 생성 (로컬 서버)
| 파일 | 내용 |
|------|------|
| `local_server/cloud/auth_client.py` | refresh_jwt, get_config, save/load token.dat |

### 신규 생성 (프론트엔드)
| 파일 | 내용 |
|------|------|
| `frontend/src/pages/Login.tsx` | 로그인 페이지 |
| `frontend/src/pages/Register.tsx` | 회원가입 페이지 |
| `frontend/src/pages/ForgotPassword.tsx` | 비밀번호 재설정 요청 |
| `frontend/src/pages/ResetPassword.tsx` | 새 비밀번호 입력 |
| `frontend/src/services/auth.ts` | Auth API 클라이언트 |
| `frontend/src/context/AuthContext.tsx` | JWT / 사용자 상태 관리 |

### 수정 (기존)
| 파일 | 변경 |
|------|------|
| `backend/app/main.py` | auth, config 라우터 추가 |
| `backend/app/core/config.py` | CONFIG_ENCRYPTION_KEY, JWT_SECRET, SMTP_* 환경변수 추가 |
| `backend/requirements.txt` | argon2-cffi, cryptography, python-jose, httpx 추가 |
| `frontend/src/App.tsx` | Login, Register 등 라우트 추가 |

---

## 4. 환경변수

```env
# .env (backend)
CONFIG_ENCRYPTION_KEY=<64 hex chars, 32 bytes>  # openssl rand -hex 32
JWT_SECRET=<256bit random>                        # openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
REFRESH_TOKEN_EXPIRE_DAYS=30
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@stockvision.app
SMTP_PASSWORD=<app password>
CLOUD_URL=https://stockvision.app
```

**운영 환경:** CONFIG_ENCRYPTION_KEY는 AWS KMS 또는 환경변수로 주입 (하드코딩 절대 금지)

---

## 5. 의존 패키지

```
# 추가 필요 (requirements.txt)
argon2-cffi>=23.1.0        # Argon2id 비밀번호 해싱
cryptography>=42.0.0       # AES-256-GCM (AESGCM)
python-jose[cryptography]  # JWT 생성/검증
httpx>=0.27.0              # 로컬 서버 → 클라우드 HTTP
slowapi>=0.1.9             # Rate Limiting
```

---

## 6. 커밋 계획

| 커밋 | 메시지 | 파일 |
|------|--------|------|
| 1 | `docs: auth plan.md 작성` | `spec/auth/plan.md` |
| 2 | `feat: Step 1 — auth DB 스키마 + 암호화 유틸` | `models/auth.py`, `core/encryption.py`, `core/password.py` |
| 3 | `feat: Step 2 — 회원가입 + 이메일 인증 API` | `api/auth.py` (register, verify-email) |
| 4 | `feat: Step 3 — 로그인 + JWT + Refresh Token API` | `api/auth.py` (login, refresh, logout), `core/jwt.py` |
| 5 | `feat: Step 4 — config blob CRUD (서버사이드 암호화)` | `api/config.py` |
| 6 | `feat: Step 5 — 비밀번호 재설정 API` | `api/auth.py` (forgot/reset-password) |
| 7 | `feat: Step 6 — 로컬 서버 token.dat + auth_client` | `local_server/cloud/auth_client.py` |
| 8 | `feat: Step 7 — React 로그인 UI` | `frontend/src/pages/Login.tsx` 외 |

---

## 7. 검증 순서 (배포 전 체크리스트)

- [ ] `python -m pytest tests/test_auth.py -v` 전체 통과
- [ ] Postman으로 register → verify-email → login → refresh → logout 플로우 확인
- [ ] PC 재시작 후 자동 시작 (token.dat 기반) 확인
- [ ] PC2에서 로그인 후 PC1 설정 동일 복원 확인
- [ ] 비밀번호 재설정 후 기존 세션 무효화 확인
- [ ] Rate limit 동작 확인 (로그인 11회 → 429)
- [ ] CONFIG_ENCRYPTION_KEY 없이 서버 시작 → 즉시 오류 확인

---

**마지막 갱신**: 2026-03-04
**상태**: 초안 (구현 전 검토 필요)
