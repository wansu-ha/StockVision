"""local_server.broker.kis.rate_limiter: API 호출 속도 제한 모듈

KIS Open API+ 제한:
- 초당 20회 (REST)
- 일 100,000회
"""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)

# KIS API 기본 제한
DEFAULT_CALLS_PER_SECOND = 20
DEFAULT_CALLS_PER_DAY = 100_000


class RateLimiter:
    """토큰 버킷 알고리즘 기반 API 속도 제한기.

    asyncio.Semaphore를 슬라이딩 윈도우로 사용.
    초당 호출 수를 초과하면 acquire() 호출이 대기한다.

    사용 예:
        limiter = RateLimiter(calls_per_second=20)
        await limiter.acquire()
        response = await client.get(url)
    """

    def __init__(
        self,
        calls_per_second: int = DEFAULT_CALLS_PER_SECOND,
        endpoint: str = "default",
    ) -> None:
        """초기화.

        Args:
            calls_per_second: 초당 최대 호출 수
            endpoint: 로그용 엔드포인트 식별자
        """
        self._calls_per_second = calls_per_second
        self._endpoint = endpoint
        self._semaphore = asyncio.Semaphore(calls_per_second)
        self._call_times: list[float] = []  # 최근 호출 시각 슬라이딩 윈도우
        self._lock = asyncio.Lock()
        self._total_calls = 0

    async def acquire(self) -> None:
        """토큰을 획득한다. 제한 초과 시 대기한다.

        슬라이딩 윈도우(1초) 방식으로 구현:
        1. 1초 이상 지난 호출 기록 제거
        2. 현재 1초 내 호출 수가 한도에 도달하면 대기
        3. 호출 기록 추가
        """
        while True:
            async with self._lock:
                now = time.monotonic()
                # 1초 지난 기록 제거
                self._call_times = [t for t in self._call_times if now - t < 1.0]

                if len(self._call_times) < self._calls_per_second:
                    self._call_times.append(now)
                    self._total_calls += 1
                    if self._total_calls % 100 == 0:
                        logger.debug(
                            "RateLimiter[%s] 누적 호출: %d",
                            self._endpoint, self._total_calls,
                        )
                    return

            # 한도 초과 → 가장 오래된 호출이 1초 지날 때까지 대기
            oldest = self._call_times[0] if self._call_times else 0.0
            wait_time = max(0.0, 1.0 - (time.monotonic() - oldest))
            logger.debug(
                "RateLimiter[%s] 대기 %.3fs (현재 %d/%d)",
                self._endpoint, wait_time,
                len(self._call_times), self._calls_per_second,
            )
            await asyncio.sleep(wait_time)

    @property
    def total_calls(self) -> int:
        """누적 호출 횟수를 반환한다."""
        return self._total_calls

    def reset_stats(self) -> None:
        """통계를 초기화한다. (테스트 용도)"""
        self._total_calls = 0


class MultiEndpointRateLimiter:
    """엔드포인트별 개별 속도 제한기.

    일부 엔드포인트는 더 낮은 한도를 가질 수 있다.

    사용 예:
        limiter = MultiEndpointRateLimiter()
        await limiter.acquire("order")  # 주문 엔드포인트
        await limiter.acquire("quote")  # 시세 엔드포인트
    """

    def __init__(self, default_cps: int = DEFAULT_CALLS_PER_SECOND) -> None:
        """초기화.

        Args:
            default_cps: 기본 초당 호출 수
        """
        self._default_cps = default_cps
        self._limiters: dict[str, RateLimiter] = {}

    def set_limit(self, endpoint: str, calls_per_second: int) -> None:
        """특정 엔드포인트의 제한을 설정한다.

        Args:
            endpoint: 엔드포인트 식별자
            calls_per_second: 초당 최대 호출 수
        """
        self._limiters[endpoint] = RateLimiter(calls_per_second, endpoint)

    async def acquire(self, endpoint: str = "default") -> None:
        """엔드포인트별 토큰을 획득한다.

        Args:
            endpoint: 엔드포인트 식별자
        """
        if endpoint not in self._limiters:
            self._limiters[endpoint] = RateLimiter(self._default_cps, endpoint)
        await self._limiters[endpoint].acquire()
