# 인증 기능 명세서 (auth)

> 작성일: 2026-03-04 | 상태: **현재 구현 대상 (Phase 3)** | 범위: 클라우드 Auth + 서버사이드 암호화

---

> **2026-03-04 최종 확정**
>
> | 항목 | 결정 | 근거 |
> |------|------|------|
> | 주 인증 | 이메일 + 비밀번호 (Argon2id) | OWASP 2023 권고 |
> | 설정 암호화 | 서버사이드 AES-256-GCM | 개인정보보호법 제29조 준수 (법적 최소 초과) |
> | 키 관리 | 서버 환경변수 (운영: AWS KMS) | 서버가 키 보유, 복구 가능 |
> | 클라이언트 수신 | 복호화된 JSON (평문) | 서버 API 레이어에서 투명하게 처리 |
> | 비밀번호 재설정 | 이메일 링크 → 새 비밀번호 | 표준 방식, 설정 데이터 영향 없음 |
> | Zero-Knowledge | ❌ 미적용 | 복구 불가 UX + 구현 복잡도 비용 > 이점 |

---

## 1. 개요

StockVision Phase 3의 인증 시스템. 클라우드에서 사용자 식별 및 JWT 발급, 설정 데이터를 서버사이드 AES-256-GCM으로 암호화 보관.

**설계 원칙:**
- 비밀번호는 단방향 해싱 (Argon2id) — 법적 의무
- 설정 데이터는 서버사이드 암호화 — 법적 의무 초과 조치
- 클라이언트는 평문 JSON 수신/송신 — 서버 API가 암호화/복호화 투명 처리
- 계좌번호는 사용자 로컬에만 — 서버 미보관

---

## 2. 법적 근거

### 2.1 개인정보보호법 (PIPA) 준수

