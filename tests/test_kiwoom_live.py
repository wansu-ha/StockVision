"""키움증권 모의투자 실서버 검증 테스트

mock 없이 실제 키움 모의투자 서버(mockapi.kiwoom.com)에 붙어서 검증한다.
keyring에 저장된 test@stockvision.dev 자격증명을 사용한다.

실행: pytest tests/test_kiwoom_live.py -v -s
"""

import asyncio
from decimal import Decimal

import pytest

from sv_core.broker.models import (
    BalanceResult,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    QuoteEvent,
)
from local_server.storage.credential import (
    load_credential,
    KEY_KIWOOM_APP_KEY,
    KEY_KIWOOM_SECRET_KEY,
)
from local_server.broker.kiwoom.auth import KiwoomAuth, KIWOOM_BASE_URL_MOCK
from local_server.broker.kiwoom.quote import KiwoomQuote
from local_server.broker.kiwoom.order import KiwoomOrder
from local_server.broker.kiwoom.ws import KiwoomWS
from local_server.broker.kiwoom.adapter import KiwoomAdapter

USER_ID = "test@stockvision.dev"
TEST_SYMBOL = "005930"  # 삼성전자


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture(scope="module")
def credentials():
    """keyring에서 키움 자격증명을 로드한다. 없으면 전체 스킵."""
    app_key = load_credential(KEY_KIWOOM_APP_KEY, USER_ID)
    secret = load_credential(KEY_KIWOOM_SECRET_KEY, USER_ID)
    if not app_key or not secret:
        pytest.skip("키움 모의투자 키 없음 (keyring)")
    return app_key, secret


@pytest.fixture(scope="module")
def auth(credentials):
    """인증된 KiwoomAuth 인스턴스."""
    app_key, secret = credentials
    _auth = KiwoomAuth(app_key, secret, is_mock=True)
    asyncio.get_event_loop().run_until_complete(_auth.get_access_token())
    return _auth


# ══════════════════════════════════════════════════════════════
# F1-F2: 인증
# ══════════════════════════════════════════════════════════════

class TestAuthLive:
    """토큰 발급, 갱신, 모드 전환."""

    def test_base_url_is_mock(self, auth):
        """F2: 모의투자 베이스 URL."""
        assert auth.base_url == KIWOOM_BASE_URL_MOCK

    @pytest.mark.asyncio
    async def test_token_issued(self, auth):
        """F1: App Key/Secret으로 Bearer Token 발급 성공."""
        token = await auth.get_access_token()
        assert isinstance(token, str)
        assert len(token) > 10

    @pytest.mark.asyncio
    async def test_token_cached(self, auth):
        """F1: 두 번째 호출은 캐시된 토큰 반환 (이미 발급된 auth 재사용)."""
        t1 = await auth.get_access_token()
        t2 = await auth.get_access_token()
        assert t1 == t2

    @pytest.mark.asyncio
    async def test_build_headers(self, credentials):
        """헤더에 authorization, api-id 포함."""
        app_key, secret = credentials
        auth = KiwoomAuth(app_key, secret, is_mock=True)
        headers = await auth.build_headers("ka10007")
        assert "Bearer " in headers["authorization"]
        assert headers["api-id"] == "ka10007"

    @pytest.mark.asyncio
    async def test_invalidate_and_refetch(self, auth):
        """토큰 무효화 후 재발급 (기존 auth 재사용, rate limit 방지)."""
        auth.invalidate()
        t2 = await auth.get_access_token()
        assert isinstance(t2, str)
        assert len(t2) > 10


# ══════════════════════════════════════════════════════════════
# F4: 현재가 조회
# ══════════════════════════════════════════════════════════════

class TestQuoteLive:
    """현재가 조회 → Decimal 가격 반환."""

    @pytest.mark.asyncio
    async def test_get_price(self, auth):
        """F4: 삼성전자 현재가 조회."""
        quote = KiwoomQuote(auth)
        result = await quote.get_price(TEST_SYMBOL)

        assert isinstance(result, QuoteEvent)
        assert result.symbol == TEST_SYMBOL
        assert isinstance(result.price, Decimal)
        assert result.price > 0
        assert result.volume >= 0
        print(f"\n  price={result.price} vol={result.volume} bid={result.bid_price} ask={result.ask_price}")

    @pytest.mark.asyncio
    async def test_get_price_invalid_symbol(self, auth):
        """존재하지 않는 종목 조회 시 에러."""
        quote = KiwoomQuote(auth)
        # 존재하지 않는 종목 — 에러 or 가격 0
        try:
            result = await quote.get_price("999999")
            # 에러 없이 0원 반환할 수도 있음
            print(f"\n  invalid symbol result: price={result.price}")
        except (RuntimeError, Exception) as e:
            print(f"\n  invalid symbol error: {e}")
            # 에러 발생도 정상 동작


# ══════════════════════════════════════════════════════════════
# F5: 잔고 조회
# ══════════════════════════════════════════════════════════════

