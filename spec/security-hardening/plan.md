# 보안 즉시 수정 구현 계획

> 작성일: 2026-03-08 | 상태: 초안
> 기반: `docs/research/security-audit-report.md`

## 범위

즉시 수정 대상 3건 (개발 중이라도 지금 고쳐야 하는 것):
1. **C1+C2**: local_server shared secret 인증
2. **H1**: token.dat → Keyring 통일
3. **H5**: 비밀번호 최소 8자 검증

---

## 위협 모델

| 위협 | 공격자 | shared secret 방어 | 비고 |
|------|--------|-------------------|------|
| **브라우저 CSRF** | 악성 웹페이지 | **방어됨** | form POST는 커스텀 헤더 불가. CORS가 응답 읽기 차단 |
| **로컬 악성 프로세스** | 같은 사용자 세션의 프로세스 | **방어 안 됨** | 파일·HTTP 응답 모두 읽기 가능. OS 세션 격리 필요 |

이 계획의 shared secret은 **C1+C2 (브라우저 CSRF)** 의 근본 해결책이다.
로컬 악성 프로세스 방어는 OS 수준 격리(별도 Windows 사용자 계정)가 필요하며 이 계획의 범위 밖이다.

---

## Step 1: local_server shared secret 인증 (C1+C2)

> 보안 감사 C1 (Critical) + C2 (Critical) 해결

### 1.1 배경

local_server의 모든 mutation API에 인증이 없다.
CORS는 브라우저 응답 차단일 뿐 요청 자체를 막지 않으며, 로컬 프로세스는 CORS를 완전히 무시한다.
Jupyter, code-server 등 localhost 서버의 표준 보호 패턴: **프로세스 시작 시 생성한 1회성 비밀을 파일로 공유**.

### 1.2 설계

```
[시작 시]
  main.py → secrets.token_hex(32) 생성
          → app.state.local_secret에 메모리 보관
          (파일 저장은 현재 구현에서 불필요 — 프론트엔드가 /api/auth/token 응답으로 수신.
           향후 desktop/native bridge 연동 시 파일 경로로 전달하는 용도로 예약)

[모든 mutation 요청]
  X-Local-Secret 헤더 필수
  → require_local_secret Depends가 app.state.local_secret과 hmac.compare_digest 비교
  → 불일치 시 403

[프론트엔드]
  POST /api/auth/token 응답에 local_secret을 포함한다.

  보안 분석:
  - 브라우저 CSRF: 악성 웹페이지가 이 엔드포인트를 호출해도
    CORS가 응답 읽기를 차단 → secret 탈취 불가.
  - 로컬 악성 프로세스: 응답·파일 모두 읽을 수 있어 secret 탈취 가능.
    → 이는 이 계획의 범위 밖 (§ 위협 모델 참조).
  - POST /api/auth/token은 전달받은 JWT를 검증하지 않으므로
    임의 호출로 credential 오염이 가능하다.
    → 범위 밖이지만, 향후 cloud JWT 검증 추가를 권장한다.

  이후 모든 요청에 X-Local-Secret 헤더 첨부.
```

### 1.3 변경 파일

| 파일 | 변경 |
|------|------|
| `local_server/core/local_auth.py` | **신규**. `generate_secret()`, `require_local_secret()` Depends |
| `local_server/main.py` | lifespan에서 `generate_secret()` 호출 → `app.state.local_secret` 저장 |
| `local_server/routers/auth.py` | `POST /token` 응답에 `local_secret` 포함. `POST /logout`에 `require_local_secret` 적용 |
| `local_server/routers/config.py` | mutation + `GET` 모두 `require_local_secret` 적용 |
| `local_server/routers/trading.py` | 모든 엔드포인트에 `require_local_secret` 적용 |
| `local_server/routers/rules.py` | mutation + `GET` 모두 `require_local_secret` 적용 |
| `local_server/routers/logs.py` | `GET /api/logs`에 `require_local_secret` 적용 |
| `local_server/routers/ws.py` | WebSocket handshake 시 `sec` query param으로 secret 검증 |
| `frontend/src/services/localClient.ts` | `setAuthToken` 응답에서 `local_secret` 저장 → 모든 요청 헤더에 첨부 |

### 1.4 `local_server/core/local_auth.py` 구조