| 조항 | 요건 | 우리 구현 |
|------|------|---------|
| 제29조 (안전조치의무) | 개인정보 안전성 확보 기술적 조치 | JWT 인증, HTTPS 강제, Argon2id |
| 안전성확보조치기준 §8 | 비밀번호 일방향 암호화 | Argon2id (OWASP 2023 #1) ✅ |
| 안전성확보조치기준 §9 | 접속기록 6개월 보관 | 서버 액세스 로그 보관 |
| 안전성확보조치기준 §10 | 민감정보 암호화 저장 | 설정 blob AES-256-GCM ✅ |

> 참고 법령:
> - [개인정보보호법](https://www.law.go.kr/법령/개인정보보호법) — 특히 제29조
> - [개인정보의 안전성 확보조치 기준](https://www.law.go.kr/행정규칙/개인정보의안전성확보조치기준) — 행안부고시

### 2.2 암호화 대상 분류

| 데이터 | PIPA 개인정보 여부 | 암호화 법적 의무 | 우리 처리 |
|--------|:----------------:|:--------------:|---------|
| 이메일 | ✅ 개인정보 | 전송 암호화 (TLS) | HTTPS 강제 ✅ |
| 비밀번호 | ✅ 개인정보 | 일방향 암호화 | Argon2id ✅ |
| 계좌번호 | ✅ 금융정보 | 암호화 | 서버 미보관 (로컬 only) ✅ |
| 트레이딩 전략 | ❌ 개인정보 아님 | 의무 없음 | AES-256-GCM (초과 조치) |
| 닉네임 | ✅ 개인정보 | 전송 암호화 | HTTPS ✅ |

> 참고:
> - [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
> - [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

---

## 3. 목표

### 3.1 기능 목표
- **계정 생성**: 이메일 + 비밀번호 + 닉네임(선택) + 이메일 인증
- **로그인**: JWT (24h) + Refresh Token (30d) 발급
- **설정 관리**: 서버사이드 AES-256-GCM 암호화/복호화 투명 처리
- **자동 재시작**: Refresh Token으로 부팅 시 무인 재인증
- **비밀번호 재설정**: 이메일 링크 → 새 비밀번호 설정 (설정 데이터 영향 없음)

### 3.2 비기능 목표
- **UX 마찰 최소화**: 부팅 후 로그인 없이 자동 시작
- **법적 준수**: 개인정보보호법 제29조, 안전성확보조치기준 준수
- **단순성**: 클라이언트 암호화 코드 없음, 서버 API만 수정

---

## 4. 사용자 시나리오

### 시나리오 1: 첫 설치 및 가입
```
1. exe 실행 → 로컬 서버 시작 → 브라우저 자동 열림
2. "계정 만들기" → 이메일 + 비밀번호 + 닉네임(선택)
3. 인증 이메일 클릭 → 이메일 확인 완료
4. 로그인 → JWT + Refresh Token 수신
5. token.dat에 Refresh Token 저장
6. GET /api/v1/config → 서버가 복호화 → 설정 JSON 수신 → 전략 엔진 시작
```

### 시나리오 2: 재부팅 후 자동 시작
```
1. Windows 시작 → exe 자동 실행
2. token.dat → Refresh Token 읽기
3. POST /api/v1/auth/refresh → 새 JWT 발급
4. GET /api/v1/config → 설정 수신
5. 전략 엔진 시작 ← 사용자 개입 없음
```

### 시나리오 3: Refresh Token 만료 (30일 후)
```
1. refresh 요청 실패 → 트레이 알림 "재로그인 필요"
2. 브라우저 → 이메일 + 비밀번호 로그인
3. 새 JWT + Refresh Token 발급 → 자동 재개
```

### 시나리오 4: PC2 이전
```
1. PC2에 exe 설치 → 이메일 + 비밀번호 로그인
2. GET /api/v1/config → 서버가 복호화 → 설정 JSON 수신
3. 전략/설정 완전 복원
4. local_secrets.json 계좌번호 수동 입력 (1회)
```

### 시나리오 5: 비밀번호 재설정
```
1. 로그인 페이지 → "비밀번호 분실"
2. 이메일 입력 → 재설정 링크 수신 (10분 TTL)
3. 새 비밀번호 입력 → 완료
4. 설정 데이터 영향 없음 (서버 키로 암호화, 비밀번호와 무관)
```

---

## 5. 인증 흐름

### 5.1 가입 흐름

```
[클라이언트]                              [서버]
    |                                        |
    | POST /api/v1/auth/register              |
    | { email, password, nickname? }          |
    |---------------------------------------->|
    |                                        | 1. 이메일 중복 확인
    |                                        | 2. Argon2id(password) 해싱
    |                                        | 3. users 테이블 저장 (email_verified=false)
    |                                        | 4. 인증 이메일 발송
    |<-- 200 { message: "이메일 확인 필요" } -|
    |                                        |
    | [사용자 이메일 클릭]                     |
    | GET /api/v1/auth/verify-email?token=xxx |
    |---------------------------------------->|
    |                                        | 5. 토큰 검증 → email_verified=true
    |<-- 302 redirect to /login -------------|
```

### 5.2 로그인 흐름

```
[클라이언트]                                     [서버]
    |                                              |
    | POST /api/v1/auth/login                      |
    | { email, password }                          |
    |--------------------------------------------->|
    |                                              | 1. Argon2id.verify(stored_hash, password)
    |                                              | 2. email_verified 확인
    |                                              | 3. JWT (24h) 발급
    |                                              | 4. Refresh Token (30d) 생성, SHA-256 저장
    |<-- 200 { jwt, refreshToken, user } ----------|
    |                                              |
    | token.dat에 Refresh Token 저장               |
    |                                              |
    | GET /api/v1/config (Authorization: Bearer)   |
    |--------------------------------------------->|
    |                                              | 5. config_blobs.blob AES-256-GCM 복호화
    |<-- 200 { strategies: [...], ui: {...} } -----|
    |                                              |
    | 전략 엔진 시작                               |
```

### 5.3 자동 재시작 흐름 (부팅 시)

```
exe 시작
    ↓
token.dat 읽기 (Refresh Token)
    ↓
POST /api/v1/auth/refresh { refreshToken }
    → 성공: 새 JWT (24h) + 새 Refresh Token (Rotation)
    → 실패: 트레이 알림 "재로그인 필요"
    ↓
GET /api/v1/config (새 JWT)
    → 서버가 AES-256-GCM 복호화 → JSON 응답
    ↓
전략 엔진 시작 ← 사용자 개입 없음
```

### 5.4 비밀번호 재설정 흐름

```
[클라이언트]                                   [서버]
    |                                             |
    | POST /api/v1/auth/forgot-password           |
    | { email }                                   |
    |-------------------------------------------->|
    |                                             | 1. 재설정 토큰 생성 (10분 TTL)
    |                                             | 2. 이메일 발송
    |<-- 200 (계정 존재 여부 동일 응답) -----------|
    |                                             |
    | POST /api/v1/auth/reset-password            |
    | { token, newPassword }                      |
    |-------------------------------------------->|
    |                                             | 3. 토큰 검증
    |                                             | 4. Argon2id(newPassword) 저장
    |                                             | 5. 새 JWT + Refresh Token 발급
    |<-- 200 { jwt, refreshToken } ---------------|
    |                                             |
    | (설정 데이터는 서버 키로 암호화 → 영향 없음) |
```

---

## 6. 서버사이드 암호화

### 6.1 설계

```
클라이언트 → PUT /api/v1/config → 평문 JSON 전송
                                      ↓
                               [서버 API 레이어]
                               AES-256-GCM.encrypt(json, SERVER_KEY)
                                      ↓
                               config_blobs 테이블에 저장

클라이언트 ← GET /api/v1/config ← 평문 JSON 수신
                                      ↑
                               [서버 API 레이어]
                               AES-256-GCM.decrypt(blob, SERVER_KEY)
                                      ↑
                               config_blobs 테이블에서 조회
```

### 6.2 키 관리

| 환경 | 키 저장소 | 비고 |
|------|---------|------|
| 개발 | `.env` 환경변수 | `CONFIG_ENCRYPTION_KEY=<hex 32바이트>` |
| 운영 | AWS KMS 또는 HashiCorp Vault | 키 자동 rotation 가능 |

```python
# backend/app/core/encryption.py
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_KEY = bytes.fromhex(os.environ["CONFIG_ENCRYPTION_KEY"])  # 32바이트

def encrypt(data: bytes) -> bytes:
    nonce = os.urandom(12)
    return nonce + AESGCM(_KEY).encrypt(nonce, data, None)

def decrypt(blob: bytes) -> bytes:
    return AESGCM(_KEY).decrypt(blob[:12], blob[12:], None)
```

### 6.3 Config API

```python
# backend/app/api/config.py

@router.get("/api/v1/config")
async def get_config(user=Depends(current_user), db=Depends(get_db)):
    record = db.query(ConfigBlob).filter_by(user_id=user.id).first()
    if not record or not record.blob:
        return {"success": True, "data": {}, "count": 0}
    plaintext = decrypt(record.blob)
    return {"success": True, "data": json.loads(plaintext), "count": 0}

@router.put("/api/v1/config")
async def put_config(body: dict, user=Depends(current_user), db=Depends(get_db)):
    blob = encrypt(json.dumps(body).encode())
    record = db.query(ConfigBlob).filter_by(user_id=user.id).first()
    if record:
        record.blob = blob
    else:
        db.add(ConfigBlob(user_id=user.id, blob=blob))
    db.commit()
    return {"success": True, "data": {}, "count": 0}
```

---

## 7. API 명세

### POST `/api/v1/auth/register`
```json
// Request
{ "email": "user@example.com", "password": "S3cur3P@ss!", "nickname": "철수" }

// 200
{ "success": true, "data": { "message": "인증 이메일이 발송되었습니다" }, "count": 0 }
// 400: 이메일 중복, 비밀번호 정책 위반
```

### GET `/api/v1/auth/verify-email?token=xxx`
```
302 redirect to /login  (성공)
401 { "error": "토큰이 만료되었습니다" }
```

### POST `/api/v1/auth/login`
```json
// Request
{ "email": "user@example.com", "password": "S3cur3P@ss!" }

// 200
{
  "success": true,
  "data": {
    "jwt": "eyJhbGc...",
    "refreshToken": "rt_abc123...",
    "jwtExpiresIn": 86400,
    "refreshExpiresIn": 2592000,
    "user": { "id": 1, "email": "user@example.com", "nickname": "철수" }
  },
  "count": 0
}
// 401: 이메일/비밀번호 불일치
// 403: 이메일 인증 미완료
```

### POST `/api/v1/auth/refresh`
```json
// Request
{ "refreshToken": "rt_abc123..." }

// 200 (Rotation: 새 토큰 발급, 기존 무효화)
{ "success": true, "data": { "jwt": "...", "refreshToken": "rt_new456...", "jwtExpiresIn": 86400 }, "count": 0 }
// 401: 만료 또는 무효
```

### POST `/api/v1/auth/logout`
```json
// Authorization: Bearer <jwt>
// Body: { "refreshToken": "rt_abc123..." }
// 200: Refresh Token 즉시 무효화
```

### POST `/api/v1/auth/forgot-password`
```json
{ "email": "user@example.com" }
// 200: (계정 존재 여부 동일 응답 — 열거 공격 방지)
```

### POST `/api/v1/auth/reset-password`
```json
{ "token": "reset_xyz...", "newPassword": "NewP@ss123!" }
// 200: { "jwt": "...", "refreshToken": "..." }
```

### GET `/api/v1/config`
```json
// Authorization: Bearer <jwt>
// 200: 복호화된 설정 JSON
{
  "success": true,
  "data": {
    "kiwoom": { "mode": "demo" },
    "strategies": [ ... ],
    "ui_preferences": { "theme": "dark" }
  },
  "count": 0
}
```

### PUT `/api/v1/config`
```json
// Authorization: Bearer <jwt>
// Body: 평문 설정 JSON (서버가 암호화 처리)
{ "kiwoom": { "mode": "demo" }, "strategies": [...] }
// 200: { "success": true }
```

---

## 8. 데이터 모델

```python
# backend/app/models/user.py

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    email_verified= Column(Boolean, default=False)
    password_hash = Column(String(255), nullable=False)  # Argon2id
    nickname      = Column(String(50), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash  = Column(String(255), unique=True, nullable=False)  # SHA-256(token)
    expires_at  = Column(DateTime, nullable=False)
    device_info = Column(String(255), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
    token      = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
    token      = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False)


class ConfigBlob(Base):
    """사용자 설정 (서버사이드 AES-256-GCM 암호화)"""
    __tablename__ = "config_blobs"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), unique=True)
    blob       = Column(LargeBinary, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## 9. 기술 요구사항

### 9.1 의존성

```
argon2-cffi==23.1.0      # Argon2id 비밀번호 해싱
python-jose==3.3.0       # JWT
email-validator==2.1.0   # 이메일 형식 검증
cryptography==42.0.0     # AES-256-GCM
```

### 9.2 Argon2id 파라미터 (OWASP 2023 권고)

```python
from argon2 import PasswordHasher

ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)
ph.hash(password)
ph.verify(stored_hash, password)
```

### 9.3 환경 변수

```bash
JWT_SECRET_KEY=<32자 이상 랜덤>
REFRESH_TOKEN_SECRET=<별도 32자 이상>
CONFIG_ENCRYPTION_KEY=<hex 인코딩 32바이트 AES 키>  # openssl rand -hex 32
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=noreply@stockvision.app
SMTP_PASSWORD=<app-password>
```

---

## 10. 보안 요구사항

| 항목 | 내용 |
|------|------|
| 비밀번호 정책 | 최소 8자, 대소문자+숫자 조합 |
| Rate Limiting | 로그인 실패: IP당 10회/시간, 가입: 5회/시간, 재설정: 3회/시간 |
| Refresh Token | SHA-256(token) 서버 저장, Rotation, 30d TTL |
| HTTPS | 모든 API 강제 (개발: localhost 제외) |
| CORS | stockvision.app, localhost:5173, localhost:8765만 허용 |

---

## 11. 미결 사항

- [ ] 닉네임 변경 빈도 제한 정책
- [ ] 멀티 디바이스 Refresh Token 목록 UI (기기별 로그아웃)
- [ ] 계정 삭제 시 config_blobs 즉시 삭제 vs 유예
- [ ] 투자 경험/리스크 선호도 온보딩 항목 확정
- [ ] CONFIG_ENCRYPTION_KEY 운영 환경 키 rotation 정책

---

**마지막 갱신**: 2026-03-04 (서버사이드 암호화 확정, Zero-Knowledge 제거)
**상태**: 확정 (Phase 3 구현 기준)