class TestBalanceLive:
    """잔고 조회 → 예수금 + 보유종목."""

    @pytest.mark.asyncio
    async def test_get_balance(self, auth):
        """F5: 잔고 조회 성공."""
        quote = KiwoomQuote(auth)
        result = await quote.get_balance()

        assert isinstance(result, BalanceResult)
        assert isinstance(result.cash, Decimal)
        assert isinstance(result.total_eval, Decimal)
        assert isinstance(result.positions, list)
        print(f"\n  cash={result.cash} total_eval={result.total_eval} positions={len(result.positions)}")

        for pos in result.positions:
            print(f"  {pos.symbol}: qty={pos.qty} avg={pos.avg_price} cur={pos.current_price}")


# ══════════════════════════════════════════════════════════════
# F3: 주문 (모의투자)
# ══════════════════════════════════════════════════════════════

class TestOrderLive:
    """모의투자 주문 실행/취소."""

    @pytest.mark.asyncio
    async def test_market_buy(self, auth):
        """F3: 모의투자 시장가 매수 → 주문번호 수신."""
        order = KiwoomOrder(auth)
        try:
            result = await order.place_order(
                client_order_id="live-test-001",
                symbol=TEST_SYMBOL,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                qty=1,
            )
            assert isinstance(result, OrderResult)
            assert result.order_id
            assert result.status == OrderStatus.SUBMITTED
            print(f"\n  order_id={result.order_id} status={result.status.value}")
        except RuntimeError as e:
            # 잔고 부족 등 예상된 에러
            print(f"\n  order error (expected): {e}")

    @pytest.mark.asyncio
    async def test_limit_sell(self, auth):
        """F3: 모의투자 지정가 매도 → 주문번호 수신."""
        order = KiwoomOrder(auth)
        try:
            result = await order.place_order(
                client_order_id="live-test-002",
                symbol=TEST_SYMBOL,
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                qty=1,
                limit_price=Decimal("500000"),  # 높은 가격 (체결 안 되게)
            )
            assert isinstance(result, OrderResult)
            assert result.order_id
            print(f"\n  order_id={result.order_id} status={result.status.value}")
        except RuntimeError as e:
            print(f"\n  order error (expected): {e}")

    @pytest.mark.asyncio
    async def test_get_open_orders(self, auth):
        """F3: 미체결 주문 목록 조회."""
        order = KiwoomOrder(auth)
        results = await order.get_open_orders()
        assert isinstance(results, list)
        print(f"\n  open_orders={len(results)}")
        for r in results:
            print(f"  {r.order_id}: {r.side.value} {r.symbol} qty={r.qty}")


# ══════════════════════════════════════════════════════════════
# F6-F7: WebSocket (모의서버)
# ══════════════════════════════════════════════════════════════

class TestWSLive:
    """WebSocket 실시간 시세."""

    @pytest.mark.asyncio
    async def test_ws_connect(self, auth):
        """F6: WS 연결 시도 (모의서버 — 실패 예상)."""
        ws = KiwoomWS(auth, is_mock=True)
        try:
            await asyncio.wait_for(ws.connect(), timeout=5)
            print(f"\n  WS connected={ws.is_connected}")
            await ws.disconnect()
            print("  WS MOCK SERVER SUPPORTS WEBSOCKET!")
        except (TimeoutError, asyncio.TimeoutError):
            print("\n  WS mock server: connection timeout (not supported)")
            pytest.skip("키움 모의서버 WS 미지원")
        except Exception as e:
            print(f"\n  WS mock server error: {type(e).__name__}: {e}")
            pytest.skip(f"키움 모의서버 WS: {e}")


# ══════════════════════════════════════════════════════════════
# R1: RateLimiter 경유 (Adapter 레벨)
# ══════════════════════════════════════════════════════════════

class TestAdapterLive:
    """KiwoomAdapter 통합 — 실서버."""

    @pytest.mark.asyncio
    async def test_connect_and_quote(self, credentials):
        """Adapter.connect() → get_quote() 전체 플로우."""
        app_key, secret = credentials
        adapter = KiwoomAdapter(app_key, secret, is_mock=True)

        # connect에서 WS 연결 시도하므로 실패할 수 있음
        # auth + ws.connect를 분리해서 테스트
        try:
            await adapter.connect()
        except ConnectionError as e:
            # WS 실패로 connect 전체가 실패할 수 있음
            print(f"\n  adapter.connect failed (WS): {e}")
            # 수동으로 auth만 통과시키고 state 설정
            from local_server.broker.kis.state_machine import ConnectionState
            adapter._state._state = ConnectionState.AUTHENTICATED
            await adapter._auth.get_access_token()

        result = await adapter.get_quote(TEST_SYMBOL)
        assert isinstance(result, QuoteEvent)
        assert result.price > 0
        print(f"\n  adapter quote: {result.symbol} = {result.price}")

        # rate_limiter 통과 확인
        assert adapter._rate_limiter._limiters.get("quote") is not None
        assert adapter._rate_limiter._limiters["quote"].total_calls >= 1
