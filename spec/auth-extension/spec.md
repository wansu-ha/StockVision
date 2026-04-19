# 인증 확장 (Auth Extension)

> 작성일: 2026-03-12 | 상태: 보류 (2026-03-24 결정, v2 이후) | Phase C (C6-b)

## 1. 배경

현재 인증 시스템은 이메일/비밀번호 + JWT이며, 이메일 발송 인프라가 없어 email_verified를 DB에서 수동 처리하고 있다. 원격 제어(C6-c) 구현에 앞서 두 가지가 필요하다:

1. **OAuth2 소셜 로그인** — 이메일 인증 문제 해결 + 디바이스 등록 시 본인 확인 수단
2. **디바이스 등록/관리** — E2E 암호화 키 페어링, 기기별 세션 관리

## 2. 목표

소셜 로그인으로 가입/로그인을 간소화하고, 디바이스 등록 체계를 구축하여 원격 접속의 인증 기반을 마련한다.

## 3. 범위

### 3.1 포함

**A. OAuth2 소셜 로그인**

| 제공자 | 우선순위 | 비고 |
|--------|---------|------|
| Google | 1순위 | 범용, 해외 사용자 |
| Kakao | 2순위 | 한국 사용자 자연스러움 |

- 기존 이메일/비밀번호 로그인 유지 (추가 옵션)
- OAuth2 로그인 시 자동으로 email_verified = True
- 내부적으로는 동일 JWT 발급 (로그인 방식만 다름)
- 기존 이메일 계정과 OAuth2 계정 연동 (같은 이메일이면 같은 계정)

**B. 이메일 인증 정비**

- 이메일 발송 인프라 구축 (SendGrid 또는 AWS SES)
- 기존 수동 email_verified 처리 → 실제 인증 메일 발송으로 교체
- 비밀번호 재설정 메일도 동일 인프라 사용

**C. 디바이스 등록/관리**

- 디바이스 페어링: E2E 암호화 키 생성 + 배포
- 등록 방법:
  - (1) 로컬 PC에서 QR코드 + 복사 가능한 문자열로 키 표시 → 원격 디바이스에서 스캔/입력
  - (2) 원격에서 OAuth2 재로그인으로 본인 확인 → 키 발급 (집 밖에서도 등록 가능)
- 디바이스 목록 조회 (이름, 마지막 접속 시간, IP)
- 디바이스 개별 해제 (E2E 키 폐기 + 세션 종료)
- 디바이스 수 제한: 기본 5대

**D. 디바이스 관리 UI**

- Settings 페이지에 "연결된 디바이스" 섹션 추가
- 디바이스 목록: 이름, 등록일, 마지막 접속, 해제 버튼
- "새 디바이스 추가" → QR코드 표시 다이얼로그
- 기기 분실 시 "이 디바이스 해제" → 즉시 키 폐기 + 세션 kill

### 3.2 제외

- WS 연결/E2E 암호화 구현 → C6-a (릴레이 인프라)
- 원격 상태 조회/킬스위치/arm → C6-c (원격 제어)
- 2FA (TOTP, SMS OTP) — 초기에는 OAuth2 + 비밀번호 재입력으로 충분
- Apple Sign In — 사용자 규모 커지면 추가

## 4. 의존성

| 의존 대상 | 상태 | 비고 |
|-----------|------|------|
| 클라우드 인증 (`cloud_server/api/auth.py`) | 구현됨 | OAuth2 엔드포인트 추가 |
| 사용자 모델 (`cloud_server/models/user.py`) | 구현됨 | oauth_provider 필드 추가 |
| 릴레이 인프라 (C6-a) | 미구현 | 디바이스 키가 E2E에서 사용됨 |
| config.json | 구현됨 | 디바이스 키 저장소 |

## 5. 설계

### 5.1 OAuth2 흐름

```
프론트엔드
  → "Google로 로그인" 클릭
  → Google OAuth2 인증 페이지로 리다이렉트
  → 사용자 승인
  → 콜백 URL로 authorization code 전달
  → 클라우드 서버에 code 전송

클라우드 서버
  → Google에 code → access_token 교환
  → access_token으로 사용자 프로필 (email, name) 조회
  → DB에서 email로 기존 사용자 검색
    → 있으면: 로그인 (JWT 발급)
    → 없으면: 자동 가입 + email_verified=True + JWT 발급
  → OAuth provider 정보 저장 (google/kakao, provider_user_id)
```

### 5.2 API

**OAuth2 엔드포인트:**

```
GET  /api/v1/auth/oauth/{provider}/login     → OAuth 인증 URL 반환
POST /api/v1/auth/oauth/{provider}/callback   → code 교환 → JWT 발급
```

- `provider`: `google` | `kakao`
- 콜백 응답: 기존 로그인과 동일 형식 (`access_token`, `refresh_token`, `expires_in`)

**디바이스 관리 엔드포인트:**

```
GET    /api/v1/devices                → 등록된 디바이스 목록 (클라우드)
POST   /api/v1/devices/register       → 디바이스 메타데이터 등록 (클라우드, 키 제외)
DELETE /api/v1/devices/{device_id}    → 디바이스 해제 (클라우드 + 로컬에 키 폐기 명령)
```

**로컬 서버 페어링 엔드포인트** (같은 PC 프론트에서 호출):

