"""local_server.broker.kiwoom.adapter: 키움증권 BrokerAdapter 구현체

키움 REST API 모듈을 조합하여 BrokerAdapter ABC를 구현한다.
제네릭 모듈(state_machine, rate_limiter, idempotency, reconnect, reconciler)은
kis 패키지에서 재사용한다.
"""

import asyncio
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
from local_server.broker.kiwoom.error_classifier import KiwoomErrorClassifier
from local_server.broker.kiwoom.order import KiwoomOrder
from local_server.broker.kiwoom.quote import KiwoomQuote
from local_server.broker.kiwoom.ws import KiwoomWS

# 제네릭 모듈은 kis에서 재사용
from local_server.broker.kis.idempotency import IdempotencyGuard
from local_server.broker.kis.rate_limiter import MultiEndpointRateLimiter
from local_server.broker.kis.reconciler import Reconciler
from local_server.broker.kis.reconnect import ReconnectManager
from local_server.broker.kis.state_machine import ConnectionState, StateMachine

logger = logging.getLogger(__name__)

# 키움 API 호출 제한: 조회 5건/초, 주문 5건/초
KIWOOM_CPS = 5


class KiwoomAdapter(BrokerAdapter):
    """키움증권 BrokerAdapter 구현체.

    라이프사이클:
        adapter = KiwoomAdapter(app_key, secret_key, is_mock=True)
        await adapter.connect()
        ...
        await adapter.disconnect()
    """

    def __init__(
        self,
        app_key: str,
        secret_key: str,
        is_mock: bool = False,
    ) -> None:
        self._auth = KiwoomAuth(app_key, secret_key, is_mock)
        self._quote_client = KiwoomQuote(self._auth)
        self._order_client = KiwoomOrder(self._auth)
        self._ws = KiwoomWS(self._auth, is_mock)
        self._rate_limiter = MultiEndpointRateLimiter(KIWOOM_CPS)
        self._state = StateMachine()
        self._idempotency = IdempotencyGuard()
        self._error_classifier = KiwoomErrorClassifier()
        self._reconciler = Reconciler(self._order_client)  # type: ignore[arg-type]

        self._reconnect_mgr = ReconnectManager(
            state_machine=self._state,
            connect_fn=self._do_connect,
        )
        self._state.on_change(self._reconnect_mgr.on_state_change)

        self._ws_available = False
        self._rest_poll_task: Optional[asyncio.Task] = None
        self._rest_poll_callbacks: list[Callable[[QuoteEvent], None]] = []
        self._rest_poll_symbols: list[str] = []

    # ── 라이프사이클 ─────────────────────────────────

    async def connect(self) -> None:
        await self._state.transition(ConnectionState.CONNECTING)
        await self._do_connect()

    async def _do_connect(self) -> None:
        try:
            await self._state.transition(ConnectionState.CONNECTED)
            await self._auth.get_access_token()
            await self._state.transition(ConnectionState.AUTHENTICATED)
            logger.info("키움 인증 완료")

            try:
                await self._ws.connect()
                self._ws_available = True
                logger.info("키움 WebSocket 연결 완료 (mock=%s)", self._auth._is_mock)
            except Exception as ws_exc:
                self._ws_available = False
                logger.warning("키움 WebSocket 연결 실패 — REST 폴링 모드: %s", ws_exc)

            await self._state.transition(ConnectionState.SUBSCRIBED)

            await self._reconciler.start()

        except Exception as exc:
            logger.error("키움 연결 실패: %s", exc, exc_info=True)
            try:
                await self._state.transition(ConnectionState.ERROR)
            except Exception:
                pass
            raise ConnectionError(f"키움 연결 실패: {exc}") from exc

    async def disconnect(self) -> None:
        self._reconnect_mgr.disable()
        if self._rest_poll_task:
            self._rest_poll_task.cancel()
            self._rest_poll_task = None
        await self._reconciler.stop()
        if self._ws_available:
            await self._ws.disconnect()
        self._state.reset()
        logger.info("KiwoomAdapter 연결 종료")

    @property
    def is_connected(self) -> bool:
        return self._state.is_operational()

    # ── 잔고 조회 ─────────────────────────────────────

    async def get_balance(self) -> BalanceResult:
        self._assert_connected()
        await self._rate_limiter.acquire("balance")
        return await self._quote_client.get_balance()

    # ── 시세 조회 ─────────────────────────────────────

    async def get_quote(self, symbol: str) -> QuoteEvent:
        self._assert_connected()
        await self._rate_limiter.acquire("quote")
        return await self._quote_client.get_price(symbol)

    async def subscribe_quotes(
        self,
        symbols: list[str],
        callback: Callable[[QuoteEvent], None],
    ) -> None:
        self._assert_connected()
        if self._ws_available:
            self._ws.add_callback(callback)
            await self._ws.subscribe(symbols)
        else:
            # REST 폴링 폴백
            self._rest_poll_callbacks.append(callback)
            self._rest_poll_symbols = list(set(self._rest_poll_symbols + symbols))
            if self._rest_poll_task is None:
                self._rest_poll_task = asyncio.create_task(self._rest_poll_loop())
                logger.info("REST 폴링 시작 — %d종목, 10초 간격", len(self._rest_poll_symbols))

    async def unsubscribe_quotes(self, symbols: list[str]) -> None:
        if self._ws_available:
            await self._ws.unsubscribe(symbols)
        else:
            for s in symbols:
                if s in self._rest_poll_symbols:
                    self._rest_poll_symbols.remove(s)

    async def _rest_poll_loop(self) -> None:
        """WS 불가 시 REST로 시세 폴링 (10초 간격)."""
        while self._rest_poll_symbols:
            for sym in list(self._rest_poll_symbols):
                try:
                    await self._rate_limiter.acquire("quote")
                    event = await self._quote_client.get_price(sym)
                    for cb in self._rest_poll_callbacks:
                        cb(event)
                except Exception as exc:
                    logger.debug("REST 폴링 실패 [%s]: %s", sym, exc)
            await asyncio.sleep(10)
        self._rest_poll_task = None

    # ── 주문 실행 ─────────────────────────────────────

    async def place_order(
        self,
        client_order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: int,
        limit_price: Optional[Decimal] = None,
    ) -> OrderResult:
        self._assert_connected()

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

        await self._idempotency.register(result)
        self._reconciler.register_order(result)
        return result

    async def cancel_order(self, order_id: str) -> OrderResult:
        self._assert_connected()
        await self._rate_limiter.acquire("order")

        local = self._reconciler._local_orders.get(order_id)
        symbol = local.symbol if local else ""
        qty = local.qty if local else 0

        result = await self._order_client.cancel_order(order_id, symbol, qty)
        self._reconciler.update_order(order_id, OrderStatus.CANCELLED)
        return result

    async def get_open_orders(self) -> list[OrderResult]:
        self._assert_connected()
        await self._rate_limiter.acquire("order")
        return await self._order_client.get_open_orders()

    # ── 내부 유틸 ─────────────────────────────────────

    def _assert_connected(self) -> None:
        if not self._state.is_operational():
            raise RuntimeError(
                f"브로커에 연결되어 있지 않습니다 (상태: {self._state.state.value}). "
                "connect()를 먼저 호출하세요."
            )
