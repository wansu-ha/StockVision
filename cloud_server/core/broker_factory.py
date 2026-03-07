"""
BrokerAdapter 팩토리

서비스 KIS 키로 BrokerAdapter 인스턴스 생성.
sv_core.broker.kis.KisAdapter를 사용 (Unit 1에서 구현).
"""
import logging
from decimal import Decimal
from typing import Callable, Optional

from sv_core.broker.base import BrokerAdapter
from sv_core.broker.models import (
    BalanceResult, OrderResult, OrderSide, OrderStatus, OrderType, QuoteEvent,
)

logger = logging.getLogger(__name__)


class BrokerFactory:
    """브로커 어댑터 팩토리"""

    @staticmethod
    def create(broker_type: str = "kis", service_key: dict | None = None) -> BrokerAdapter:
        """
        BrokerAdapter 인스턴스 생성.

        Args:
            broker_type: "kis" (현재 지원)
            service_key: {"api_key": str, "api_secret": str}
        """
        if broker_type == "kis":
            try:
                from sv_core.broker.kis import KisAdapter
                return KisAdapter(
                    api_key=service_key["api_key"],
                    api_secret=service_key["api_secret"],
                )
            except ImportError:
                logger.warning("sv_core.broker.kis 미설치 - stub 반환")
                return _KisStub()

        raise ValueError(f"지원하지 않는 브로커 타입: {broker_type}")


class _KisStub(BrokerAdapter):
    """
    KisAdapter stub (sv_core 미설치 시 사용).
    실제 API 호출 없이 빈 응답 반환.
    Unit 1 구현 후 sv_core.broker.kis.KisAdapter로 교체.

    C5: 정본 BrokerAdapter ABC 시그니처에 맞게 재작성.
    """

    def __init__(self) -> None:
        self._connected = False

    # ── 연결 관리 ───────────────────────────────────────────────────────

    async def connect(self) -> None:
        """연결 (stub: 즉시 성공)"""
        self._connected = True
        logger.info("[KisStub] connect() 호출")

    async def disconnect(self) -> None:
        """연결 해제 (stub)"""
        self._connected = False
        logger.info("[KisStub] disconnect() 호출")

    @property
    def is_connected(self) -> bool:
        """연결 상태"""
        return self._connected

    # ── 잔고 조회 ──────────────────────────────────────────────────────

    async def get_balance(self) -> BalanceResult:
        """잔고 조회 (stub: 빈 잔고 반환). C4: account_no 파라미터 없음."""
        return BalanceResult(
            cash=Decimal("0"),
            total_eval=Decimal("0"),
            positions=[],
        )

    # ── 시세 조회 ──────────────────────────────────────────────────────

    async def get_quote(self, symbol: str) -> QuoteEvent:
        """현재가 조회 (stub: 0원 반환)"""
        return QuoteEvent(
            symbol=symbol,
            price=Decimal("0"),
            volume=0,
        )

    # ── 실시간 시세 구독 ────────────────────────────────────────────────

    async def subscribe_quotes(
        self,
        symbols: list[str],
        callback: Callable[[QuoteEvent], None],
    ) -> None:
        """실시간 시세 구독 (stub: 아무 이벤트도 발생시키지 않음)"""
        logger.info(f"[KisStub] subscribe_quotes({symbols})")

    async def unsubscribe_quotes(self, symbols: list[str]) -> None:
        """실시간 시세 구독 해제 (stub)"""
        logger.info(f"[KisStub] unsubscribe_quotes({symbols})")

    # ── 주문 ────────────────────────────────────────────────────────────

    async def place_order(
        self,
        client_order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: int,
        limit_price: Optional[Decimal] = None,
    ) -> OrderResult:
        """주문 (stub: REJECTED 반환)"""
        logger.info(f"[KisStub] place_order({symbol}, {side}, {order_type}, qty={qty})")
        return OrderResult(
            order_id="",
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=qty,
            limit_price=limit_price,
            status=OrderStatus.REJECTED,
        )

    async def cancel_order(self, order_id: str) -> OrderResult:
        """주문 취소 (stub: REJECTED 반환)"""
        logger.info(f"[KisStub] cancel_order({order_id})")
        return OrderResult(
            order_id=order_id,
            client_order_id="",
            symbol="",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=0,
            limit_price=None,
            status=OrderStatus.REJECTED,
        )

    async def get_open_orders(self) -> list[OrderResult]:
        """미체결 주문 조회 (stub: 빈 목록 반환)"""
        return []
