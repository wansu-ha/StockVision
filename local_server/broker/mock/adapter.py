"""local_server.broker.mock.adapter: 테스트용 인메모리 브로커 어댑터

실제 키움 API 없이 BrokerAdapter를 완전히 모사한다.
단위 테스트 및 개발 환경에서 사용한다.
"""

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Callable, Optional

from sv_core.broker.base import BrokerAdapter
from sv_core.broker.models import (
    BalanceResult,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    QuoteEvent,
)

logger = logging.getLogger(__name__)

# 기본 모의 잔고
DEFAULT_INITIAL_CASH = Decimal("10_000_000")  # 1천만원

# 모의 현재가 (고정값, 테스트용)
DEFAULT_MOCK_PRICE: dict[str, Decimal] = {
    "005930": Decimal("75000"),  # 삼성전자
    "000660": Decimal("180000"),  # SK하이닉스
    "035420": Decimal("50000"),   # NAVER
}
DEFAULT_PRICE_FALLBACK = Decimal("10000")


class MockAdapter(BrokerAdapter):
    """테스트용 인메모리 브로커 어댑터.

    - 가격은 고정값 사용 (set_price로 변경 가능)
    - 주문은 즉시 체결 처리
    - 잔고/포지션은 주문 체결 시 자동 갱신
    """

    def __init__(self, initial_cash: Decimal = DEFAULT_INITIAL_CASH) -> None:
        """초기화.

        Args:
            initial_cash: 초기 현금 잔고
        """
        self._cash = initial_cash
        self._positions: dict[str, Position] = {}
        self._orders: dict[str, OrderResult] = {}
        self._prices: dict[str, Decimal] = dict(DEFAULT_MOCK_PRICE)
        self._connected = False
        self._quote_callbacks: list[Callable[[QuoteEvent], None]] = []
        self._subscribed: set[str] = set()

    # ──────────────────────────────────────────
    # 라이프사이클
    # ──────────────────────────────────────────

    async def connect(self) -> None:
        """모의 연결 (즉시 완료)."""
        self._connected = True
        logger.info("MockAdapter 연결 완료")

    async def disconnect(self) -> None:
        """모의 연결 해제."""
        self._connected = False
        self._subscribed.clear()
        logger.info("MockAdapter 연결 해제")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ──────────────────────────────────────────
    # 잔고 조회
    # ──────────────────────────────────────────

    async def get_balance(self) -> BalanceResult:
        """인메모리 잔고를 반환한다."""
        self._assert_connected()
        positions = list(self._positions.values())

        # 보유 주식 평가액 계산
        stock_eval = sum(
            self._prices.get(pos.symbol, DEFAULT_PRICE_FALLBACK) * pos.qty
            for pos in positions
        )
        total_eval = self._cash + stock_eval

        # 포지션 현재가 및 평가 갱신
        updated_positions = [
            Position(
                symbol=pos.symbol,
                qty=pos.qty,
                avg_price=pos.avg_price,
                current_price=self._prices.get(pos.symbol, DEFAULT_PRICE_FALLBACK),
                eval_amount=self._prices.get(pos.symbol, DEFAULT_PRICE_FALLBACK) * pos.qty,
                unrealized_pnl=(
                    self._prices.get(pos.symbol, DEFAULT_PRICE_FALLBACK) - pos.avg_price
                ) * pos.qty,
                unrealized_pnl_rate=(
                    (self._prices.get(pos.symbol, DEFAULT_PRICE_FALLBACK) - pos.avg_price)
                    / pos.avg_price * 100
                ) if pos.avg_price > 0 else Decimal("0"),
            )
            for pos in positions
        ]

        return BalanceResult(
            cash=self._cash,
            total_eval=total_eval,
            positions=updated_positions,
        )

    # ──────────────────────────────────────────
    # 시세 조회
    # ──────────────────────────────────────────

    async def get_quote(self, symbol: str) -> QuoteEvent:
        """고정 가격으로 QuoteEvent를 반환한다."""
        self._assert_connected()
        price = self._prices.get(symbol, DEFAULT_PRICE_FALLBACK)
        return QuoteEvent(
            symbol=symbol,
            price=price,
            volume=1000,
            bid_price=price - Decimal("5"),
            ask_price=price + Decimal("5"),
            timestamp=datetime.now(),
        )

    async def subscribe_quotes(
        self,
        symbols: list[str],
        callback: Callable[[QuoteEvent], None],
    ) -> None:
        """모의 구독 (콜백 등록만, 실시간 이벤트 없음)."""
        self._assert_connected()
        self._quote_callbacks.append(callback)
        self._subscribed.update(symbols)
        logger.debug("MockAdapter 구독: %s", symbols)

    async def unsubscribe_quotes(self, symbols: list[str]) -> None:
        """모의 구독 해제."""
        for sym in symbols:
            self._subscribed.discard(sym)

    # ──────────────────────────────────────────
    # 주문 실행
    # ──────────────────────────────────────────

    async def place_order(
        self,
        client_order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: int,
        limit_price: Optional[Decimal] = None,
    ) -> OrderResult:
        """주문을 즉시 체결 처리한다."""
        self._assert_connected()

        price = self._prices.get(symbol, DEFAULT_PRICE_FALLBACK)
        order_id = f"MOCK-{uuid.uuid4().hex[:8].upper()}"
        total_amount = price * qty

        # 잔고/포지션 갱신
        if side == OrderSide.BUY:
            if self._cash < total_amount:
                raise ValueError(f"잔고 부족: 필요 {total_amount}, 보유 {self._cash}")
            self._cash -= total_amount
            self._apply_buy(symbol, qty, price)
        else:
            pos = self._positions.get(symbol)
            if pos is None or pos.qty < qty:
                raise ValueError(f"보유 수량 부족: {symbol} 필요 {qty}주")
            self._apply_sell(symbol, qty, price)
            self._cash += total_amount

        result = OrderResult(
            order_id=order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=qty,
            limit_price=limit_price,
            status=OrderStatus.FILLED,
            filled_qty=qty,
            filled_avg_price=price,
            submitted_at=datetime.now(),
        )
        self._orders[order_id] = result
        logger.info(
            "MockAdapter 주문 체결: %s %s %d주 @ %s",
            side.value, symbol, qty, price,
        )
        return result

    async def cancel_order(self, order_id: str) -> OrderResult:
        """주문을 취소 상태로 변경한다."""
        self._assert_connected()
        order = self._orders.get(order_id)
        if order is None:
            raise ValueError(f"주문을 찾을 수 없음: {order_id}")
        if order.status == OrderStatus.FILLED:
            raise ValueError(f"이미 체결된 주문은 취소할 수 없음: {order_id}")
        order.status = OrderStatus.CANCELLED
        return order

    async def get_open_orders(self) -> list[OrderResult]:
        """미체결 주문 목록을 반환한다 (MockAdapter에서는 항상 빈 리스트 — 즉시 체결)."""
        return [
            o for o in self._orders.values()
            if o.status == OrderStatus.SUBMITTED
        ]

    # ──────────────────────────────────────────
    # 테스트 유틸
    # ──────────────────────────────────────────

    def set_price(self, symbol: str, price: Decimal) -> None:
        """종목 가격을 설정한다. (테스트 시나리오 구성용)

        Args:
            symbol: 종목 코드
            price: 설정할 가격
        """
        self._prices[symbol] = price

    def reset(self, initial_cash: Decimal = DEFAULT_INITIAL_CASH) -> None:
        """상태를 초기화한다.

        Args:
            initial_cash: 리셋 후 초기 현금
        """
        self._cash = initial_cash
        self._positions.clear()
        self._orders.clear()
        self._prices = dict(DEFAULT_MOCK_PRICE)

    def fire_quote_event(self, event: QuoteEvent) -> None:
        """수동으로 시세 이벤트를 발생시킨다. (테스트용)

        Args:
            event: 발생시킬 QuoteEvent
        """
        for cb in self._quote_callbacks:
            try:
                cb(event)
            except Exception as exc:
                logger.error("MockAdapter 콜백 오류: %s", exc)

    # ──────────────────────────────────────────
    # 내부 유틸
    # ──────────────────────────────────────────

    def _apply_buy(self, symbol: str, qty: int, price: Decimal) -> None:
        """매수 체결 후 포지션을 갱신한다."""
        pos = self._positions.get(symbol)
        if pos is None:
            self._positions[symbol] = Position(
                symbol=symbol,
                qty=qty,
                avg_price=price,
                current_price=price,
                eval_amount=price * qty,
                unrealized_pnl=Decimal("0"),
                unrealized_pnl_rate=Decimal("0"),
            )
        else:
            # 평균 단가 재계산
            total_qty = pos.qty + qty
            avg_price = (pos.avg_price * pos.qty + price * qty) / total_qty
            pos.qty = total_qty
            pos.avg_price = avg_price

    def _apply_sell(self, symbol: str, qty: int, price: Decimal) -> None:
        """매도 체결 후 포지션을 갱신한다."""
        pos = self._positions.get(symbol)
        if pos is None:
            return
        pos.qty -= qty
        if pos.qty <= 0:
            del self._positions[symbol]

    def _assert_connected(self) -> None:
        """연결 상태를 확인한다."""
        if not self._connected:
            raise RuntimeError("MockAdapter가 연결되어 있지 않습니다. connect()를 먼저 호출하세요.")
