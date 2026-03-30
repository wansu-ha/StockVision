"""Host → Runtime 어댑터.

engine/ports.py의 Protocol을 구현하는 얇은 래퍼.
host가 가진 구체 서비스(LogDB, CloudClient 등)를 port 인터페이스에 맞게 감싼다.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


class LogDbAdapter:
    """LogPort 구현 — LogDB를 감싸는 래퍼."""

    def __init__(self, log_db: Any) -> None:
        self._db = log_db

    async def write(
        self,
        log_type: str,
        message: str,
        *,
        symbol: str | None = None,
        meta: dict[str, Any] | None = None,
        intent_id: str | None = None,
    ) -> None:
        await self._db.async_write(
            log_type, message,
            symbol=symbol, meta=meta, intent_id=intent_id,
        )

    def today_realized_pnl(self) -> float:
        return self._db.today_realized_pnl()

    def today_executed_amount(self) -> Decimal:
        return self._db.today_executed_amount()


class CloudBarDataAdapter:
    """BarDataPort 구현 — CloudClient를 감싸는 래퍼.

    CloudClient가 None(미연결)이면 빈 리스트 반환.
    """

    def __init__(self, cloud_client: Any | None) -> None:
        self._client = cloud_client

    async def fetch_minute_bars(
        self, symbol: str, tf: str, limit: int,
    ) -> list[dict]:
        if self._client is None:
            return []
        try:
            path = f"/api/v1/stocks/{symbol}/bars?resolution={tf}&limit={limit}"
            resp = await self._client._get(path)
            return resp.get("data", []) if isinstance(resp, dict) else []
        except Exception:
            logger.warning("분봉 조회 실패 [%s %s]", symbol, tf)
            return []


class MinuteBarStoreAdapter:
    """BarStorePort 구현 — MinuteBarStore를 감싸는 래퍼."""

    def __init__(self, store: Any | None) -> None:
        self._store = store

    def save_bars(self, symbol: str, bars: list[dict]) -> None:
        if self._store is not None:
            self._store.save_bars(symbol, bars)


class StockMasterAdapter:
    """ReferenceDataPort 구현 — StockMasterCache를 감싸는 래퍼."""

    def __init__(self, cache: Any) -> None:
        self._cache = cache

    def get_market_map(self) -> dict[str, str]:
        return {
            s["symbol"]: s.get("market", "")
            for s in self._cache.get_all()
        }
