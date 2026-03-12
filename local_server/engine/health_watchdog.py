"""HealthWatchdog — 엔진/브로커 헬스 체크 (독립 asyncio 태스크).

evaluate_all()과 분리된 독립 태스크로 30초마다 실행된다.
엔진이 죽어도 이 태스크는 살아서 경고를 발송한다.

오탐 방지:
- 시작 후 5분 grace period (최초 evaluate_all 실행 전)
- 장 시간(09:00~15:30) 외에는 하트비트 체크 비활성화
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from local_server.engine.alert_monitor import AlertMonitor

logger = logging.getLogger(__name__)

MARKET_OPEN = (9, 0)    # 09:00
MARKET_CLOSE = (15, 30)  # 15:30
GRACE_PERIOD = timedelta(minutes=5)
HEARTBEAT_THRESHOLD = timedelta(minutes=3)
BROKER_FAIL_THRESHOLD = 3


class HealthWatchdog:
    """엔진/브로커 헬스 체크 독립 태스크."""

    def __init__(
        self,
        alert_monitor: "AlertMonitor",
        check_interval: int = 30,
    ) -> None:
        self._alert_monitor = alert_monitor
        self._check_interval = check_interval
        self._started_at = datetime.now()
        self._broker_fail_count = 0
        self._task: asyncio.Task | None = None

        # 엔진 / 브로커 참조 (start() 이후 외부에서 주입)
        self._engine: Any = None
        self._broker: Any = None

    def set_engine(self, engine: Any) -> None:
        """엔진 참조 주입 (app.state에서 엔진이 생성된 후 호출)."""
        self._engine = engine

    def set_broker(self, broker: Any) -> None:
        """브로커 참조 주입."""
        self._broker = broker

    async def start(self) -> None:
        """헬스 체크 태스크를 시작한다."""
        self._started_at = datetime.now()
        self._task = asyncio.create_task(self._loop())
        logger.info("HealthWatchdog 시작 (interval=%ds)", self._check_interval)

    async def stop(self) -> None:
        """헬스 체크 태스크를 중지한다."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("HealthWatchdog 중지")

    # ── 내부 루프 ──

    async def _loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._check_interval)
                await self._run_checks()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("HealthWatchdog 체크 오류")

    async def _run_checks(self) -> None:
        # grace period 중에는 체크하지 않음
        if datetime.now() - self._started_at < GRACE_PERIOD:
            return

        await self._check_engine_heartbeat()
        await self._check_broker_health()

    def _is_market_hours(self) -> bool:
        """현재 장 시간 여부 (09:00~15:30)."""
        now = datetime.now()
        open_dt = now.replace(hour=MARKET_OPEN[0], minute=MARKET_OPEN[1], second=0, microsecond=0)
        close_dt = now.replace(hour=MARKET_CLOSE[0], minute=MARKET_CLOSE[1], second=0, microsecond=0)
        return open_dt <= now <= close_dt

    async def _check_engine_heartbeat(self) -> None:
        """evaluate_all 마지막 실행 시각이 3분 초과 시 critical.

        장 시간(09:00~15:30) 외에는 체크하지 않는다.
        엔진이 None이면 (아직 시작 전) 체크하지 않는다.
        """
        if not self._is_market_hours():
            return
        if self._engine is None:
            return

        last_ts = getattr(self._engine, "_last_evaluate_ts", None)
        if last_ts is None:
            # 엔진이 존재하지만 아직 한 번도 evaluate_all 실행 안 됨 → 체크 보류
            return

        elapsed = datetime.now() - last_ts
        if elapsed > HEARTBEAT_THRESHOLD:
            await self._alert_monitor.fire(
                alert_type="engine_health",
                severity="critical",
                title="엔진 비정상 정지",
                message=f"전략 엔진이 {int(elapsed.total_seconds() / 60)}분간 응답 없음",
                action_label="설정 확인",
                action_route="/settings",
                current_value=elapsed.total_seconds(),
                alert_key="engine_health",
            )

    async def _check_broker_health(self) -> None:
        """브로커 API ping 3회 연속 실패 시 critical."""
        if self._broker is None:
            return

        try:
            # ping: get_balance() 경량 호출로 대체 (브로커 어댑터 공통 메서드)
            await self._broker.get_balance()
            self._broker_fail_count = 0  # 성공 시 카운트 리셋
        except Exception as e:
            self._broker_fail_count += 1
            logger.debug("브로커 ping 실패 (%d/%d): %s", self._broker_fail_count, BROKER_FAIL_THRESHOLD, e)
            if self._broker_fail_count >= BROKER_FAIL_THRESHOLD:
                await self._alert_monitor.fire(
                    alert_type="broker_health",
                    severity="critical",
                    title="브로커 연결 단절",
                    message=f"브로커 API 응답 실패 {self._broker_fail_count}회 연속",
                    action_label="설정 확인",
                    action_route="/settings",
                    current_value=float(self._broker_fail_count),
                    alert_key="broker_health",
                )
