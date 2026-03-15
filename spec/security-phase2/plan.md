# 보안 2차 — 구현 계획

> 작성일: 2026-03-16 | 상태: 초안 | spec: `spec/security-phase2/spec.md`

## 의존관계

```
S1 (Rate Limiter 신뢰)  ─── 독립
S2 (Redis Rate Limit)   ─── S1 완료 후 (같은 파일 수정)
S3 (Refresh Token)      ─── 독립
S4 (Soft-Delete)        ─── 독립

→ S1→S2 순서. S3, S4는 병렬 가능.
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

### 4.2 DB 마이그레이션

```sql
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP NULL DEFAULT NULL;
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

## 변경 파일 요약

| 파일 | Step | 변경 |
|------|------|------|
| `cloud_server/core/rate_limit.py` | S1, S2 | IP 추출 + Redis 백엔드 |
| `cloud_server/models/user.py` | S4 | `deleted_at` 필드 |
| `frontend/src/context/AuthContext.tsx` | S3 | RT 저장 위치 |
| `frontend/src/pages/Login.tsx` | S3 | "로그인 유지" 체크박스 |
