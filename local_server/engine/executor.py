"""OrderExecutor — 주문 실행 파이프라인.

조건 충족 → 중복 체크 → 한도 체크 → 안전장치 → 가격 검증 → 주문 실행.
각 단계에서 거부되면 로그를 기록하고 거부 결과를 반환한다.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from sv_core.broker.models import OrderSide, OrderType

if TYPE_CHECKING:
    from sv_core.broker.base import BrokerAdapter
    from local_server.engine.limit_checker import LimitChecker
    from local_server.engine.price_verifier import PriceVerifier
    from local_server.engine.safeguard import Safeguard
    from local_server.engine.signal_manager import SignalManager

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """실행 결과 상태."""

    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class ExecutionResult:
    """주문 실행 결과."""

    status: ExecutionStatus
    rule_id: int
    symbol: str
    message: str
    order_id: str | None = None


class OrderExecutor:
    """조건 충족 → 가격 검증 → BrokerAdapter 주문."""

    def __init__(
        self,
        broker: BrokerAdapter,
        signal_manager: SignalManager,
        price_verifier: PriceVerifier,
        limit_checker: LimitChecker,
        safeguard: Safeguard,
    ) -> None:
        self._broker = broker
        self._signal = signal_manager
        self._price = price_verifier
        self._limit = limit_checker
        self._safeguard = safeguard

    async def execute(
        self,
        rule: dict[str, Any],
        market_data: dict[str, Any],
        balance_cash: Decimal,
        position_count: int,
    ) -> ExecutionResult:
        """주문 실행 파이프라인.

        1. 중복 체크 (SignalManager)
        2. 한도 체크 (LimitChecker)
        3. 안전장치 체크 (Safeguard)
        4. 가격 검증 (PriceVerifier)
        5. 주문 실행 (BrokerAdapter.place_order)
        """
        rule_id = int(rule.get("id", 0))
        symbol = str(rule.get("symbol", ""))
        side_str = str(rule.get("side", "BUY"))
        qty = int(rule.get("qty", 1))
        order_type_str = str(rule.get("order_type", "MARKET"))

        # 1. 중복 체크
        if not self._signal.can_trigger(rule_id):
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id,
                symbol=symbol,
                message="오늘 이미 실행된 규칙",
            )

        # 2. 한도 체크
        ws_price = Decimal(str(market_data.get("price", 0)))
        order_amount = ws_price * qty

        budget_check = self._limit.check_budget(balance_cash, order_amount)
        if not budget_check.ok:
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id,
                symbol=symbol,
                message=budget_check.reason,
            )

        pos_check = self._limit.check_max_positions(position_count)
        if not pos_check.ok:
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id,
                symbol=symbol,
                message=pos_check.reason,
            )

        # 3. 안전장치 체크
        if not self._safeguard.is_trading_enabled():
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id,
                symbol=symbol,
                message="Trading Enabled = OFF (Kill Switch 또는 손실 락)",
            )

        if not self._safeguard.check_order_speed():
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id,
                symbol=symbol,
                message="주문 속도 제한 초과",
            )

        # 4. 가격 검증 (실패 시 IDLE 복귀 — 일시적 괴리는 재시도 허용)
        verify_result = await self._price.verify(symbol, ws_price)
        if not verify_result.ok:
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id,
                symbol=symbol,
                message=(
                    f"가격 검증 실패 (WS={ws_price}, "
                    f"REST={verify_result.actual_price}, "
                    f"괴리={verify_result.diff_pct:.2f}%)"
                ),
            )

        # 5. 주문 실행 — mark_triggered는 주문 직전 (가격 검증 실패 시 재시도 가능)
        self._signal.mark_triggered(rule_id)
        side = OrderSide.BUY if side_str == "BUY" else OrderSide.SELL
        order_type = OrderType.LIMIT if order_type_str == "LIMIT" else OrderType.MARKET
        limit_price = (
            Decimal(str(rule.get("limit_price")))
            if rule.get("limit_price") and order_type == OrderType.LIMIT
            else None
        )
        client_order_id = f"sv-{rule_id}-{uuid.uuid4().hex[:8]}"

        try:
            result = await self._broker.place_order(
                client_order_id=client_order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                qty=qty,
                limit_price=limit_price,
            )

            self._safeguard.increment_order_count()
            self._signal.mark_filled(rule_id)
            self._limit.record_execution(order_amount)

            logger.info(
                "주문 성공: Rule %d, %s %s %d주, order_id=%s",
                rule_id, side.value, symbol, qty, result.order_id,
            )

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                rule_id=rule_id,
                symbol=symbol,
                order_id=result.order_id,
                message="주문 성공",
            )

        except Exception as e:
            self._signal.mark_failed(rule_id)
            logger.error("주문 실행 실패: Rule %d — %s", rule_id, e)
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                rule_id=rule_id,
                symbol=symbol,
                message=f"주문 실행 실패: {e}",
            )
