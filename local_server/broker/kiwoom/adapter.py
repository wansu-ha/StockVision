"""local_server.broker.kiwoom.adapter: 키움증권 BrokerAdapter 구현체

모든 kiwoom 모듈을 조합하여 BrokerAdapter ABC를 구현한다.
"""

import logging
from decimal import Decimal
from typing import Callable, Optional

from sv_core.broker.base import BrokerAdapter
from sv_core.broker.models import (
    BalanceResult,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    QuoteEvent,
)

from local_server.broker.kiwoom.auth import KiwoomAuth
from local_server.broker.kiwoom.error_classifier import ErrorClassifier
from local_server.broker.kiwoom.idempotency import IdempotencyGuard
from local_server.broker.kiwoom.order import KiwoomOrder
from local_server.broker.kiwoom.quote import KiwoomQuote
from local_server.broker.kiwoom.rate_limiter import MultiEndpointRateLimiter
from local_server.broker.kiwoom.reconciler import Reconciler
from local_server.broker.kiwoom.reconnect import ReconnectManager
from local_server.broker.kiwoom.state_machine import (
    ConnectionState,
    StateMachine,
)
from local_server.broker.kiwoom.ws import KiwoomWS

logger = logging.getLogger(__name__)


class KiwoomAdapter(BrokerAdapter):
    """키움증권 BrokerAdapter 구현체.

    라이프사이클:
        adapter = KiwoomAdapter(app_key, app_secret, account_no)
        await adapter.connect()   # 인증 + WS 연결
        ...
        await adapter.disconnect()
    """

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        account_no: str,
        is_mock: bool = False,
        rate_limit_cps: int = 20,
    ) -> None:
        """초기화.

        Args:
            app_key: 키움 App Key
            app_secret: 키움 App Secret
            account_no: 계좌번호
            is_mock: 모의투자 여부
            rate_limit_cps: 초당 REST 호출 수 한도
        """
        self._auth = KiwoomAuth(app_key, app_secret)
        self._quote_client = KiwoomQuote(self._auth, account_no, is_mock)
        self._order_client = KiwoomOrder(self._auth, account_no, is_mock)
        self._ws = KiwoomWS(self._auth)
        self._rate_limiter = MultiEndpointRateLimiter(rate_limit_cps)
        self._state = StateMachine()
        self._idempotency = IdempotencyGuard()
        self._error_classifier = ErrorClassifier()
        self._reconciler = Reconciler(self._order_client)

        # 재연결 관리자 설정
        self._reconnect_mgr = ReconnectManager(
            state_machine=self._state,
            connect_fn=self._do_connect,
        )
        self._state.on_change(self._reconnect_mgr.on_state_change)

    # ──────────────────────────────────────────
    # 라이프사이클
    # ──────────────────────────────────────────

    async def connect(self) -> None:
        """키움 서버에 연결한다. (인증 + WebSocket)

        Raises:
            ConnectionError: 연결/인증 실패 시
        """
        await self._state.transition(ConnectionState.CONNECTING)
        await self._do_connect()

    async def _do_connect(self) -> None:
        """실제 연결 로직. ReconnectManager에서 재호출된다."""
        try:
            # HTTP 연결 성공 (토큰 발급 전에 CONNECTED 전환)
            await self._state.transition(ConnectionState.CONNECTED)
            # 인증 토큰 발급
            await self._auth.get_access_token()
            await self._state.transition(ConnectionState.AUTHENTICATED)
            logger.info("키움 인증 완료")

            # WebSocket 연결
            await self._ws.connect()
            await self._state.transition(ConnectionState.SUBSCRIBED)
            logger.info("키움 WebSocket 연결 완료")

            # 대사 태스크 시작
            await self._reconciler.start()

        except Exception as exc:
            logger.error("키움 연결 실패: %s", exc, exc_info=True)
            try:
                await self._state.transition(ConnectionState.ERROR)
            except Exception:
                pass
            raise ConnectionError(f"키움 연결 실패: {exc}") from exc

    async def disconnect(self) -> None:
        """연결을 종료한다."""
        self._reconnect_mgr.disable()
        await self._reconciler.stop()
        await self._ws.disconnect()
        self._state.reset()
        logger.info("KiwoomAdapter 연결 종료")

    @property
    def is_connected(self) -> bool:
        """연결 상태를 반환한다."""
        return self._state.is_operational()

    # ──────────────────────────────────────────
    # 잔고 조회
    # ──────────────────────────────────────────

    async def get_balance(self) -> BalanceResult:
        """계좌 잔고를 조회한다."""
        self._assert_connected()
        await self._rate_limiter.acquire("balance")
        return await self._quote_client.get_balance()

    # ──────────────────────────────────────────
    # 시세 조회
    # ──────────────────────────────────────────

    async def get_quote(self, symbol: str) -> QuoteEvent:
        """종목 현재가를 조회한다."""
        self._assert_connected()
        await self._rate_limiter.acquire("quote")
        return await self._quote_client.get_price(symbol)

    async def subscribe_quotes(
        self,
        symbols: list[str],
        callback: Callable[[QuoteEvent], None],
    ) -> None:
        """실시간 시세 구독을 시작한다."""
        self._assert_connected()
        self._ws.add_callback(callback)
        await self._ws.subscribe(symbols)

    async def unsubscribe_quotes(self, symbols: list[str]) -> None:
        """실시간 시세 구독을 해제한다."""
        await self._ws.unsubscribe(symbols)

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
        """주문을 실행한다. 멱등성 보장."""
        self._assert_connected()

        # 중복 주문 확인
        existing = await self._idempotency.check(client_order_id)
        if existing is not None:
            return existing

        await self._rate_limiter.acquire("order")
        try:
            result = await self._order_client.place_order(
                client_order_id=client_order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                qty=qty,
                limit_price=limit_price,
            )
        except Exception as exc:
            category = self._error_classifier.classify_exception(exc)
            if self._error_classifier.needs_reauth(category):
                self._auth.invalidate()
            logger.error(
                "주문 실패 [%s]: client_id=%s — %s",
                category.value, client_order_id, exc,
            )
            raise

        # 성공: 멱등성 기록 + 대사 등록
        await self._idempotency.register(result)
        self._reconciler.register_order(result)
        return result

    async def cancel_order(self, order_id: str) -> OrderResult:
        """주문을 취소한다."""
        self._assert_connected()
        await self._rate_limiter.acquire("order")

        # 심볼/수량은 미체결 조회에서 가져와야 하나, 단순화를 위해 직접 전달
        # 실제 운영 시 reconciler의 _local_orders에서 조회
        local = self._reconciler._local_orders.get(order_id)
        symbol = local.symbol if local else ""
        qty = local.qty if local else 0

        result = await self._order_client.cancel_order(order_id, symbol, qty)
        self._reconciler.update_order(order_id, OrderStatus.CANCELLED)
        return result

    async def get_open_orders(self) -> list[OrderResult]:
        """미체결 주문 목록을 조회한다."""
        self._assert_connected()
        await self._rate_limiter.acquire("order")
        return await self._order_client.get_open_orders()

    # ──────────────────────────────────────────
    # 내부 유틸
    # ──────────────────────────────────────────

    def _assert_connected(self) -> None:
        """연결 상태를 확인한다.

        Raises:
            RuntimeError: 미연결 상태일 때
        """
        if not self._state.is_operational():
            raise RuntimeError(
                f"브로커에 연결되어 있지 않습니다 (상태: {self._state.state.value}). "
                "connect()를 먼저 호출하세요."
            )
