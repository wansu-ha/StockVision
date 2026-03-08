"""키움증권 BrokerAdapter Unit 1 검증 테스트

수용 기준 (spec/kiwoom-rest/spec.md)을 코드 수준에서 검증한다.
실제 API 호출 없이 httpx/websockets 모킹으로 전 모듈을 커버한다.

카테고리:
- F1-F2: 인증 (토큰, 갱신, 모드 전환)
- F3: 주문 (매수/매도, 취소, 미체결)
- F4-F5: 조회 (현재가, 잔고)
- F6-F7: WebSocket (구독, 메시지 파싱)
- R1: RateLimiter
- R2: StateMachine
- R4: Reconciler
- R5: IdempotencyGuard
- R6: ErrorClassifier
- 재연결: ReconnectManager
"""

import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sv_core.broker.models import (
    BalanceResult,
    ErrorCategory,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    QuoteEvent,
)

# ── 제네릭 모듈 (kis 패키지에서 재사용) ────────────────────

from local_server.broker.kis.state_machine import (
    ConnectionState,
    InvalidStateTransitionError,
    StateMachine,
)
from local_server.broker.kis.rate_limiter import RateLimiter, MultiEndpointRateLimiter
from local_server.broker.kis.idempotency import IdempotencyGuard
from local_server.broker.kis.reconciler import (
    RECONCILE_GHOST,
    RECONCILE_MISMATCH,
    RECONCILE_ORPHAN,
    Reconciler,
)
from local_server.broker.kis.reconnect import ReconnectManager

# ── 키움 전용 모듈 ──────────────────────────────────────────

from local_server.broker.kiwoom.auth import KiwoomAuth, KIWOOM_BASE_URL_MOCK, KIWOOM_BASE_URL_REAL
from local_server.broker.kiwoom.quote import KiwoomQuote
from local_server.broker.kiwoom.order import KiwoomOrder, API_ID_BUY, API_ID_SELL, API_ID_CANCEL
from local_server.broker.kiwoom.ws import KiwoomWS
from local_server.broker.kiwoom.error_classifier import KiwoomErrorClassifier
from local_server.broker.kiwoom.adapter import KiwoomAdapter


# ══════════════════════════════════════════════════════════════
# R2: StateMachine
# ══════════════════════════════════════════════════════════════

class TestStateMachine:
    """상태 머신 전환 및 로그 기록 (R2)."""

    def test_initial_state_is_disconnected(self):
        sm = StateMachine()
        assert sm.state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_valid_full_lifecycle(self):
        """DISCONNECTED→CONNECTING→CONNECTED→AUTHENTICATED→SUBSCRIBED 정상 전환."""
        sm = StateMachine()
        transitions = []
        sm.on_change(lambda old, new: transitions.append((old, new)))

        await sm.transition(ConnectionState.CONNECTING)
        await sm.transition(ConnectionState.CONNECTED)
        await sm.transition(ConnectionState.AUTHENTICATED)
        await sm.transition(ConnectionState.SUBSCRIBED)

        assert sm.state == ConnectionState.SUBSCRIBED
        assert len(transitions) == 4
        assert transitions[0] == (ConnectionState.DISCONNECTED, ConnectionState.CONNECTING)
        assert transitions[-1] == (ConnectionState.AUTHENTICATED, ConnectionState.SUBSCRIBED)

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self):
        """유효하지 않은 전환 시 예외 발생."""
        sm = StateMachine()
        with pytest.raises(InvalidStateTransitionError):
            await sm.transition(ConnectionState.SUBSCRIBED)  # DISCONNECTED→SUBSCRIBED 불가

    @pytest.mark.asyncio
    async def test_error_to_connecting(self):
        """ERROR→CONNECTING 재연결 전환."""
        sm = StateMachine()
        await sm.transition(ConnectionState.CONNECTING)
        await sm.transition(ConnectionState.ERROR)
        await sm.transition(ConnectionState.CONNECTING)
        assert sm.state == ConnectionState.CONNECTING

    def test_is_operational(self):
        sm = StateMachine()
        assert sm.is_operational() is False

    @pytest.mark.asyncio
    async def test_is_operational_when_authenticated(self):
        sm = StateMachine()
        await sm.transition(ConnectionState.CONNECTING)
        await sm.transition(ConnectionState.CONNECTED)
        await sm.transition(ConnectionState.AUTHENTICATED)
        assert sm.is_operational() is True

    def test_reset(self):
        sm = StateMachine()
        sm._state = ConnectionState.ERROR  # 강제 설정
        sm.reset()
        assert sm.state == ConnectionState.DISCONNECTED


