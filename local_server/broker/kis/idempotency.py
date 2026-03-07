"""local_server.broker.kis.idempotency: 주문 멱등성 보장 모듈

동일한 client_order_id로 중복 주문을 방지한다.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sv_core.broker.models import OrderResult

logger = logging.getLogger(__name__)

# 완료된 주문 기록 보존 기간 (기본 24시간)
DEFAULT_TTL_HOURS = 24


class DuplicateOrderError(Exception):
    """중복 주문 시도 시 발생하는 예외"""

    def __init__(self, client_order_id: str, existing: OrderResult) -> None:
        self.client_order_id = client_order_id
        self.existing = existing
        super().__init__(
            f"중복 주문 감지: client_order_id={client_order_id} "
            f"(기존 order_id={existing.order_id})"
        )


class IdempotencyGuard:
    """주문 멱등성 보장 가드.

    client_order_id를 키로 주문 결과를 캐싱하여
    동일 ID로 재요청 시 기존 결과를 반환하거나 예외를 발생시킨다.
    """

    def __init__(self, ttl_hours: int = DEFAULT_TTL_HOURS) -> None:
        """초기화.

        Args:
            ttl_hours: 주문 기록 보존 시간 (시간)
        """
        self._ttl = timedelta(hours=ttl_hours)
        # {client_order_id: (OrderResult, 등록 시각)}
        self._records: dict[str, tuple[OrderResult, datetime]] = {}
        self._lock = asyncio.Lock()

    async def check(self, client_order_id: str) -> Optional[OrderResult]:
        """멱등성 체크를 수행한다.

        이미 처리된 client_order_id가 있으면 기존 결과를 반환한다.
        없으면 None을 반환한다.

        Args:
            client_order_id: 클라이언트 주문 ID

        Returns:
            Optional[OrderResult]: 기존 결과 (없으면 None)
        """
        async with self._lock:
            self._cleanup_expired()
            if client_order_id in self._records:
                result, _ = self._records[client_order_id]
                logger.warning(
                    "중복 주문 감지: client_order_id=%s → 기존 결과 반환 (order_id=%s)",
                    client_order_id, result.order_id,
                )
                return result
        return None

    async def register(self, result: OrderResult) -> None:
        """주문 결과를 등록한다. (place_order 성공 직후 호출)

        Args:
            result: 등록할 주문 결과
        """
        async with self._lock:
            self._records[result.client_order_id] = (result, datetime.now())
            logger.debug("멱등성 기록 등록: client_order_id=%s", result.client_order_id)

    def _cleanup_expired(self) -> None:
        """만료된 기록을 제거한다. (lock 보유 상태에서만 호출)"""
        now = datetime.now()
        expired = [
            key for key, (_, ts) in self._records.items()
            if now - ts > self._ttl
        ]
        for key in expired:
            del self._records[key]
        if expired:
            logger.debug("만료된 멱등성 기록 제거: %d건", len(expired))

    @property
    def record_count(self) -> int:
        """현재 보관 중인 기록 수를 반환한다."""
        return len(self._records)
