"""EngineScheduler — 장 시간 1분 주기 규칙 평가 스케줄러.

APScheduler의 AsyncIOScheduler를 사용하여
월~금 09:00~15:30 KST 동안 매 분 evaluate_all()을 호출한다.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Coroutine, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class EngineScheduler:
    """장 시간 1분 주기로 규칙 평가 실행."""

    def __init__(self, evaluate_fn: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._evaluate_fn = evaluate_fn
        self._scheduler = AsyncIOScheduler()
        self._running = False

    async def start(self) -> None:
        """스케줄러 시작. 장 시간에만 evaluate_fn을 호출한다."""
        self._scheduler.add_job(
            self._evaluate_fn,
            trigger="cron",
            day_of_week="mon-fri",
            hour="9-15",
            minute="*",
            second=0,
            timezone="Asia/Seoul",
            id="evaluate_all",
            replace_existing=True,
        )
        self._scheduler.start()
        self._running = True
        logger.info("EngineScheduler 시작")

    async def stop(self) -> None:
        """스케줄러 중지."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
        self._running = False
        logger.info("EngineScheduler 중지")

    @property
    def is_running(self) -> bool:
        return self._running
