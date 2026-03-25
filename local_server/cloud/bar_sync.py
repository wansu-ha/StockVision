"""로컬 분봉 → 클라우드 sync 워커.

BarBuilder가 로컬 SQLite에 저장한 완성된 분봉을
주기적으로 cloud API (POST /api/v1/bars/ingest)에 전송한다.

전송 실패 시 다음 주기에 재시도 (마지막 성공 시각 기준).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# sync 주기 (초)
SYNC_INTERVAL = 60
# 1회 전송 최대 건수
BATCH_SIZE = 500


class BarSyncWorker:
    """로컬 분봉을 cloud로 주기적 sync하는 워커."""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._last_sync_ts: datetime | None = None
        self._running = False

    async def start(self) -> None:
        """sync 루프 시작."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("BarSync 워커 시작")

    async def stop(self) -> None:
        """sync 루프 중지."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("BarSync 워커 중지")

    async def _loop(self) -> None:
        """주기적 sync 루프."""
        while self._running:
            try:
                await self._sync_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("BarSync 에러: %s", e)
            await asyncio.sleep(SYNC_INTERVAL)

    async def _sync_once(self) -> None:
        """마지막 sync 이후 새 분봉을 cloud로 전송."""
        from local_server.storage.minute_bar import get_minute_bar_store

        store = get_minute_bar_store()
        if store is None:
            return

        from local_server.cloud.client import CloudClient
        cloud = CloudClient.get_instance()
        if cloud is None or not cloud.has_token():
            return

        # 마지막 sync 이후 데이터 조회
        since = self._last_sync_ts or (datetime.now() - timedelta(hours=1))
        bars = store.get_bars_since(since, limit=BATCH_SIZE)

        if not bars:
            return

        # cloud API로 전송
        payload = {
            "bars": [
                {
                    "symbol": b["symbol"],
                    "timestamp": b["time"],
                    "open": int(b["open"]),
                    "high": int(b["high"]),
                    "low": int(b["low"]),
                    "close": int(b["close"]),
                    "volume": int(b["volume"]),
                }
                for b in bars
            ]
        }

        try:
            resp = await cloud.post("/api/v1/bars/ingest", json=payload)
            if resp and resp.get("success"):
                self._last_sync_ts = datetime.now()
                logger.info("BarSync 전송 완료: %d건", len(bars))
            else:
                logger.warning("BarSync 전송 실패: %s", resp)
        except Exception as e:
            logger.warning("BarSync 전송 에러: %s", e)