# ══════════════════════════════════════════════════════════════
# R1: RateLimiter
# ══════════════════════════════════════════════════════════════

class TestRateLimiter:
    """모든 REST 호출이 단일 RateLimiter를 경유 (R1)."""

    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        """한도 내 호출은 즉시 통과."""
        limiter = RateLimiter(calls_per_second=5)
        for _ in range(5):
            await limiter.acquire()
        assert limiter.total_calls == 5

    @pytest.mark.asyncio
    async def test_multi_endpoint_creates_per_endpoint(self):
        """엔드포인트별 개별 제한기 생성."""
        multi = MultiEndpointRateLimiter(default_cps=5)
        await multi.acquire("order")
        await multi.acquire("quote")
        assert "order" in multi._limiters
        assert "quote" in multi._limiters

    @pytest.mark.asyncio
    async def test_kiwoom_cps_is_5(self):
        """키움 API 제한: 5 CPS."""
        from local_server.broker.kiwoom.adapter import KIWOOM_CPS
        assert KIWOOM_CPS == 5


# ══════════════════════════════════════════════════════════════
# R5: IdempotencyGuard
# ══════════════════════════════════════════════════════════════

class TestIdempotencyGuard:
    """동일 signal_id 중복 주문 전송 불가 (R5)."""

    @pytest.mark.asyncio
    async def test_first_check_returns_none(self):
        guard = IdempotencyGuard()
        result = await guard.check("order-001")
        assert result is None

    @pytest.mark.asyncio
    async def test_duplicate_returns_existing(self):
        guard = IdempotencyGuard()
        existing = OrderResult(
            order_id="K12345",
            client_order_id="order-001",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=10,
            limit_price=None,
            status=OrderStatus.SUBMITTED,
        )
        await guard.register(existing)

        dup = await guard.check("order-001")
        assert dup is not None
        assert dup.order_id == "K12345"

    @pytest.mark.asyncio
    async def test_expired_records_cleaned(self):
        guard = IdempotencyGuard(ttl_hours=0)  # 즉시 만료
        existing = OrderResult(
            order_id="K12345",
            client_order_id="order-001",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=10,
            limit_price=None,
            status=OrderStatus.SUBMITTED,
        )
        await guard.register(existing)
        # TTL=0이므로 다음 check에서 만료 제거
        result = await guard.check("order-001")
        assert result is None


# ══════════════════════════════════════════════════════════════
# R6: ErrorClassifier
# ══════════════════════════════════════════════════════════════

