"""LimitChecker — 일일 예산 및 포지션 수 한도 체크."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from local_server.storage.log_db import LogDB

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """한도 체크 결과."""

    ok: bool
    reason: str = ""


class LimitChecker:
    """일일 거래 예산, 최대 포지션 수 체크."""

    def __init__(
        self,
        budget_ratio: Decimal = Decimal("0.1"),
        max_positions: int = 5,
    ) -> None:
        self._budget_ratio = budget_ratio  # 계좌의 N%
        self._max_positions = max_positions
        self._today_executed: Decimal = Decimal(0)
        self._last_date: date | None = None

    def check_budget(
        self,
        account_balance: Decimal,
        order_amount: Decimal,
    ) -> CheckResult:
        """일일 예산 체크."""
        max_daily = account_balance * self._budget_ratio
        if self._today_executed + order_amount > max_daily:
            return CheckResult(
                ok=False,
                reason=(
                    f"일일 예산 초과 "
                    f"({self._today_executed + order_amount} > {max_daily})"
                ),
            )
        return CheckResult(ok=True)

    def check_max_positions(self, current_positions: int) -> CheckResult:
        """최대 포지션 수 체크."""
        if current_positions >= self._max_positions:
            return CheckResult(
                ok=False,
                reason=f"포지션 수 초과 ({current_positions} >= {self._max_positions})",
            )
        return CheckResult(ok=True)

    def record_execution(self, amount: Decimal) -> None:
        """체결 금액 누적 (일일 예산 추적)."""
        self._today_executed += amount

    @property
    def today_executed(self) -> Decimal:
        """오늘 누적 체결 금액 (읽기용)."""
        return self._today_executed

    def reset_daily(self) -> None:
        """일일 누적 리셋."""
        self._today_executed = Decimal(0)
        logger.info("LimitChecker 일일 누적 리셋")

    def restore_from_db(self, log_db: LogDB) -> None:
        """당일 체결 금액을 LogDB에서 복원한다 (엔진 재시작 시)."""
        self._today_executed = log_db.today_executed_amount()
        self._last_date = date.today()
        logger.info("LimitChecker 복원: _today_executed=%s", self._today_executed)

    def check_date_boundary(self) -> None:
        """날짜 경계 감지 시 자동 리셋."""
        today = date.today()
        if self._last_date and self._last_date != today:
            self.reset_daily()
        self._last_date = today
