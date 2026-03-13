"""Safeguard — Kill Switch, 최대 손실 제한, 주문 속도 제한.

안전장치 3가지:
1. Kill Switch 2단계 (STOP_NEW, CANCEL_OPEN)
2. 최대 손실 제한 (일일 실현 손실 > 임계값 → 자동 락)
3. 주문 속도 제한 (분당 최대 주문 수)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

logger = logging.getLogger(__name__)


class KillSwitchLevel(Enum):
    """Kill Switch 단계."""

    OFF = 0
    STOP_NEW = 1       # 신규 주문 차단
    CANCEL_OPEN = 2    # 신규 차단 + 미체결 취소


@dataclass
class SafeguardState:
    """안전장치 상태."""

    kill_switch: KillSwitchLevel = KillSwitchLevel.OFF
    loss_lock: bool = False
    orders_this_minute: int = 0
    last_minute_reset: datetime = field(default_factory=datetime.now)


class Safeguard:
    """Kill Switch + 최대 손실 제한 + 주문 속도 제한."""

    DEFAULT_LOSS_THRESHOLD_PCT = Decimal("5.0")
    DEFAULT_MAX_ORDERS_PER_MINUTE = 10

    def __init__(
        self,
        max_loss_pct: Decimal | None = None,
        max_orders_per_minute: int | None = None,
    ) -> None:
        self._loss_threshold = max_loss_pct or self.DEFAULT_LOSS_THRESHOLD_PCT
        self._max_orders_per_min = max_orders_per_minute or self.DEFAULT_MAX_ORDERS_PER_MINUTE
        self._state = SafeguardState()

    def is_trading_enabled(self) -> bool:
        """거래 가능 여부."""
        if self._state.kill_switch != KillSwitchLevel.OFF:
            return False
        if self._state.loss_lock:
            return False
        return True

    def check_order_speed(self) -> bool:
        """주문 속도 제한 체크."""
        now = datetime.now()
        elapsed = (now - self._state.last_minute_reset).total_seconds()
        if elapsed > 60:
            self._state.orders_this_minute = 0
            self._state.last_minute_reset = now

        return self._state.orders_this_minute < self._max_orders_per_min

    def increment_order_count(self) -> None:
        """주문 카운트 증가."""
        self._state.orders_this_minute += 1

    def check_max_loss(
        self,
        today_realized_pnl: Decimal,
        account_balance: Decimal,
    ) -> bool:
        """최대 손실 제한 체크.

        Returns:
            True면 정상, False면 손실 초과 → 락 발동
        """
        if account_balance <= 0:
            return True
        if today_realized_pnl >= 0:
            return True

        loss_pct = abs(today_realized_pnl) / account_balance * 100
        if loss_pct > self._loss_threshold:
            self._state.loss_lock = True
            logger.critical(
                "최대 손실 제한 발동: 손실 %.2f%% > 임계값 %s%%",
                loss_pct, self._loss_threshold,
            )
            return False
        return True

    def set_kill_switch(self, level: KillSwitchLevel) -> None:
        """Kill Switch 설정."""
        self._state.kill_switch = level
        logger.warning("Kill Switch 설정: %s", level.name)

    def unlock_loss_lock(self) -> None:
        """손실 락 수동 해제."""
        self._state.loss_lock = False
        logger.info("손실 락 해제")

    @property
    def state(self) -> SafeguardState:
        return self._state