class TestKiwoomErrorClassifier:
    """오류 분류별 처리 (R6)."""

    def setup_method(self):
        self.clf = KiwoomErrorClassifier()

    def test_http_401_is_auth(self):
        resp = MagicMock(spec=httpx.Response, status_code=401)
        exc = httpx.HTTPStatusError("", request=MagicMock(), response=resp)
        assert self.clf.classify_http_error(exc) == ErrorCategory.AUTH

    def test_http_429_is_rate_limit(self):
        resp = MagicMock(spec=httpx.Response, status_code=429)
        exc = httpx.HTTPStatusError("", request=MagicMock(), response=resp)
        assert self.clf.classify_http_error(exc) == ErrorCategory.RATE_LIMIT

    def test_http_500_is_transient(self):
        resp = MagicMock(spec=httpx.Response, status_code=500)
        exc = httpx.HTTPStatusError("", request=MagicMock(), response=resp)
        assert self.clf.classify_http_error(exc) == ErrorCategory.TRANSIENT

    def test_http_400_is_permanent(self):
        resp = MagicMock(spec=httpx.Response, status_code=400)
        exc = httpx.HTTPStatusError("", request=MagicMock(), response=resp)
        assert self.clf.classify_http_error(exc) == ErrorCategory.PERMANENT

    def test_api_token_error_is_auth(self):
        assert self.clf.classify_api_response(
            {"return_code": -1, "return_msg": "토큰이 만료되었습니다"}
        ) == ErrorCategory.AUTH

    def test_api_rate_limit_error(self):
        assert self.clf.classify_api_response(
            {"return_code": -2, "return_msg": "호출 횟수 초과"}
        ) == ErrorCategory.RATE_LIMIT

    def test_api_generic_error_is_permanent(self):
        assert self.clf.classify_api_response(
            {"return_code": -3, "return_msg": "종목코드 오류"}
        ) == ErrorCategory.PERMANENT

    def test_timeout_is_transient(self):
        exc = httpx.TimeoutException("")
        assert self.clf.classify_exception(exc) == ErrorCategory.TRANSIENT

    def test_connect_error_is_transient(self):
        exc = httpx.ConnectError("")
        assert self.clf.classify_exception(exc) == ErrorCategory.TRANSIENT

    def test_is_retryable(self):
        assert self.clf.is_retryable(ErrorCategory.TRANSIENT) is True
        assert self.clf.is_retryable(ErrorCategory.RATE_LIMIT) is True
        assert self.clf.is_retryable(ErrorCategory.PERMANENT) is False

    def test_needs_reauth(self):
        assert self.clf.needs_reauth(ErrorCategory.AUTH) is True
        assert self.clf.needs_reauth(ErrorCategory.TRANSIENT) is False


# ══════════════════════════════════════════════════════════════
# F1-F2: KiwoomAuth (인증)
# ══════════════════════════════════════════════════════════════

def _mock_token_response():
    """성공적인 토큰 응답 mock."""
    expires_dt = (datetime.now() + timedelta(hours=24)).strftime("%Y%m%d%H%M%S")
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = {
        "return_code": 0,
        "token": "test-access-token-abc123",
        "token_type": "bearer",
        "expires_dt": expires_dt,
    }
    resp.raise_for_status = MagicMock()
    return resp


class TestKiwoomAuth:
    """App Key/Secret으로 Bearer Token 발급 (F1-F2)."""

    def test_mock_url(self):
        """모의투자 베이스 URL 전환 (F2)."""
        auth = KiwoomAuth("key", "secret", is_mock=True)
        assert auth.base_url == KIWOOM_BASE_URL_MOCK

    def test_real_url(self):
        """실거래 베이스 URL 전환 (F2)."""
        auth = KiwoomAuth("key", "secret", is_mock=False)
        assert auth.base_url == KIWOOM_BASE_URL_REAL

    def test_needs_refresh_when_no_token(self):
        auth = KiwoomAuth("key", "secret")
        assert auth._needs_refresh() is True

    @pytest.mark.asyncio
    async def test_get_access_token_fetches(self):
        """토큰 발급 성공 (F1)."""
        auth = KiwoomAuth("key", "secret", is_mock=True)

        mock_resp = _mock_token_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("local_server.broker.kiwoom.auth.httpx.AsyncClient", return_value=mock_client):
            token = await auth.get_access_token()

        assert token == "test-access-token-abc123"
        assert auth._token_info is not None
        assert auth._token_info.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_token_cached_on_second_call(self):
        """토큰 만료 전 자동 캐싱."""
        auth = KiwoomAuth("key", "secret", is_mock=True)

        mock_resp = _mock_token_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("local_server.broker.kiwoom.auth.httpx.AsyncClient", return_value=mock_client):
            t1 = await auth.get_access_token()
            t2 = await auth.get_access_token()

        assert t1 == t2
        # post는 한 번만 호출되어야 함 (두 번째는 캐시)
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_refresh_near_expiry(self):
        """토큰 만료 5분 전 자동 갱신 (F1)."""
        auth = KiwoomAuth("key", "secret", is_mock=True)

        # 첫 토큰: 곧 만료
        from local_server.broker.kiwoom.auth import TokenInfo
        auth._token_info = TokenInfo(
            access_token="old-token",
            token_type="bearer",
            expires_at=datetime.now() + timedelta(seconds=60),  # 1분 남음 (< 5분 여유)
        )

        mock_resp = _mock_token_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("local_server.broker.kiwoom.auth.httpx.AsyncClient", return_value=mock_client):
            token = await auth.get_access_token()

        assert token == "test-access-token-abc123"  # 새 토큰
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_build_headers_includes_api_id(self):
        """헤더에 authorization + api-id 포함."""
        auth = KiwoomAuth("key", "secret", is_mock=True)

        mock_resp = _mock_token_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("local_server.broker.kiwoom.auth.httpx.AsyncClient", return_value=mock_client):
            headers = await auth.build_headers("ka10007")

        assert headers["api-id"] == "ka10007"
        assert headers["authorization"] == "Bearer test-access-token-abc123"

    def test_invalidate_clears_token(self):
        auth = KiwoomAuth("key", "secret")
        from local_server.broker.kiwoom.auth import TokenInfo
        auth._token_info = TokenInfo("tok", "bearer", datetime.now() + timedelta(hours=1))
        auth.invalidate()
        assert auth._token_info is None
        assert auth._needs_refresh() is True