```python
"""로컬 서버 프로세스 인증.

시작 시 1회성 비밀을 생성하여 mutation API를 보호한다.
"""
import hmac
import secrets

from fastapi import Header, HTTPException, Request


def generate_secret() -> str:
    """32바이트 hex 비밀 생성 → 반환. 메모리(app.state)에만 보관."""
    return secrets.token_hex(32)


async def require_local_secret(
    request: Request,
    x_local_secret: str = Header(None),
) -> None:
    """모든 mutation 엔드포인트의 Depends.

    X-Local-Secret 헤더가 시작 시 생성된 비밀과 일치하는지 검증.
    """
    expected = request.app.state.local_secret
    if not x_local_secret or not hmac.compare_digest(x_local_secret, expected):
        raise HTTPException(status_code=403, detail="Invalid local secret")
```

### 1.5 엔드포인트 보호 분류

#### Mutation — require_local_secret 적용

모든 POST/PATCH/DELETE (아래 면제 제외).

#### Mutation 면제

| 엔드포인트 | 이유 |
|-----------|------|
| `POST /api/auth/token` | secret 발급 엔드포인트. CORS가 응답 읽기 차단 |

#### GET — 보호 대상 (require_local_secret 적용)

| 엔드포인트 | 민감 이유 |
|-----------|----------|
| `GET /api/config` | cloud.url·서버 설정 노출 → SSRF 체인 가능 (M1) |
| `GET /api/logs` | 주문·체결·전략 활동 기록 |
| `GET /api/rules` | 매매 규칙 (전략 로직) |

#### GET — 공개 (secret 불필요)

| 엔드포인트 | 이유 |
|-----------|------|
| `GET /health` | 헬스체크 (`status`, `version`만 노출) |
| `GET /api/status` | 서버 상태 (`broker.has_credentials`, `broker.connected`, `strategy_engine.running` 노출 — 값 자체는 비민감) |
| `GET /api/auth/status` | 인증 여부 (`has_cloud_token: bool`). token_preview 제거 (M2 동시 해결) |

#### WebSocket

| 엔드포인트 | 보호 |
|-----------|------|
| `WS /ws` | handshake 시 `sec` query param으로 secret 검증 |

### 1.6 프론트엔드 흐름

```
1. 유저 로그인 → cloud에서 JWT + RT 수신
2. localClient.setAuthToken(jwt, rt) → POST /api/auth/token
3. 응답: { success, data: { message, local_secret } }
4. localClient가 local_secret을 메모리(모듈 변수)에 저장
5. 이후 모든 localClient 요청에 X-Local-Secret 헤더 자동 첨부
6. 페이지 새로고침 시 → sessionStorage에서 jwt 복원 → setAuthToken 재호출 → secret 재발급
```

### 1.7 검증

- [ ] `POST /api/trading/order` — X-Local-Secret 없이 호출 → 403
- [ ] `POST /api/trading/order` — 잘못된 secret → 403
- [ ] `POST /api/trading/order` — 올바른 secret → 정상 처리
- [ ] `POST /api/auth/logout` — secret 없이 → 403
- [ ] `GET /api/config` — secret 없이 → 403
- [ ] `GET /api/logs` — secret 없이 → 403
- [ ] `GET /api/rules` — secret 없이 → 403
- [ ] `GET /health` — secret 없이 → 200 (면제)
- [ ] `GET /api/auth/status` — secret 없이 → 200 (면제)
- [ ] `POST /api/auth/token` — secret 없이 → 200 (면제, secret 발급)
- [ ] WebSocket — secret 없이 연결 시도 → 거부
- [ ] 서버 재시작 → 새 secret 생성 → 이전 secret 무효화

---

## Step 2: token.dat → Keyring 통일 (H1)

> 보안 감사 H1 (High) 해결

### 2.1 배경

`local_server/cloud/auth_client.py`가 refresh token을 `%APPDATA%\StockVision\token.dat`에 평문 파일로 저장한다.
동일 서버의 `local_server/storage/credential.py`에 이미 `KEY_CLOUD_REFRESH_TOKEN`과
`save_cloud_tokens()` / `load_cloud_tokens()`가 존재하며 Windows Keyring(DPAPI)을 사용한다.

### 2.2 변경

| 파일 | 변경 |
|------|------|
| `local_server/cloud/auth_client.py` | `_TOKEN_DAT` 관련 코드 제거. `credential.py` import로 대체 |

### 2.3 수정 후 `auth_client.py`

