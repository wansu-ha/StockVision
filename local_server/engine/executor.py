"""OrderExecutor — 주문 실행 파이프라인.

v2: side를 호출자 파라미터로 받음. execution dict에서 주문 설정 추출.
매도 보호: 보유수량 > 0 확인. trigger_policy 처리.
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
    from sv_core.broker.models import BalanceResult
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
    side: str
    message: str
    order_id: str | None = None
    realized_pnl: Decimal | None = None  # 매도 시 실현손익
    cycle_id: str | None = None
    signal_id: str | None = None
    intent_id: str | None = None  # 타임라인 그룹핑용


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
        side: str,
        market_data: dict[str, Any],
        balance: BalanceResult,
        intent_id: str | None = None,
    ) -> ExecutionResult:
        """주문 실행 파이프라인.

        Args:
            rule: 규칙 dict
            side: "BUY" | "SELL" (호출자가 결정)
            market_data: 시세 데이터
            balance: BalanceResult (cash, positions)
            intent_id: 타임라인 그룹핑용 ID
        """
        from local_server.storage.log_db import get_log_db, LOG_TYPE_ORDER, LOG_TYPE_FILL, LOG_TYPE_ERROR

        rule_id = int(rule.get("id", 0))
        symbol = str(rule.get("symbol", ""))
        db = get_log_db()

        # intent_id가 없으면 생성 (하위 호환)
        if not intent_id:
            intent_id = uuid.uuid4().hex[:12]

        # execution dict에서 주문 설정 추출 (없으면 개별 필드 폴백)
        execution = rule.get("execution") or {}
        order_type_str = str(execution.get("order_type", rule.get("order_type", "MARKET"))).upper()
        qty = int(execution.get("qty_value", rule.get("qty", 1)))
        limit_price_raw = execution.get("limit_price", rule.get("limit_price"))
        trigger_policy = rule.get("trigger_policy")

        # 매도 보호: 보유수량 > 0 확인 (spec §7.3)
        if side == "SELL":
            holding = any(p.symbol == symbol for p in balance.positions)
            if not holding:
                db.write(LOG_TYPE_ERROR, "미보유 종목 매도 거부", symbol=symbol,
                         meta={"rule_id": rule_id, "side": side}, intent_id=intent_id)
                return ExecutionResult(
                    status=ExecutionStatus.REJECTED,
                    rule_id=rule_id, symbol=symbol, side=side,
                    message="미보유 종목 매도 거부", intent_id=intent_id,
                )

        # 1. 중복 체크 (매수/매도 독립)
        if not self._signal.can_trigger(rule_id, side):
            msg = f"오늘 이미 실행된 규칙 ({side})"
            db.write(LOG_TYPE_ERROR, msg, symbol=symbol,
                     meta={"rule_id": rule_id, "side": side, "check": "duplicate"}, intent_id=intent_id)
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id, symbol=symbol, side=side,
                message=msg, intent_id=intent_id,
            )

        # 2. 한도 체크 (매수만)
        ws_price = Decimal(str(market_data.get("price", 0)))
        order_amount = ws_price * qty

        if side == "BUY":
            budget_check = self._limit.check_budget(balance.cash, order_amount)
            if not budget_check.ok:
                db.write(LOG_TYPE_ERROR, budget_check.reason, symbol=symbol,
                         meta={"rule_id": rule_id, "side": side, "check": "budget"}, intent_id=intent_id)
                return ExecutionResult(
                    status=ExecutionStatus.REJECTED,
                    rule_id=rule_id, symbol=symbol, side=side,
                    message=budget_check.reason, intent_id=intent_id,
                )

            pos_check = self._limit.check_max_positions(len(balance.positions))
            if not pos_check.ok:
                db.write(LOG_TYPE_ERROR, pos_check.reason, symbol=symbol,
                         meta={"rule_id": rule_id, "side": side, "check": "max_positions"}, intent_id=intent_id)
                return ExecutionResult(
                    status=ExecutionStatus.REJECTED,
                    rule_id=rule_id, symbol=symbol, side=side,
                    message=pos_check.reason, intent_id=intent_id,
                )

        # 3. 안전장치 체크
        if not self._safeguard.is_trading_enabled():
            msg = "Trading Enabled = OFF (Kill Switch 또는 손실 락)"
            db.write(LOG_TYPE_ERROR, msg, symbol=symbol,
                     meta={"rule_id": rule_id, "side": side, "check": "safeguard"}, intent_id=intent_id)
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id, symbol=symbol, side=side,
                message=msg, intent_id=intent_id,
            )

        if not self._safeguard.check_order_speed():
            msg = "주문 속도 제한 초과"
            db.write(LOG_TYPE_ERROR, msg, symbol=symbol,
                     meta={"rule_id": rule_id, "side": side, "check": "speed"}, intent_id=intent_id)
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id, symbol=symbol, side=side,
                message=msg, intent_id=intent_id,
            )

        # 4. 가격 검증
        verify_result = await self._price.verify(symbol, ws_price)
        if not verify_result.ok:
            msg = (
                f"가격 검증 실패 (WS={ws_price}, "
                f"REST={verify_result.actual_price}, "
                f"괴리={verify_result.diff_pct:.2f}%)"
            )
            db.write(LOG_TYPE_ERROR, msg, symbol=symbol,
                     meta={"rule_id": rule_id, "side": side, "check": "price_verify",
                            "ws_price": float(ws_price), "rest_price": float(verify_result.actual_price)},
                     intent_id=intent_id)
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id, symbol=symbol, side=side,
                message=msg, intent_id=intent_id,
            )

        # 5. 주문 제출 전 ORDER 로그
        db.write(LOG_TYPE_ORDER, f"주문 준비 ({side} {qty}주, {order_type_str})",
                 symbol=symbol, meta={"rule_id": rule_id, "side": side, "qty": qty, "order_type": order_type_str},
                 intent_id=intent_id)

        self._signal.mark_triggered(rule_id, side)
        order_side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
        order_type = OrderType.LIMIT if order_type_str == "LIMIT" else OrderType.MARKET
        limit_price = (
            Decimal(str(limit_price_raw))
            if limit_price_raw and order_type == OrderType.LIMIT
            else None
        )
        client_order_id = f"sv-{rule_id}-{uuid.uuid4().hex[:8]}"

        try:
            result = await self._broker.place_order(
                client_order_id=client_order_id,
                symbol=symbol,
                side=order_side,
                order_type=order_type,
                qty=qty,
                limit_price=limit_price,
            )

            self._safeguard.increment_order_count()
            self._signal.mark_filled(rule_id, side, trigger_policy)
            self._limit.record_execution(order_amount)

            # 주문 제출 완료 로그
            db.write(LOG_TYPE_ORDER, f"주문 제출 완료 (order_id={result.order_id})",
                     symbol=symbol, meta={"rule_id": rule_id, "side": side, "order_id": result.order_id,
                                          "qty": qty, "price": float(ws_price)},
                     intent_id=intent_id)

            # 매도 시 실현손익 추정 (v1: 시장가 기준)
            pnl: Decimal | None = None
            if side == "SELL":
                pos = next((p for p in balance.positions if p.symbol == symbol), None)
                if pos and pos.avg_price:
                    pnl = (ws_price - pos.avg_price) * qty

            # 체결 로그
            db.write(LOG_TYPE_FILL, f"체결 완료 ({ws_price}원, {qty}주)",
                     symbol=symbol, meta={"rule_id": rule_id, "side": side,
                                          "order_id": result.order_id, "fill_price": float(ws_price),
                                          "qty": qty, "realized_pnl": float(pnl) if pnl else None},
                     intent_id=intent_id)

            logger.info(
                "주문 성공: Rule %d, %s %s %d주, order_id=%s, pnl=%s",
                rule_id, side, symbol, qty, result.order_id, pnl,
            )

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                rule_id=rule_id, symbol=symbol, side=side,
                order_id=result.order_id,
                message="주문 성공",
                realized_pnl=pnl,
                intent_id=intent_id,
            )

        except Exception as e:
            self._signal.mark_failed(rule_id, side)
            logger.error("주문 실행 실패: Rule %d — %s", rule_id, e)
            db.write(LOG_TYPE_ERROR, f"주문 실행 실패: {e}",
                     symbol=symbol, meta={"rule_id": rule_id, "side": side, "error": str(e)},
                     intent_id=intent_id)
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                rule_id=rule_id, symbol=symbol, side=side,
                message=f"주문 실행 실패: {e}",
                intent_id=intent_id,
            )