```
POST   /api/devices/pair/init         → 키 생성 + QR 데이터 반환 (로컬)
POST   /api/devices/pair/complete     → 페어링 완료 확인 (로컬 → 클라우드에 등록 요청)
```

> 키 생성은 로컬 서버에서 수행. 클라우드는 디바이스 메타데이터(이름, 플랫폼, 등록일)만 저장하고 키는 절대 받지 않는다.

### 5.3 사용자 모델 확장

```python
# cloud_server/models/oauth_account.py (신규, 별도 테이블)
class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    id              = Column(Integer, primary_key=True)
    user_id         = Column(UUID, ForeignKey("users.id"), nullable=False)
    provider        = Column(String(20), nullable=False)   # 'google' | 'kakao'
    provider_user_id = Column(String(100), nullable=False)
    created_at      = Column(DateTime, default=now)
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id"),
    )
```

> 별도 테이블로 분리하여 한 사용자가 Google + Kakao를 동시에 연동 가능.

### 5.4 디바이스 모델

```python
# cloud_server/models/device.py (신규)
class Device(Base):
    __tablename__ = "devices"
    id           = Column(String(50), primary_key=True)  # uuid
    user_id      = Column(UUID, ForeignKey("users.id"), nullable=False)
    name         = Column(String(100))              # "iPhone 15", "Chrome - Windows"
    platform     = Column(String(20))               # 'web' | 'android' | 'ios'
    registered_at = Column(DateTime, default=now)
    last_seen_at  = Column(DateTime)
    last_ip       = Column(String(45))
    is_active     = Column(Boolean, default=True)
    # 암호화 키는 클라우드에 저장하지 않음 (E2E 원칙)
```

### 5.5 E2E 키 페어링 흐름

**방법 1: 로컬 PC에서 페어링 (권장)**

```
사용자가 로컬 프론트에서 "새 디바이스 추가" 클릭
  → 로컬 서버가 AES-256 키 생성 (32바이트)
  → 키를 QR코드 + 복사 문자열로 화면에 표시
  → 원격 디바이스에서 스캔/입력
  → 원격 디바이스가 IndexedDB에 키 저장
  → 완료 확인 → 클라우드에 디바이스 등록 (키 자체는 전송하지 않음)
```

**방법 2: 원격에서 페어링 (집 밖)**

```
원격 디바이스에서 "새 디바이스 등록" 클릭
  → OAuth2 재로그인 (본인 확인)
  → 클라우드가 로컬 서버에 WS로 키 생성 요청
  → 로컬 서버가 키 생성 → E2E로 원격 디바이스에 전달
    (이 시점에서는 아직 디바이스 키가 없으므로, 일회용 키 교환 필요)
  → Diffie-Hellman 키 교환 또는 임시 비밀번호 기반 키 유도
```

> 방법 2는 구현 복잡도가 높다. 초기에는 **방법 1만 지원**하고, 방법 2는 후속 이터레이션에서 추가.

### 5.6 키 분실/재페어링

- 원격 디바이스에서 키가 날아감 (브라우저 초기화 등)
- 로컬 PC에서 해당 디바이스 해제 → 새로 페어링
- 새 키 발급, 기존 키 자동 폐기
- 별도 복구 절차 없음

### 5.7 이메일 발송 인프라

```python
# cloud_server/services/email_service.py (신규)
class EmailService:
    def __init__(self, api_key: str):
        # SendGrid 또는 AWS SES 클라이언트

    def send_verification(self, to: str, token: str) -> None:
        # 인증 메일 발송

    def send_password_reset(self, to: str, token: str) -> None:
        # 비밀번호 재설정 메일 발송

    def send_device_alert(self, to: str, device_name: str) -> None:
        # "새 디바이스가 등록되었습니다" 알림
```

환경변수: `EMAIL_PROVIDER` (sendgrid/ses), `EMAIL_API_KEY`

## 6. 수용 기준

### OAuth2 소셜 로그인
- [ ] Google 로그인으로 가입/로그인이 가능하다
- [ ] Kakao 로그인으로 가입/로그인이 가능하다
- [ ] OAuth2 가입 시 email_verified가 자동 True이다
- [ ] 기존 이메일 계정과 같은 이메일의 OAuth2 계정이 자동 연동된다
- [ ] 기존 이메일/비밀번호 로그인이 정상 작동한다 (하위 호환)

### 이메일 인증
- [ ] 이메일/비밀번호 가입 시 인증 메일이 발송된다
- [ ] 인증 링크 클릭 시 email_verified가 True가 된다
- [ ] 비밀번호 재설정 메일이 발송된다

### 디바이스 등록/관리
- [ ] 로컬 PC에서 QR코드로 원격 디바이스를 페어링할 수 있다
- [ ] 페어링 시 AES-256 키가 생성되어 디바이스에 저장된다
- [ ] 클라우드 서버는 E2E 키를 저장하지 않는다
- [ ] 등록된 디바이스 목록을 조회할 수 있다 (이름, 마지막 접속)
- [ ] 디바이스를 해제하면 키가 폐기되고 세션이 종료된다
- [ ] 디바이스 수가 5대로 제한된다
- [ ] 새 디바이스 등록 시 이메일 알림이 발송된다

## 7. 참고

- 기존 인증: `cloud_server/api/auth.py`
- 사용자 모델: `cloud_server/models/user.py`
- 권한 모델: `docs/product/remote-permission-model.md`
- 릴레이 인프라: `spec/relay-infra/spec.md` (C6-a)
