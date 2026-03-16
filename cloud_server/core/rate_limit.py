"""
Rate Limiting — 인메모리 + Redis 백엔드

S1: X-Forwarded-For rightmost-N 방식으로 실제 클라이언트 IP 추출
S2: Redis ZSET 슬라이딩 윈도우 (Redis 불가 시 인메모리 폴백)
"""
import os
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request

from cloud_server.core.config import settings

# S1: 프록시 홉 수 — Render는 1홉
_PROXY_DEPTH = int(os.getenv("TRUSTED_PROXY_DEPTH", "1"))


def _get_ip(request: Request) -> str:
    """클라이언트 IP 추출 (S1: rightmost-N 방식).

    X-Forwarded-For에서 프록시 홉 수만큼 뒤에서 건너뛴 IP가 실제 클라이언트.
    DEPTH=1 (Render): rightmost에서 1칸 앞 = 실제 클라이언트.
    DEPTH=0: leftmost (직접 노출 환경).
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",")]
        idx = max(0, len(parts) - _PROXY_DEPTH - 1)
        return parts[idx]
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """IP별 슬라이딩 윈도우 Rate Limiter (S2: Redis + 인메모리 폴백)"""

    def __init__(self, max_calls: int, period_seconds: int = 3600):
        self.max_calls = max_calls
        self.period = period_seconds
        self._store: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str) -> None:
        """허용 여부 확인. 초과 시 HTTPException(429) 발생"""
        from cloud_server.core.redis import get_redis
        redis = get_redis()
        if redis:
            self._check_redis(redis, key)
        else:
            self._check_memory(key)

    def _check_redis(self, redis: object, key: str) -> None:
        """Redis ZSET 슬라이딩 윈도우"""
        zkey = f"rl:{self.max_calls}:{self.period}:{key}"
        now = time.time()
        pipe = redis.pipeline()  # type: ignore[union-attr]
        pipe.zremrangebyscore(zkey, 0, now - self.period)
        pipe.zcard(zkey)
        pipe.zadd(zkey, {str(now): now})
        pipe.expire(zkey, self.period)
        results = pipe.execute()
        count = results[1]
        if count >= self.max_calls:
            raise HTTPException(
                status_code=429,
                detail=f"요청이 너무 많습니다. {self.period // 60}분 후 다시 시도하세요.",
            )

    def _check_memory(self, key: str) -> None:
        """인메모리 폴백"""
        now = time.time()
        with self._lock:
            calls = self._store[key]
            calls[:] = [t for t in calls if now - t < self.period]
            if len(calls) >= self.max_calls:
                raise HTTPException(
                    status_code=429,
                    detail=f"요청이 너무 많습니다. {self.period // 60}분 후 다시 시도하세요.",
                )
            calls.append(now)


# 엔드포인트별 리미터 인스턴스
login_limiter = RateLimiter(settings.RATE_LIMIT_LOGIN, 3600)
register_limiter = RateLimiter(settings.RATE_LIMIT_REGISTER, 3600)
forgot_pw_limiter = RateLimiter(settings.RATE_LIMIT_FORGOT_PW, 3600)


def check_login_rate(request: Request) -> None:
    login_limiter.check(_get_ip(request))


def check_register_rate(request: Request) -> None:
    register_limiter.check(_get_ip(request))


def check_forgot_pw_rate(request: Request) -> None:
    forgot_pw_limiter.check(_get_ip(request))