```python
from local_server.storage.credential import (
    load_credential, save_credential, delete_credential,
    KEY_CLOUD_REFRESH_TOKEN,
)

class AuthClient:
    def load_refresh_token(self) -> str | None:
        return load_credential(KEY_CLOUD_REFRESH_TOKEN)

    def save_refresh_token(self, token: str) -> None:
        save_credential(KEY_CLOUD_REFRESH_TOKEN, token)

    def delete_refresh_token(self) -> None:
        delete_credential(KEY_CLOUD_REFRESH_TOKEN)

    # refresh_jwt, get_config, save_token_from_login — 변경 없음 (내부에서 위 메서드 호출)
```

### 2.4 마이그레이션

기존 `token.dat`가 있으면 Keyring으로 이전 후 파일 삭제:

```python
# lifespan에서 1회 실행
def migrate_token_dat():
    if _TOKEN_DAT.exists():
        token = _TOKEN_DAT.read_text(encoding="utf-8").strip()
        if token:
            save_credential(KEY_CLOUD_REFRESH_TOKEN, token)
        _TOKEN_DAT.unlink()
        logger.info("token.dat → Keyring 마이그레이션 완료")
```

### 2.5 검증

- [ ] 기존 `token.dat` 존재 시 → Keyring 이전 후 파일 삭제 확인
- [ ] `token.dat` 없는 신규 설치 → Keyring에 직접 저장 확인
- [ ] `refresh_jwt()` 호출 → Keyring에서 RT 로드 → 갱신 → Keyring에 새 RT 저장

---

## Step 3: 비밀번호 최소 길이 검증 (H5)

> 보안 감사 H5 (High) 해결

### 3.1 배경

`cloud_server/api/auth.py`의 `RegisterBody`와 `ResetPasswordBody`에 password 검증이 없다.
빈 문자열도 Argon2id로 해싱되어 저장된다.

### 3.2 변경

| 파일 | 변경 |
|------|------|
| `cloud_server/api/auth.py` | `RegisterBody.password`와 `ResetPasswordBody.new_password`에 `field_validator` 추가 |

### 3.3 코드

```python
from pydantic import BaseModel, EmailStr, field_validator

MIN_PASSWORD_LENGTH = 8

class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    nickname: str | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다.")
        return v


class ResetPasswordBody(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다.")
        return v
```

### 3.4 검증

- [ ] `POST /auth/register` password="" → 422 에러
- [ ] `POST /auth/register` password="1234567" (7자) → 422 에러
- [ ] `POST /auth/register` password="12345678" (8자) → 정상 처리
- [ ] `POST /auth/reset-password` new_password="" → 422 에러
- [ ] `POST /auth/reset-password` new_password="validpass" → 정상 처리

---

## 의존관계

```
Step 1 (local_server shared secret)  ─── 독립
Step 2 (token.dat → Keyring)         ─── 독립
Step 3 (비밀번호 검증)                ─── 독립

→ 3개 모두 독립. 병렬 작업 가능.
```

---

## 변경 파일 요약

### 신규 (1)
- `local_server/core/local_auth.py`

### 수정 (8)
- `local_server/main.py` — secret 생성 + token.dat 마이그레이션
- `local_server/cloud/auth_client.py` — token.dat → Keyring
- `local_server/routers/auth.py` — secret 응답 + require_local_secret
- `local_server/routers/config.py` — require_local_secret
- `local_server/routers/trading.py` — require_local_secret
- `local_server/routers/rules.py` — require_local_secret
- `local_server/routers/logs.py` — require_local_secret
- `cloud_server/api/auth.py` — password validator

### 프론트엔드 수정 (1)
- `frontend/src/services/localClient.ts` — secret 저장 + 헤더 첨부

### 보조 수정 (2, Step 1에 포함)
- `local_server/routers/ws.py` — WebSocket secret 검증
- `local_server/routers/auth.py` — token_preview 제거 (M2 동시 해결)

---

## 비범위 (출시 전 별도 작업)

이하 항목은 이 plan 범위 밖이며 `docs/research/security-audit-report.md`에서 추적한다:

- C3: 이메일/리셋 토큰 해싱 (DB 마이그레이션 필요)
- C4: refresh token httpOnly cookie (백엔드+프론트 동시 대공사)
- H2: rules injection 차단
- H3: WebSocket Origin 검증 (Step 1에서 secret 검증으로 부분 해결)
- H4: rate limiter XFF 검증
- H6: reset token URL 노출
- H7: refresh/logout rate limit
- M1~M6: 프로덕션 하드닝
