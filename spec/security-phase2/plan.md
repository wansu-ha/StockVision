# 보안 2차 — 구현 계획

> 작성일: 2026-03-16 | 상태: 구현 완료 | spec: `spec/security-phase2/spec.md`

## 의존관계

```
S1 (Rate Limiter 신뢰)  ─── 독립
S2 (Redis Rate Limit)   ─── S1 완료 후 (같은 파일 수정)
S3 (Refresh Token)      ─── 독립
S4 (Soft-Delete)        ─── 독립
S5 (토큰 해싱)          ─── 독립
S6 (WS Origin)          ─── 독립
S7 (비밀번호 강도)       ─── 독립
S8 (리셋 URL)           ─── S5 완료 후 (같은 토큰 모델 수정)

→ S1→S2 순서. S3, S4, S5, S6, S7 병렬 가능. S8은 S5 후.
```

## Step 1: Rate Limiter X-Forwarded-For 신뢰 정책

**파일**: `cloud_server/core/rate_limit.py` (수정)

현재 `_get_ip()`가 leftmost IP를 추출하지만, rightmost-N 방식이 안전하다.
Render 프록시는 1홉이므로 기본값 `TRUSTED_PROXY_DEPTH=1`.

```python
import os

_PROXY_DEPTH = int(os.getenv("TRUSTED_PROXY_DEPTH", "1"))

def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",")]
        # rightmost-N: 프록시 홉 수만큼 뒤에서 건너뛴 IP가 실제 클라이언트
        idx = max(0, len(parts) - _PROXY_DEPTH)
        return parts[idx]
    return request.client.host if request.client else "unknown"
```

**검증**:
- [ ] `X-Forwarded-For: fake, real` → `DEPTH=1`일 때 `real` 반환
- [ ] 헤더 없을 때 `request.client.host` 반환
- [ ] `DEPTH=0`이면 leftmost (직접 노출 환경)

## Step 2: Redis Rate Limiter

**파일**: `cloud_server/core/rate_limit.py` (수정)

기존 `RateLimiter` 클래스를 Redis ZSET 백엔드로 교체하되, Redis 불가 시 인메모리 폴백 유지.

```python
class RateLimiter:
    def __init__(self, max_requests: int, period_seconds: int):
        self.max_requests = max_requests
        self.period = period_seconds
        self._memory: dict[str, list[float]] = defaultdict(list)  # 폴백

    async def check(self, request: Request) -> None:
        ip = _get_ip(request)
        redis = get_redis()
        if redis:
            await self._check_redis(redis, ip)
        else:
            self._check_memory(ip)

    async def _check_redis(self, redis, ip: str) -> None:
        key = f"rl:{self.max_requests}:{ip}"
        now = time.time()
        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - self.period)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, self.period)
        results = await pipe.execute()
        count = results[1]
        if count >= self.max_requests:
            raise HTTPException(status_code=429, ...)

    def _check_memory(self, ip: str) -> None:
        # 기존 로직 유지
```

**검증**:
- [ ] Redis 가용 시 ZSET에 기록 확인
- [ ] Redis 불가 시 인메모리 폴백 동작
- [ ] 기존 3개 리미터 인터페이스 유지

## Step 3: Refresh Token 보안 강화

**파일**: `frontend/src/context/AuthContext.tsx` (수정), `frontend/src/pages/Login.tsx` (수정)

### 3.1 AuthContext 저장 위치 변경

```typescript
// 기존
localStorage.setItem('sv_rt', refreshToken)
// 변경
const storage = keepLoggedIn ? localStorage : sessionStorage
storage.setItem('sv_rt', refreshToken)
```

### 3.2 초기화 시 마이그레이션

```typescript
// 기존 localStorage RT → sessionStorage로 이전
useEffect(() => {
  const oldRT = localStorage.getItem('sv_rt')
  if (oldRT && !sessionStorage.getItem('sv_rt')) {
    sessionStorage.setItem('sv_rt', oldRT)
    localStorage.removeItem('sv_rt')
  }
}, [])
```

### 3.3 Login 페이지 체크박스

```tsx
const [keepLoggedIn, setKeepLoggedIn] = useState(false)
// ... login 성공 시 keepLoggedIn 값을 AuthContext에 전달
```

