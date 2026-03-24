"""Unit 3 전략 엔진 단위 테스트 + 통합 테스트.

MockBrokerAdapter를 사용하여 엔진 전체 흐름을 검증한다.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, date
from decimal import Decimal
from typing import Callable, Optional
from unittest.mock import AsyncMock

import pytest

from sv_core.broker.models import (
    BalanceResult,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    QuoteEvent,
)
from local_server.engine.evaluator import RuleEvaluator
from local_server.engine.signal_manager import SignalManager
from local_server.engine.price_verifier import PriceVerifier, VerifyResult
from local_server.engine.limit_checker import LimitChecker, CheckResult
from local_server.engine.safeguard import Safeguard, KillSwitchLevel
from local_server.engine.context_cache import ContextCache
from local_server.engine.bar_builder import BarBuilder, Bar
from local_server.engine.executor import OrderExecutor, ExecutionStatus


# ═══════════════════════════════════════
# Mock BrokerAdapter
# ═══════════════════════════════════════

class MockBrokerAdapter:
    """테스트용 BrokerAdapter mock."""

    def __init__(
        self,
        quote_price: Decimal = Decimal("50000"),
        balance_cash: Decimal = Decimal("10000000"),
    ) -> None:
        self._quote_price = quote_price
        self._balance_cash = balance_cash
        self._connected = True
        self._orders: list[dict] = []

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def get_balance(self) -> BalanceResult:
        return BalanceResult(
            cash=self._balance_cash,
            total_eval=self._balance_cash,
            positions=[],
        )

    async def get_quote(self, symbol: str) -> QuoteEvent:
        return QuoteEvent(
            symbol=symbol,
            price=self._quote_price,
            volume=1000,
            timestamp=datetime.now(),
        )

    async def subscribe_quotes(
        self, symbols: list[str], callback: Callable[[QuoteEvent], None],
    ) -> None:
        pass

    async def unsubscribe_quotes(self, symbols: list[str]) -> None:
        pass

    async def place_order(
        self,
        client_order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: int,
        limit_price: Optional[Decimal] = None,
    ) -> OrderResult:
        self._orders.append({
            "client_order_id": client_order_id,
            "symbol": symbol,
            "side": side,
            "qty": qty,
        })
        return OrderResult(
            order_id=f"ORD-{len(self._orders)}",
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=qty,
            limit_price=limit_price,
            status=OrderStatus.SUBMITTED,
        )

    async def cancel_order(self, order_id: str) -> OrderResult:
        return OrderResult(
            order_id=order_id,
            client_order_id="",
            symbol="",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=0,
            limit_price=None,
            status=OrderStatus.CANCELLED,
        )

    async def get_open_orders(self) -> list[OrderResult]:
        return []


# ═══════════════════════════════════════
# RuleEvaluator 테스트
# ═══════════════════════════════════════

def _buy_rule(operator: str = "AND", conditions: list | None = None) -> dict:
    """v2 buy_conditions 규칙 헬퍼."""
    return {"buy_conditions": {"operator": operator, "conditions": conditions or []}}


class TestRuleEvaluator:
    """v2 API: evaluate() → (buy, sell)."""

    def setup_method(self) -> None:
        self.evaluator = RuleEvaluator()

    def test_and_all_true(self) -> None:
        rule = _buy_rule("AND", [
            {"type": "price", "field": "price", "operator": ">", "value": 100},
            {"type": "price", "field": "price", "operator": "<", "value": 200},
        ])
        buy, sell = self.evaluator.evaluate(rule, {"price": Decimal("150")}, {})
        assert buy is True
        assert sell is False

    def test_and_one_false(self) -> None:
        rule = _buy_rule("AND", [
            {"type": "price", "field": "price", "operator": ">", "value": 100},
            {"type": "price", "field": "price", "operator": "<", "value": 120},
        ])
        buy, _ = self.evaluator.evaluate(rule, {"price": Decimal("150")}, {})
        assert buy is False

    def test_or_one_true(self) -> None:
        rule = _buy_rule("OR", [
            {"type": "price", "field": "price", "operator": ">", "value": 200},
            {"type": "price", "field": "price", "operator": "<", "value": 200},
        ])
        buy, _ = self.evaluator.evaluate(rule, {"price": Decimal("150")}, {})
        assert buy is True

    def test_or_all_false(self) -> None:
        rule = _buy_rule("OR", [
            {"type": "price", "field": "price", "operator": ">", "value": 200},
            {"type": "price", "field": "price", "operator": "==", "value": 300},
        ])
        buy, _ = self.evaluator.evaluate(rule, {"price": Decimal("150")}, {})
        assert buy is False

    def test_empty_conditions(self) -> None:
        rule = _buy_rule("AND", [])
        buy, sell = self.evaluator.evaluate(rule, {}, {})
        assert buy is False
        assert sell is False

    def test_context_condition(self) -> None:
        rule = _buy_rule("AND", [
            {"type": "context", "field": "kospi_rsi", "operator": "<", "value": 70},
        ])
        buy, _ = self.evaluator.evaluate(rule, {}, {"kospi_rsi": 55})
        assert buy is True

    def test_missing_field_returns_false(self) -> None:
        rule = _buy_rule("AND", [
            {"type": "price", "field": "nonexistent", "operator": ">", "value": 0},
        ])
        buy, _ = self.evaluator.evaluate(rule, {}, {})
        assert buy is False

    def test_all_comparison_operators(self) -> None:
        for op, expected in [("==", True), ("!=", False), ("<", False),
                             ("<=", True), (">", False), (">=", True)]:
            rule = _buy_rule("AND", [
                {"type": "price", "field": "price", "operator": op, "value": 100},
            ])
            buy, _ = self.evaluator.evaluate(rule, {"price": 100}, {})
            assert buy is expected, f"op={op}"


# ═══════════════════════════════════════
# SignalManager 테스트
# ═══════════════════════════════════════

class TestSignalManager:
    """v2 API: 매수/매도 독립 상태. side 파라미터 필수."""

    def setup_method(self) -> None:
        self.sm = SignalManager()

    def test_initial_state_idle(self) -> None:
        assert self.sm.get_state(1, "BUY") == "IDLE"
        assert self.sm.can_trigger(1, "BUY") is True

    def test_triggered_blocks_retry(self) -> None:
        self.sm.mark_triggered(1, "BUY")
        assert self.sm.can_trigger(1, "BUY") is False

    def test_filled_blocks_retry(self) -> None:
        self.sm.mark_triggered(1, "BUY")
        self.sm.mark_filled(1, "BUY")
        assert self.sm.can_trigger(1, "BUY") is False

    def test_failed_returns_to_idle(self) -> None:
        self.sm.mark_triggered(1, "BUY")
        self.sm.mark_failed(1, "BUY")
        assert self.sm.can_trigger(1, "BUY") is True

    def test_independent_rules(self) -> None:
        self.sm.mark_triggered(1, "BUY")
        assert self.sm.can_trigger(2, "BUY") is True

    def test_reset_all(self) -> None:
        self.sm.mark_triggered(1, "BUY")
        self.sm.reset_all()
        assert self.sm.can_trigger(1, "BUY") is True


# ═══════════════════════════════════════
# LimitChecker 테스트
# ═══════════════════════════════════════

class TestLimitChecker:
    def test_budget_ok(self) -> None:
        lc = LimitChecker(budget_ratio=Decimal("0.1"), max_positions=5)
        result = lc.check_budget(Decimal("10000000"), Decimal("500000"))
        assert result.ok is True

    def test_budget_exceeded(self) -> None:
        lc = LimitChecker(budget_ratio=Decimal("0.1"), max_positions=5)
        result = lc.check_budget(Decimal("10000000"), Decimal("2000000"))
        assert result.ok is False

    def test_positions_ok(self) -> None:
        lc = LimitChecker(max_positions=5)
        assert lc.check_max_positions(3).ok is True

    def test_positions_exceeded(self) -> None:
        lc = LimitChecker(max_positions=5)
        assert lc.check_max_positions(5).ok is False

    def test_cumulative_budget(self) -> None:
        lc = LimitChecker(budget_ratio=Decimal("0.1"), max_positions=5)
        lc.record_execution(Decimal("800000"))
        result = lc.check_budget(Decimal("10000000"), Decimal("500000"))
        assert result.ok is False  # 800k + 500k > 1M


# ═══════════════════════════════════════
# Safeguard 테스트
# ═══════════════════════════════════════

class TestSafeguard:
    def test_default_trading_enabled(self) -> None:
        sg = Safeguard()
        assert sg.is_trading_enabled() is True

    def test_kill_switch_stops_trading(self) -> None:
        sg = Safeguard()
        sg.set_kill_switch(KillSwitchLevel.STOP_NEW)
        assert sg.is_trading_enabled() is False

    def test_loss_lock(self) -> None:
        sg = Safeguard(max_loss_pct=Decimal("5.0"))
        result = sg.check_max_loss(Decimal("-600000"), Decimal("10000000"))
        assert result is False
        assert sg.state.loss_lock is True
        assert sg.is_trading_enabled() is False

    def test_loss_within_threshold(self) -> None:
        sg = Safeguard(max_loss_pct=Decimal("5.0"))
        result = sg.check_max_loss(Decimal("-400000"), Decimal("10000000"))
        assert result is True

    def test_unlock_loss_lock(self) -> None:
        sg = Safeguard()
        sg._state.loss_lock = True
        sg.unlock_loss_lock()
        assert sg.is_trading_enabled() is True

    def test_order_speed_limit(self) -> None:
        sg = Safeguard(max_orders_per_minute=2)
        assert sg.check_order_speed() is True
        sg.increment_order_count()
        sg.increment_order_count()
        assert sg.check_order_speed() is False


# ═══════════════════════════════════════
# PriceVerifier 테스트
# ═══════════════════════════════════════

class TestPriceVerifier:
    def test_price_within_tolerance(self) -> None:
        broker = MockBrokerAdapter(quote_price=Decimal("50000"))
        pv = PriceVerifier(broker)
        result = asyncio.run(pv.verify("005930", Decimal("50000")))
        assert result.ok is True
        assert result.diff_pct == Decimal(0)

    def test_price_exceeds_tolerance(self) -> None:
        broker = MockBrokerAdapter(quote_price=Decimal("51500"))
        pv = PriceVerifier(broker)
        result = asyncio.run(pv.verify("005930", Decimal("50000")))
        assert result.ok is False

    def test_zero_expected_price(self) -> None:
        broker = MockBrokerAdapter()
        pv = PriceVerifier(broker)
        result = asyncio.run(pv.verify("005930", Decimal("0")))
        assert result.ok is False


# ═══════════════════════════════════════
# ContextCache 테스트
# ═══════════════════════════════════════

class TestContextCache:
    def test_update_and_get(self) -> None:
        cc = ContextCache(ttl_seconds=3600)
        cc.update({"kospi_rsi": 55, "volatility": 0.02})
        assert cc.get()["kospi_rsi"] == 55
        assert cc.is_valid() is True

    def test_get_field(self) -> None:
        cc = ContextCache()
        cc.update({"key1": "val1"})
        assert cc.get_field("key1") == "val1"
        assert cc.get_field("missing", "default") == "default"

    def test_empty_cache_invalid(self) -> None:
        cc = ContextCache()
        assert cc.is_valid() is False

    def test_clear(self) -> None:
        cc = ContextCache()
        cc.update({"data": 1})
        cc.clear()
        assert cc.get() == {}
        assert cc.is_valid() is False


# ═══════════════════════════════════════
# BarBuilder 테스트
# ═══════════════════════════════════════

class TestBarBuilder:
    def test_first_quote_creates_bar(self) -> None:
        bb = BarBuilder()
        ts = datetime(2026, 3, 5, 10, 30, 15)
        bb.on_quote("005930", Decimal("50000"), 100, ts)
        bar = bb.get_current_bar("005930")
        assert bar is not None
        assert bar.open == Decimal("50000")
        assert bar.close == Decimal("50000")

    def test_same_minute_updates(self) -> None:
        bb = BarBuilder()
        ts1 = datetime(2026, 3, 5, 10, 30, 10)
        ts2 = datetime(2026, 3, 5, 10, 30, 30)
        ts3 = datetime(2026, 3, 5, 10, 30, 50)
        bb.on_quote("005930", Decimal("50000"), 100, ts1)
        bb.on_quote("005930", Decimal("51000"), 200, ts2)
        bb.on_quote("005930", Decimal("49000"), 150, ts3)
        bar = bb.get_current_bar("005930")
        assert bar.high == Decimal("51000")
        assert bar.low == Decimal("49000")
        assert bar.close == Decimal("49000")
        assert bar.volume == 450

    def test_minute_boundary_creates_new_bar(self) -> None:
        bb = BarBuilder()
        ts1 = datetime(2026, 3, 5, 10, 30, 50)
        ts2 = datetime(2026, 3, 5, 10, 31, 5)
        bb.on_quote("005930", Decimal("50000"), 100, ts1)
        bb.on_quote("005930", Decimal("51000"), 200, ts2)
        completed = bb.get_completed_bar("005930")
        assert completed is not None
        assert completed.close == Decimal("50000")
        current = bb.get_current_bar("005930")
        assert current.open == Decimal("51000")

    def test_get_latest(self) -> None:
        bb = BarBuilder()
        bb.on_quote("005930", Decimal("50000"), 100, datetime.now())
        latest = bb.get_latest("005930")
        assert latest is not None
        assert latest["price"] == Decimal("50000")


# ═══════════════════════════════════════
# OrderExecutor 통합 테스트
# ═══════════════════════════════════════

class TestOrderExecutor:
    def _make_executor(
        self,
        quote_price: Decimal = Decimal("50000"),
    ) -> tuple[OrderExecutor, MockBrokerAdapter]:
        broker = MockBrokerAdapter(quote_price=quote_price)
        sm = SignalManager()
        pv = PriceVerifier(broker)
        lc = LimitChecker(budget_ratio=Decimal("0.1"), max_positions=5)
        sg = Safeguard()
        executor = OrderExecutor(broker, sm, pv, lc, sg)
        return executor, broker

    def _balance(self, cash: Decimal = Decimal("10000000")) -> BalanceResult:
        return BalanceResult(cash=cash, total_eval=cash, positions=[])

    def test_successful_order(self) -> None:
        executor, broker = self._make_executor()
        rule = {"id": 1, "symbol": "005930", "qty": 1, "order_type": "MARKET"}
        market = {"price": Decimal("50000")}
        result = asyncio.run(executor.execute(rule, "BUY", market, self._balance()))
        assert result.status == ExecutionStatus.SUCCESS
        assert result.order_id is not None
        assert len(broker._orders) == 1

    def test_duplicate_rejected(self) -> None:
        executor, _ = self._make_executor()
        rule = {"id": 1, "symbol": "005930", "qty": 1, "order_type": "MARKET"}
        market = {"price": Decimal("50000")}
        asyncio.run(executor.execute(rule, "BUY", market, self._balance()))
        result = asyncio.run(executor.execute(rule, "BUY", market, self._balance()))
        assert result.status == ExecutionStatus.REJECTED
        assert "이미 실행" in result.message

    def test_price_mismatch_rejected(self) -> None:
        executor, _ = self._make_executor(quote_price=Decimal("55000"))
        rule = {"id": 1, "symbol": "005930", "qty": 1, "order_type": "MARKET"}
        market = {"price": Decimal("50000")}
        result = asyncio.run(executor.execute(rule, "BUY", market, self._balance()))
        assert result.status == ExecutionStatus.REJECTED
        assert "가격 검증 실패" in result.message

    def test_budget_exceeded_rejected(self) -> None:
        executor, _ = self._make_executor()
        rule = {"id": 1, "symbol": "005930", "qty": 100, "order_type": "MARKET"}
        market = {"price": Decimal("50000")}
        result = asyncio.run(executor.execute(rule, "BUY", market, self._balance()))
        assert result.status == ExecutionStatus.REJECTED
        assert "예산" in result.message

    def test_kill_switch_rejected(self) -> None:
        executor, _ = self._make_executor()
        executor._safeguard.set_kill_switch(KillSwitchLevel.STOP_NEW)
        rule = {"id": 1, "symbol": "005930", "qty": 1, "order_type": "MARKET"}
        market = {"price": Decimal("50000")}
        result = asyncio.run(executor.execute(rule, "BUY", market, self._balance()))
        assert result.status == ExecutionStatus.REJECTED
        assert "Kill Switch" in result.message


# ═══════════════════════════════════════
# 손실 락 → 미체결 취소 + 알림 통합 테스트
# ═══════════════════════════════════════

class TestLossLockCancelOrders:
    """check_max_loss() 발동 시 미체결 취소 + WS 알림 검증."""

    def _make_engine(self, open_orders: list | None = None):
        """StrategyEngine을 낮은 max_loss_pct로 구성한다."""
        from local_server.engine.engine import StrategyEngine

        broker = MockBrokerAdapter()
        # get_open_orders가 미체결 주문을 반환하도록 오버라이드
        if open_orders is not None:
            broker.get_open_orders = AsyncMock(return_value=open_orders)
        broker.cancel_order = AsyncMock(return_value=OrderResult(
            order_id="X", client_order_id="", symbol="", side=OrderSide.BUY,
            order_type=OrderType.MARKET, qty=0, limit_price=None,
            status=OrderStatus.CANCELLED,
        ))

        engine = StrategyEngine(broker, config={"max_loss_pct": "1.0"})
        return engine, broker

    def test_loss_lock_cancels_open_orders(self) -> None:
        """손실 제한 발동 시 미체결 주문이 전량 취소된다."""
        open_orders = [
            OrderResult(order_id="ORD-1", client_order_id="c1", symbol="005930",
                        side=OrderSide.BUY, order_type=OrderType.MARKET,
                        qty=10, limit_price=None, status=OrderStatus.SUBMITTED),
            OrderResult(order_id="ORD-2", client_order_id="c2", symbol="035720",
                        side=OrderSide.SELL, order_type=OrderType.LIMIT,
                        qty=5, limit_price=Decimal("30000"), status=OrderStatus.SUBMITTED),
        ]
        engine, broker = self._make_engine(open_orders=open_orders)

        # 손실 제한 발동
        result = engine.safeguard.check_max_loss(Decimal("-200000"), Decimal("10000000"))
        assert result is False
        assert engine.safeguard.state.loss_lock is True

        # _cancel_open_orders 호출
        cancelled = asyncio.run(engine._cancel_open_orders())
        assert cancelled == 2
        assert broker.cancel_order.call_count == 2
        broker.cancel_order.assert_any_call("ORD-1")
        broker.cancel_order.assert_any_call("ORD-2")

    def test_loss_lock_notifies_via_callback(self) -> None:
        """손실 제한 발동 시 AlertMonitor.fire()로 알림이 전달된다."""
        from unittest.mock import AsyncMock, patch
        import asyncio

        engine, _ = self._make_engine()

        with patch.object(engine._alert_monitor, "fire", new_callable=AsyncMock) as mock_fire:
            engine.safeguard.check_max_loss(Decimal("-200000"), Decimal("10000000"))
            asyncio.run(engine._notify_loss_lock(Decimal("-200000")))

            mock_fire.assert_called_once()
            call_kwargs = mock_fire.call_args.kwargs
            assert call_kwargs.get("alert_type") == "loss_lock"
            assert "손실" in call_kwargs.get("message", "")


# ═══════════════════════════════════════
# BarBuilder fill_gap 테스트
# ═══════════════════════════════════════

class TestBarBuilderFillGap:
    """WS 끊김 복구 시 REST 분봉 보충 검증."""

    def test_fill_gap_after_3min(self) -> None:
        """3분 gap 이후 fill_gap() 호출 시 1개 분봉이 보충된다."""
        from datetime import timedelta

        bb = BarBuilder()
        three_min_ago = datetime.now() - timedelta(minutes=3)
        bb.on_quote("005930", Decimal("50000"), 100, three_min_ago)

        broker = MockBrokerAdapter(quote_price=Decimal("51000"))
        filled = asyncio.run(bb.fill_gap("005930", broker))
        assert filled == 1

        # 보충된 시세가 latest에 반영
        latest = bb.get_latest("005930")
        assert latest is not None
        assert latest["price"] == Decimal("51000")

    def test_no_gap_no_fill(self) -> None:
        """gap 없을 때 fill_gap() 호출 시 0 반환."""
        bb = BarBuilder()
        bb.on_quote("005930", Decimal("50000"), 100, datetime.now())

        broker = MockBrokerAdapter()
        filled = asyncio.run(bb.fill_gap("005930", broker))
        assert filled == 0

    def test_fill_gap_unknown_symbol(self) -> None:
        """미수신 종목은 gap fill 하지 않는다."""
        bb = BarBuilder()
        broker = MockBrokerAdapter()
        filled = asyncio.run(bb.fill_gap("UNKNOWN", broker))
        assert filled == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