# ══════════════════════════════════════════════════════════════
# F4-F5: KiwoomQuote (조회)
# ══════════════════════════════════════════════════════════════

class TestKiwoomQuote:
    """현재가/잔고 조회 (F4-F5)."""

    def _make_auth(self):
        auth = MagicMock(spec=KiwoomAuth)
        auth.base_url = "https://mockapi.kiwoom.com"
        auth.build_headers = AsyncMock(return_value={
            "authorization": "Bearer test",
            "api-id": "ka10007",
            "Content-Type": "application/json;charset=UTF-8",
        })
        return auth

    @pytest.mark.asyncio
    async def test_get_price_decimal(self):
        """현재가 조회 → Decimal 가격 반환 (F4)."""
        auth = self._make_auth()
        quote = KiwoomQuote(auth)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = {
            "return_code": 0,
            "stk_cd": "005930",
            "cur_prc": "-72500",  # 부호 접두사
            "trde_qty": "1234567",
            "buy_1bid": "72400",
            "sel_1bid": "72500",
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("local_server.broker.kiwoom.quote.httpx.AsyncClient", return_value=mock_client):
            result = await quote.get_price("005930")

        assert isinstance(result, QuoteEvent)
        assert result.symbol == "005930"
        assert result.price == Decimal("72500")  # abs() 변환
        assert result.volume == 1234567
        assert result.bid_price == Decimal("72400")
        assert result.ask_price == Decimal("72500")

    @pytest.mark.asyncio
    async def test_get_balance_positions(self):
        """잔고 조회 → 예수금 + 보유종목 반환 (F5)."""
        auth = self._make_auth()
        quote = KiwoomQuote(auth)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = {
            "return_code": 0,
            "tot_dps_amt": "5000000",
            "tot_evlt_amt": "7500000",
            "stk_list": [
                {
                    "stk_cd": "005930",
                    "hldg_qty": "100",
                    "avg_pur_prc": "70000",
                    "cur_prc": "72500",
                    "evlt_amt": "7250000",
                    "evlt_pl": "250000",
                    "evlt_pl_rt": "3.57",
                },
            ],
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("local_server.broker.kiwoom.quote.httpx.AsyncClient", return_value=mock_client):
            result = await quote.get_balance()

        assert isinstance(result, BalanceResult)
        assert result.cash == Decimal("5000000")
        assert result.total_eval == Decimal("7500000")
        assert len(result.positions) == 1
        pos = result.positions[0]
        assert pos.symbol == "005930"
        assert pos.qty == 100
        assert pos.avg_price == Decimal("70000")

    @pytest.mark.asyncio
    async def test_get_price_error_raises(self):
        """현재가 조회 실패 시 RuntimeError."""
        auth = self._make_auth()
        quote = KiwoomQuote(auth)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = {
            "return_code": -1,
            "return_msg": "종목 코드 오류",
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("local_server.broker.kiwoom.quote.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="현재가 조회 실패"):
                await quote.get_price("999999")


# ══════════════════════════════════════════════════════════════
# F3: KiwoomOrder (주문)
# ══════════════════════════════════════════════════════════════

class TestKiwoomOrder:
    """모의투자 주문 실행/취소 (F3)."""

    def _make_auth(self):
        auth = MagicMock(spec=KiwoomAuth)
        auth.base_url = "https://mockapi.kiwoom.com"
        auth.build_headers = AsyncMock(return_value={
            "authorization": "Bearer test",
            "api-id": "kt10000",
            "Content-Type": "application/json;charset=UTF-8",
        })
        return auth

    @pytest.mark.asyncio
    async def test_market_buy(self):
        """시장가 매수 → 주문번호 수신 (F3)."""
        auth = self._make_auth()
        order = KiwoomOrder(auth)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = {"return_code": 0, "ord_no": "20260308001"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("local_server.broker.kiwoom.order.httpx.AsyncClient", return_value=mock_client):
            result = await order.place_order(
                client_order_id="sig-001",
                symbol="005930",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                qty=10,
            )

        assert result.order_id == "20260308001"
        assert result.side == OrderSide.BUY
        assert result.order_type == OrderType.MARKET
        assert result.qty == 10
        assert result.status == OrderStatus.SUBMITTED

        # build_headers가 매수 api-id로 호출되었는지 확인
        auth.build_headers.assert_called_with(API_ID_BUY)

    @pytest.mark.asyncio
    async def test_limit_sell(self):
        """지정가 매도 → 주문번호 수신 (F3)."""
        auth = self._make_auth()
        order = KiwoomOrder(auth)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = {"return_code": 0, "ord_no": "20260308002"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("local_server.broker.kiwoom.order.httpx.AsyncClient", return_value=mock_client):
            result = await order.place_order(
                client_order_id="sig-002",
                symbol="005930",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                qty=5,
                limit_price=Decimal("75000"),
            )

        assert result.order_id == "20260308002"
        assert result.side == OrderSide.SELL
        assert result.limit_price == Decimal("75000")
        auth.build_headers.assert_called_with(API_ID_SELL)

    @pytest.mark.asyncio
    async def test_limit_order_without_price_raises(self):
        """지정가 주문에 가격 없으면 ValueError."""
        auth = self._make_auth()
        order = KiwoomOrder(auth)

        with pytest.raises(ValueError, match="limit_price"):
            await order.place_order(
                client_order_id="sig-003",
                symbol="005930",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                qty=10,
            )

    @pytest.mark.asyncio
    async def test_order_failure_raises(self):
        """주문 실패 시 RuntimeError (잔고 부족 등)."""
        auth = self._make_auth()
        order = KiwoomOrder(auth)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = {
            "return_code": -1,
            "return_msg": "주문가능금액이 부족합니다",
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("local_server.broker.kiwoom.order.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="주문 실패"):
                await order.place_order(
                    client_order_id="sig-004",
                    symbol="005930",
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    qty=10000,
                )

    @pytest.mark.asyncio
    async def test_cancel_order(self):
        """주문 취소 (F3)."""
        auth = self._make_auth()
        order = KiwoomOrder(auth)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = {"return_code": 0, "ord_no": "20260308001"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("local_server.broker.kiwoom.order.httpx.AsyncClient", return_value=mock_client):
            result = await order.cancel_order("20260308001", "005930", 10)

        assert result.status == OrderStatus.CANCELLED
        auth.build_headers.assert_called_with(API_ID_CANCEL)

    @pytest.mark.asyncio
    async def test_get_open_orders_parses(self):
        """미체결 주문 목록 파싱 (F3)."""
        auth = self._make_auth()
        order = KiwoomOrder(auth)

        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = {
            "return_code": 0,
            "oso": [
                {
                    "ord_no": "20260308001",
                    "stk_cd": "005930",
                    "sell_tp": "0",
                    "trde_tp": "3",
                    "ord_qty": "10",
                    "ord_uv": "0",
                    "ccld_qty": "0",
                },
                {
                    "ord_no": "20260308002",
                    "stk_cd": "035720",
                    "sell_tp": "1",
                    "trde_tp": "0",
                    "ord_qty": "5",
                    "ord_uv": "150000",
                    "ccld_qty": "2",
                },
            ],
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("local_server.broker.kiwoom.order.httpx.AsyncClient", return_value=mock_client):
            results = await order.get_open_orders()

        assert len(results) == 2
        # 첫 번째: 시장가 매수
        assert results[0].side == OrderSide.BUY
        assert results[0].order_type == OrderType.MARKET
        # 두 번째: 지정가 매도, 부분 체결
        assert results[1].side == OrderSide.SELL
        assert results[1].order_type == OrderType.LIMIT
        assert results[1].limit_price == Decimal("150000")
        assert results[1].filled_qty == 2


# ══════════════════════════════════════════════════════════════
# F6-F7: KiwoomWS (WebSocket 메시지 파싱)
# ══════════════════════════════════════════════════════════════

class TestKiwoomWS:
    """WebSocket 구독 및 메시지 파싱 (F6-F7)."""

    def _make_ws(self):
        auth = MagicMock(spec=KiwoomAuth)
        auth.get_access_token = AsyncMock(return_value="test-token")
        return KiwoomWS(auth, is_mock=True)

    def test_initial_state(self):
        ws = self._make_ws()
        assert ws.is_connected is False
        assert len(ws.get_subscribed_symbols()) == 0

    def test_handle_quote_data(self):
        """시세 메시지 파싱 → QuoteEvent → 콜백 호출."""
        ws = self._make_ws()
        received = []
        ws.add_callback(lambda ev: received.append(ev))

        msg = json.dumps({
            "stk_cd": "005930",
            "cur_prc": "-72500",
            "trde_qty": "100",
            "buy_1bid": "72400",
            "sel_1bid": "72500",
        })
        ws._handle_message(msg)

        assert len(received) == 1
        ev = received[0]
        assert ev.symbol == "005930"
        assert ev.price == Decimal("72500")
        assert ev.volume == 100

    def test_handle_non_json_ignored(self):
        """비JSON 메시지 무시."""
        ws = self._make_ws()
        received = []
        ws.add_callback(lambda ev: received.append(ev))

        ws._handle_message("not-json-data")
        assert len(received) == 0

    def test_handle_empty_message_ignored(self):
        ws = self._make_ws()
        received = []
        ws.add_callback(lambda ev: received.append(ev))

        ws._handle_message("")
        assert len(received) == 0

    def test_handle_non_quote_json_ignored(self):
        """stk_cd 없는 JSON 무시."""
        ws = self._make_ws()
        received = []
        ws.add_callback(lambda ev: received.append(ev))

        ws._handle_message(json.dumps({"type": "ack", "status": "ok"}))
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_subscribe_fails_when_not_connected(self):
        """미연결 상태에서 구독 시 RuntimeError."""
        ws = self._make_ws()
        with pytest.raises(RuntimeError, match="연결되어 있지 않습니다"):
            await ws.subscribe(["005930"])

    def test_callback_error_does_not_propagate(self):
        """콜백에서 예외 발생해도 다른 콜백 계속 호출."""
        ws = self._make_ws()
        results = []

        ws.add_callback(lambda ev: (_ for _ in ()).throw(ValueError("boom")))  # 예외 발생
        ws.add_callback(lambda ev: results.append(ev))

        msg = json.dumps({"stk_cd": "005930", "cur_prc": "72500", "trde_qty": "100"})
        ws._handle_message(msg)

        assert len(results) == 1  # 두 번째 콜백은 정상 호출


# ══════════════════════════════════════════════════════════════
# R4: Reconciler (대사)
# ══════════════════════════════════════════════════════════════

class TestReconciler:
    """리컨실리에이션: 미체결/잔고 조회로 WS 누락 보정 (R4)."""

    def _make_order(self, order_id, status=OrderStatus.SUBMITTED):
        return OrderResult(
            order_id=order_id,
            client_order_id=f"c-{order_id}",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=10,
            limit_price=None,
            status=status,
        )

    @pytest.mark.asyncio
    async def test_orphan_detection(self):
        """로컬에만 있는 주문 → ORPHAN 이벤트."""
        mock_client = MagicMock()
        mock_client.get_open_orders = AsyncMock(return_value=[])

        reconciler = Reconciler(mock_client)
        reconciler.register_order(self._make_order("ORD-001"))

        events = await reconciler.reconcile_once()
        orphans = [e for e in events if e.event_type == RECONCILE_ORPHAN]
        assert len(orphans) == 1
        assert orphans[0].order_id == "ORD-001"

    @pytest.mark.asyncio
    async def test_ghost_detection(self):
        """서버에만 있는 주문 → GHOST 이벤트."""
        server_order = self._make_order("ORD-999")
        mock_client = MagicMock()
        mock_client.get_open_orders = AsyncMock(return_value=[server_order])

        reconciler = Reconciler(mock_client)
        # 로컬에는 아무 주문도 없음

        events = await reconciler.reconcile_once()
        ghosts = [e for e in events if e.event_type == RECONCILE_GHOST]
        assert len(ghosts) == 1
        assert ghosts[0].order_id == "ORD-999"

    @pytest.mark.asyncio
    async def test_mismatch_detection(self):
        """상태 불일치 → MISMATCH 이벤트 + 서버 상태로 동기화."""
        local_order = self._make_order("ORD-001", OrderStatus.SUBMITTED)
        server_order = self._make_order("ORD-001", OrderStatus.PARTIAL_FILLED)

        mock_client = MagicMock()
        mock_client.get_open_orders = AsyncMock(return_value=[server_order])

        reconciler = Reconciler(mock_client)
        reconciler.register_order(local_order)

        events = await reconciler.reconcile_once()
        mismatches = [e for e in events if e.event_type == RECONCILE_MISMATCH]
        assert len(mismatches) == 1
        # 로컬 상태가 서버와 동기화되었는지 확인
        assert reconciler._local_orders["ORD-001"].status == OrderStatus.PARTIAL_FILLED

    @pytest.mark.asyncio
    async def test_no_events_when_in_sync(self):
        """로컬/서버 일치 시 이벤트 없음."""
        order = self._make_order("ORD-001")
        mock_client = MagicMock()
        mock_client.get_open_orders = AsyncMock(return_value=[order])

        reconciler = Reconciler(mock_client)
        reconciler.register_order(self._make_order("ORD-001"))

        events = await reconciler.reconcile_once()
        assert len(events) == 0


# ══════════════════════════════════════════════════════════════
# 재연결: ReconnectManager
# ══════════════════════════════════════════════════════════════

class TestReconnectManager:
    """연결 끊김 시 자동 재연결 (3회, 지수 백오프) (F7/R3)."""

    @pytest.mark.asyncio
    async def test_triggers_on_error_state(self):
        """ERROR 상태에서 재연결 태스크 시작."""
        sm = StateMachine()
        connect_fn = AsyncMock()
        mgr = ReconnectManager(sm, connect_fn, initial_delay=0.01, max_retries=1)

        mgr.on_state_change(ConnectionState.SUBSCRIBED, ConnectionState.ERROR)

        # 재연결 태스크 실행 대기
        await asyncio.sleep(0.05)
        connect_fn.assert_called()

    @pytest.mark.asyncio
    async def test_max_retries_stops(self):
        """최대 재시도 횟수 초과 시 포기."""
        sm = StateMachine()
        connect_fn = AsyncMock(side_effect=ConnectionError("fail"))
        mgr = ReconnectManager(sm, connect_fn, initial_delay=0.01, max_delay=0.02, max_retries=2)

        mgr.on_state_change(ConnectionState.SUBSCRIBED, ConnectionState.ERROR)
        await asyncio.sleep(0.2)

        assert connect_fn.call_count == 2

    @pytest.mark.asyncio
    async def test_disable_stops_reconnect(self):
        """disable() 호출 시 재연결 중단."""
        sm = StateMachine()
        connect_fn = AsyncMock(side_effect=ConnectionError("fail"))
        mgr = ReconnectManager(sm, connect_fn, initial_delay=0.5, max_retries=10)

        mgr.on_state_change(ConnectionState.SUBSCRIBED, ConnectionState.ERROR)
        await asyncio.sleep(0.05)
        mgr.disable()
        await asyncio.sleep(0.1)

        # disable 전 호출 횟수에서 멈춤
        count = connect_fn.call_count
        await asyncio.sleep(0.2)
        assert connect_fn.call_count == count


# ══════════════════════════════════════════════════════════════
# 통합: KiwoomAdapter
# ══════════════════════════════════════════════════════════════

class TestKiwoomAdapter:
    """KiwoomAdapter 통합 테스트."""

    def test_not_connected_initially(self):
        adapter = KiwoomAdapter("key", "secret", is_mock=True)
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_assert_connected_raises_when_disconnected(self):
        adapter = KiwoomAdapter("key", "secret", is_mock=True)
        with pytest.raises(RuntimeError, match="연결되어 있지 않습니다"):
            await adapter.get_balance()

    @pytest.mark.asyncio
    async def test_place_order_idempotency(self):
        """동일 client_order_id 중복 주문 방지 (R5)."""
        adapter = KiwoomAdapter("key", "secret", is_mock=True)
        # 상태를 운영 가능으로 설정
        adapter._state._state = ConnectionState.AUTHENTICATED

        existing = OrderResult(
            order_id="ORD-001",
            client_order_id="sig-001",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=10,
            limit_price=None,
            status=OrderStatus.SUBMITTED,
        )
        await adapter._idempotency.register(existing)

        # 동일 client_order_id로 재주문 → 기존 결과 반환
        result = await adapter.place_order(
            client_order_id="sig-001",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=10,
        )
        assert result.order_id == "ORD-001"

    @pytest.mark.asyncio
    async def test_place_order_goes_through_rate_limiter(self):
        """주문이 RateLimiter를 경유하는지 확인 (R1)."""
        adapter = KiwoomAdapter("key", "secret", is_mock=True)
        adapter._state._state = ConnectionState.AUTHENTICATED

        # rate_limiter.acquire를 모킹하여 호출 확인
        adapter._rate_limiter.acquire = AsyncMock()

        # order_client.place_order 모킹
        mock_result = OrderResult(
            order_id="ORD-002",
            client_order_id="sig-002",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=10,
            limit_price=None,
            status=OrderStatus.SUBMITTED,
        )
        adapter._order_client.place_order = AsyncMock(return_value=mock_result)

        await adapter.place_order(
            client_order_id="sig-002",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=10,
        )

        adapter._rate_limiter.acquire.assert_called_with("order")

    @pytest.mark.asyncio
    async def test_get_quote_goes_through_rate_limiter(self):
        """시세 조회가 RateLimiter를 경유하는지 확인 (R1)."""
        adapter = KiwoomAdapter("key", "secret", is_mock=True)
        adapter._state._state = ConnectionState.AUTHENTICATED

        adapter._rate_limiter.acquire = AsyncMock()
        adapter._quote_client.get_price = AsyncMock(return_value=QuoteEvent(
            symbol="005930", price=Decimal("72500"), volume=100,
        ))

        await adapter.get_quote("005930")
        adapter._rate_limiter.acquire.assert_called_with("quote")