**검증**:
- [ ] 기본 로그인 → 탭 종료 후 RT 소멸 확인
- [ ] "로그인 유지" 체크 → 브라우저 재시작 후 자동 로그인
- [ ] 기존 localStorage RT가 sessionStorage로 마이그레이션

## Step 4: Soft-Delete

**파일**: `cloud_server/models/user.py` (수정), `cloud_server/api/auth.py` (확인)

### 4.1 모델 변경

```python
# user.py
deleted_at = Column(DateTime, nullable=True, default=None)
```

### 4.2 DB 마이그레이션 (Alembic)

```bash
alembic revision --autogenerate -m "add users.deleted_at"
alembic upgrade head
```

생성된 마이그레이션:
```python
# alembic/versions/xxx_add_users_deleted_at.py
def upgrade():
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('users', 'deleted_at')
```

### 4.3 삭제 로직 확인

현재 삭제 API 자체가 없음. Admin에서 추후 추가 시 반드시 soft-delete 사용:
```python
user.is_active = False
user.deleted_at = datetime.utcnow()
db.commit()  # DELETE 금지
```

**검증**:
- [ ] `deleted_at` 컬럼 존재
- [ ] `is_active=False` 사용자 로그인 차단 (기존 동작 유지)
- [ ] Admin 사용자 목록에서 비활성 사용자 조회 가능

## Step 5: 이메일/리셋 토큰 해싱 (S5)

**파일**: `cloud_server/models/user.py` (수정), `cloud_server/api/auth.py` (수정)

### 5.1 토큰 모델에 해싱 적용

`RefreshToken`이 이미 사용하는 `hash_token()` 패턴을 `EmailVerificationToken`, `PasswordResetToken`에 동일 적용.

```python
# models/user.py
class EmailVerificationToken(Base):
    # 기존: token = Column(String, nullable=False)
    # 변경: token_hash = Column(String, nullable=False)  # hash_token(token)
    token_hash = Column(String, nullable=False, index=True)

class PasswordResetToken(Base):
    token_hash = Column(String, nullable=False, index=True)
```

### 5.2 생성/검증 로직 수정

```python
# api/auth.py — 토큰 생성
raw_token = secrets.token_urlsafe(32)
hashed = hash_token(raw_token)
db_token = EmailVerificationToken(user_id=user.id, token_hash=hashed, ...)
# raw_token만 사용자에게 전달 (이메일/응답)

# api/auth.py — 토큰 검증
hashed = hash_token(input_token)
db_token = db.query(EmailVerificationToken).filter_by(token_hash=hashed).first()
```

### 5.3 DB 마이그레이션

```bash
alembic revision --autogenerate -m "hash email_verification and password_reset tokens"
```

기존 평문 토큰 → 해시 마이그레이션 (데이터 마이그레이션 스크립트):
```python
# 기존 평문 token을 hash_token()으로 변환
for t in session.query(EmailVerificationToken).all():
    t.token_hash = hash_token(t.token)  # 임시: 기존 컬럼에서 읽어서 해시
```

**검증**:
- [ ] 이메일 인증 토큰이 DB에 해시값으로 저장
- [ ] 비밀번호 리셋 토큰이 DB에 해시값으로 저장
- [ ] 평문 토큰으로 검증 시 해시 비교 성공
- [ ] DB 직접 조회 시 원문 토큰 노출 불가

## Step 6: WebSocket Origin 검증 (S6)

**파일**: `local_server/routers/ws.py` (수정)

```python
from urllib.parse import urlparse

_ALLOWED_ORIGINS = {"localhost", "127.0.0.1"}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if origin:
        parsed = urlparse(origin)
        hostname = parsed.hostname or ""
        if hostname not in _ALLOWED_ORIGINS:
            await websocket.close(code=4003, reason="Origin not allowed")
            return
    # Origin 없는 요청은 허용 (로컬 앱, Electron 등)
    await websocket.accept()
    # ... 기존 로직
```

**검증**:
- [ ] `Origin: http://localhost:5173` → 접속 허용
- [ ] `Origin: http://127.0.0.1:5173` → 접속 허용
- [ ] `Origin: http://evil.com` → 접속 거부 (4003)
- [ ] Origin 헤더 없음 → 접속 허용

