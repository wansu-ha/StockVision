"""sv_core.broker.base: BrokerAdapter 추상 기반 클래스"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import AsyncIterator, Callable, Optional

from sv_core.broker.models import (
    BalanceResult,
    OrderResult,
    OrderSide,
    OrderType,
    QuoteEvent,
)


class BrokerAdapter(ABC):
    """브로커 어댑터 추상 기반 클래스.

    모든 브로커 연동(키움, 모의 등)은 이 ABC를 구현해야 한다.
    외부에서는 이 인터페이스만 의존하며, 구체 구현체를 몰라도 된다.
    """

    # ──────────────────────────────────────────
    # 라이프사이클
    # ──────────────────────────────────────────

    @abstractmethod
    async def connect(self) -> None:
        """브로커에 연결한다. (인증 포함)

        Raises:
            ConnectionError: 연결 실패 시
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """브로커 연결을 끊는다."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """연결 상태를 반환한다."""

    # ──────────────────────────────────────────
    # 잔고 조회
    # ──────────────────────────────────────────

    @abstractmethod
    async def get_balance(self) -> BalanceResult:
        """계좌 잔고 및 보유 포지션을 조회한다.

        Returns:
            BalanceResult: 잔고 정보

        Raises:
            RuntimeError: 미연결 상태이거나 API 오류 시
        """

    # ──────────────────────────────────────────
    # 시세 조회
    # ──────────────────────────────────────────

    @abstractmethod
    async def get_quote(self, symbol: str) -> QuoteEvent:
        """종목의 현재가를 조회한다 (REST, 단건).

        Args:
            symbol: 종목 코드 (예: "005930")

        Returns:
            QuoteEvent: 현재 시세 정보
        """

    @abstractmethod
    async def subscribe_quotes(
        self,
        symbols: list[str],
        callback: Callable[[QuoteEvent], None],
    ) -> None:
        """실시간 시세 구독을 시작한다 (WebSocket).

        Args:
            symbols: 구독할 종목 코드 목록
            callback: 시세 이벤트 수신 시 호출되는 콜백 함수

        Raises:
            RuntimeError: 미연결 상태이거나 WebSocket 오류 시
        """

    @abstractmethod
    async def unsubscribe_quotes(self, symbols: list[str]) -> None:
        """실시간 시세 구독을 해제한다.

        Args:
            symbols: 구독 해제할 종목 코드 목록
        """

    # ──────────────────────────────────────────
    # 주문 실행
    # ──────────────────────────────────────────

    @abstractmethod
    async def place_order(
        self,
        client_order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: int,
        limit_price: Optional[Decimal] = None,
    ) -> OrderResult:
        """주문을 실행한다.

        Args:
            client_order_id: 클라이언트 주문 ID (멱등성 키)
            symbol: 종목 코드
            side: 매수/매도
            order_type: 시장가/지정가
            qty: 주문 수량
            limit_price: 지정가 (시장가면 None)

        Returns:
            OrderResult: 주문 결과

        Raises:
            ValueError: 잘못된 파라미터
            RuntimeError: API 오류 시
        """

    @abstractmethod
    async def cancel_order(self, order_id: str) -> OrderResult:
        """주문을 취소한다.

        Args:
            order_id: 브로커 주문 ID

        Returns:
            OrderResult: 취소된 주문 정보

        Raises:
            RuntimeError: 취소 불가 상태이거나 API 오류 시
        """

    @abstractmethod
    async def get_open_orders(self) -> list[OrderResult]:
        """미체결 주문 목록을 조회한다.

        Returns:
            list[OrderResult]: 미체결 주문 목록
        """
