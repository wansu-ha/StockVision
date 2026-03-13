"""
Rate Limiting (in-memory 구현)

프로덕션에서는 Redis로 교체 예정.
현재는 메모리 딕셔너리로 IP별 요청 횟수 추적.
"""
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request

from cloud_server.core.config import settings


class RateLimiter:
    """IP별 슬라이딩 윈도우 Rate Limiter"""

    def __init__(self, max_calls: int, period_seconds: int = 3600):
        self.max_calls = max_calls
        self.period = period_seconds
        self._store: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str) -> None:
        """허용 여부 확인. 초과 시 HTTPException(429) 발생"""
        now = time.time()
        with self._lock:
            calls = self._store[key]
            # 윈도우 외 항목 제거
            calls[:] = [t for t in calls if now - t < self.period]
            if len(calls) >= self.max_calls:
                raise HTTPException(
                    status_code=429,
                    detail=f"요청이 너무 많습니다. {self.period // 60}분 후 다시 시도하세요.",
                )
            calls.append(now)


def _get_ip(request: Request) -> str:
    """클라이언트 IP 추출 (X-Forwarded-For leftmost 우선).

    Render 프록시는 X-Forwarded-For에 클라이언트 IP를 추가하므로
    첫 번째(leftmost) IP가 실제 클라이언트. request.client.host는
    프록시 IP일 수 있어 폴백으로만 사용한다.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


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