## Step 7: 비밀번호 강도 검증 (S7)

**파일**: `cloud_server/api/auth.py` (수정), `frontend/src/pages/Register.tsx` (수정)

### 7.1 서버 측 Pydantic 검증

```python
# api/auth.py — RegisterBody 또는 공통 스키마
import re

@field_validator("password")
@classmethod
def validate_password_strength(cls, v: str) -> str:
    if len(v) < 8:
        raise ValueError("비밀번호는 최소 8자 이상이어야 합니다.")
    if not re.search(r"[A-Za-z]", v):
        raise ValueError("비밀번호에 영문자가 포함되어야 합니다.")
    if not re.search(r"[0-9]", v):
        raise ValueError("비밀번호에 숫자가 포함되어야 합니다.")
    return v
```

### 7.2 프론트엔드 표시

```tsx
// Register.tsx — 비밀번호 입력 하단에 강도 표시
const passwordErrors = useMemo(() => {
  const errs: string[] = []
  if (password.length > 0 && password.length < 8) errs.push('8자 이상')
  if (password.length > 0 && !/[A-Za-z]/.test(password)) errs.push('영문 포함')
  if (password.length > 0 && !/[0-9]/.test(password)) errs.push('숫자 포함')
  return errs
}, [password])
```

**검증**:
- [ ] `""` → 서버 422 거부
- [ ] `"1234567"` → 8자 미만 거부
- [ ] `"abcdefgh"` → 숫자 미포함 거부
- [ ] `"12345678"` → 영문 미포함 거부
- [ ] `"abcd1234"` → 통과
- [ ] 프론트에서 실시간 강도 피드백 표시

## Step 8: 비밀번호 리셋 토큰 URL 노출 방지 (S8)

**파일**: `cloud_server/api/auth.py` (수정), `frontend/src/pages/ResetPassword.tsx` (수정)

### 8.1 URL fragment 방식

리셋 이메일의 링크를 쿼리스트링에서 fragment로 변경:
```python
# 기존: f"{frontend_url}/reset-password?token={token}"
# 변경:
reset_url = f"{frontend_url}/reset-password#token={token}"
```

### 8.2 프론트엔드 fragment 추출

```tsx
// ResetPassword.tsx
useEffect(() => {
  const hash = window.location.hash  // "#token=xxx"
  const params = new URLSearchParams(hash.slice(1))
  const token = params.get('token')
  if (token) {
    setResetToken(token)
    // fragment 제거 (히스토리에 남지 않도록)
    window.history.replaceState(null, '', window.location.pathname)
  }
}, [])
```

### 8.3 토큰을 POST body로 전송

```tsx
// 기존: GET /reset-password?token=xxx 로 토큰 노출
// 변경: fragment에서 추출 후 POST body로만 전송
const handleReset = async () => {
  await cloudAuth.resetPassword({ token: resetToken, new_password: newPassword })
}
```

**검증**:
- [ ] 리셋 URL에 `?token=` 쿼리스트링 없음
- [ ] fragment (`#token=`) 방식으로 토큰 전달
- [ ] 페이지 로드 후 fragment가 URL에서 제거됨
- [ ] 서버 로그에 토큰 미기록
- [ ] Referer 헤더에 토큰 미포함

## 변경 파일 요약

| 파일 | Step | 변경 |
|------|------|------|
| `cloud_server/core/rate_limit.py` | S1, S2 | IP 추출 + Redis 백엔드 |
| `cloud_server/models/user.py` | S4, S5 | `deleted_at` 필드 + 토큰 해싱 |
| `cloud_server/api/auth.py` | S5, S7, S8 | 토큰 해싱 로직 + 비밀번호 검증 + 리셋 URL |
| `frontend/src/context/AuthContext.tsx` | S3 | RT 저장 위치 |
| `frontend/src/pages/Login.tsx` | S3 | "로그인 유지" 체크박스 |
| `local_server/routers/ws.py` | S6 | Origin 검증 |
| `frontend/src/pages/Register.tsx` | S7 | 비밀번호 강도 표시 |
| `frontend/src/pages/ResetPassword.tsx` | S8 | fragment 토큰 추출 |
