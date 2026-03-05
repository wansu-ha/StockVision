"""유닛 테스트: sv_core 모델, RateLimiter, StateMachine, IdempotencyGuard, ErrorClassifier, MockAdapter"""

import asyncio
import sys
import os
from decimal import Decimal
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ──────────────────────────────────────────────────────────────
# 테스트 도우미
# ──────────────────────────────────────────────────────────────

def run(coro):
    """asyncio 코루틴을 동기적으로 실행한다."""
    return asyncio.get_event_loop().run_until_complete(coro)


def test_pass(name: str) -> None:
    print(f"  [PASS] {name}")


def test_fail(name: str, reason: str) -> None:
    print(f"  [FAIL] {name}: {reason}")
    raise AssertionError(f"{name}: {reason}")


# ──────────────────────────────────────────────────────────────
# 1. sv_core 모델 테스트
# ──────────────────────────────────────────────────────────────

def test_models():
    print("\n[1] sv_core.broker.models 테스트")
    from sv_core.broker.models import (
        OrderSide, OrderType, OrderStatus, ErrorCategory,
        OrderResult, BalanceResult, Position, QuoteEvent,
    )

    # Enum 값 확인
    assert OrderSide.BUY == "BUY"
    assert OrderSide.SELL == "SELL"
    test_pass("OrderSide enum 값 확인")

    assert OrderType.MARKET == "MARKET"
    assert OrderType.LIMIT == "LIMIT"
    test_pass("OrderType enum 값 확인")

    assert OrderStatus.FILLED == "FILLED"
    assert OrderStatus.CANCELLED == "CANCELLED"
    test_pass("OrderStatus enum 값 확인")

    assert ErrorCategory.TRANSIENT == "TRANSIENT"
    assert ErrorCategory.PERMANENT == "PERMANENT"
    assert ErrorCategory.AUTH == "AUTH"
    assert ErrorCategory.RATE_LIMIT == "RATE_LIMIT"
    test_pass("ErrorCategory enum 값 확인")

    # OrderResult 생성
    order = OrderResult(
        order_id="ORD001",
        client_order_id="CLI001",
        symbol="005930",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        qty=10,
        limit_price=None,
        status=OrderStatus.SUBMITTED,
    )
    assert order.filled_qty == 0
    assert order.raw == {}
    test_pass("OrderResult 기본값 확인")

    # BalanceResult 생성
    balance = BalanceResult(
        cash=Decimal("5000000"),
        total_eval=Decimal("10000000"),
    )
    assert balance.positions == []
    test_pass("BalanceResult 기본값 확인")

    # QuoteEvent 생성
    quote = QuoteEvent(
        symbol="005930",
        price=Decimal("75000"),
        volume=1000,
    )
    assert quote.bid_price is None
    assert quote.timestamp is None
    test_pass("QuoteEvent 기본값 확인")


# ──────────────────────────────────────────────────────────────
# 2. BrokerAdapter ABC 인터페이스 확인
# ──────────────────────────────────────────────────────────────

def test_broker_adapter_abc():
    print("\n[2] BrokerAdapter ABC 테스트")
    from sv_core.broker.base import BrokerAdapter

    # 추상 클래스 직접 인스턴스화 불가 확인
    try:
        BrokerAdapter()  # type: ignore
        test_fail("ABC 인스턴스화 불가", "예외가 발생해야 함")
    except TypeError:
        test_pass("ABC 직접 인스턴스화 불가 확인")

    # 필수 메서드 존재 확인
    abstract_methods = getattr(BrokerAdapter, "__abstractmethods__", set())
    expected = {
        "connect", "disconnect", "is_connected",
        "get_balance", "get_quote", "subscribe_quotes", "unsubscribe_quotes",
        "place_order", "cancel_order", "get_open_orders",
    }
    for method in expected:
        assert method in abstract_methods, f"{method} 누락"
    test_pass("BrokerAdapter 추상 메서드 10개 확인")


# ──────────────────────────────────────────────────────────────
# 3. RateLimiter 테스트
# ──────────────────────────────────────────────────────────────

def test_rate_limiter():
    print("\n[3] RateLimiter 테스트")
    from local_server.broker.kiwoom.rate_limiter import RateLimiter, MultiEndpointRateLimiter

    async def _test():
        # 기본 생성
        limiter = RateLimiter(calls_per_second=5)
        assert limiter.total_calls == 0
        test_pass("RateLimiter 초기화")

        # 제한 내 호출 즉시 반환
        for _ in range(5):
            await limiter.acquire()
        assert limiter.total_calls == 5
        test_pass("5회 호출 성공 (한도 내)")

        # MultiEndpointRateLimiter
        multi = MultiEndpointRateLimiter(default_cps=10)
        multi.set_limit("order", 5)
        await multi.acquire("order")
        await multi.acquire("quote")
        test_pass("MultiEndpointRateLimiter 엔드포인트별 제한")

    run(_test())


# ──────────────────────────────────────────────────────────────
# 4. StateMachine 테스트
# ──────────────────────────────────────────────────────────────

def test_state_machine():
    print("\n[4] StateMachine 테스트")
    from local_server.broker.kiwoom.state_machine import (
        StateMachine, ConnectionState, InvalidStateTransitionError,
    )

    async def _test():
        sm = StateMachine()
        assert sm.state == ConnectionState.DISCONNECTED
        test_pass("초기 상태 DISCONNECTED 확인")

        # 정상 전환
        await sm.transition(ConnectionState.CONNECTING)
        await sm.transition(ConnectionState.CONNECTED)
        await sm.transition(ConnectionState.AUTHENTICATED)
        assert sm.state == ConnectionState.AUTHENTICATED
        assert sm.is_operational()
        test_pass("DISCONNECTED → CONNECTING → CONNECTED → AUTHENTICATED 정상 전환")

        # 잘못된 전환
        try:
            await sm.transition(ConnectionState.CONNECTING)  # AUTHENTICATED에서 CONNECTING 불가
            test_fail("잘못된 전환 거부", "예외가 발생해야 함")
        except InvalidStateTransitionError:
            test_pass("잘못된 전환 거부 확인")

        # 콜백 등록
        changes = []
        sm.on_change(lambda old, new: changes.append((old, new)))
        await sm.transition(ConnectionState.SUBSCRIBED)
        assert len(changes) == 1
        assert changes[0][1] == ConnectionState.SUBSCRIBED
        test_pass("상태 변경 콜백 호출 확인")

        # 강제 초기화
        sm.reset()
        assert sm.state == ConnectionState.DISCONNECTED
        test_pass("강제 초기화(reset) 확인")

    run(_test())


# ──────────────────────────────────────────────────────────────
# 5. IdempotencyGuard 테스트
# ──────────────────────────────────────────────────────────────

def test_idempotency_guard():
    print("\n[5] IdempotencyGuard 테스트")
    from local_server.broker.kiwoom.idempotency import IdempotencyGuard
    from sv_core.broker.models import (
        OrderResult, OrderSide, OrderType, OrderStatus,
    )

    async def _test():
        guard = IdempotencyGuard()
        assert guard.record_count == 0

        # 미등록 ID 조회 → None
        result = await guard.check("CLI001")
        assert result is None
        test_pass("미등록 ID → None 반환")

        # 주문 등록 후 재조회 → 기존 결과 반환
        order = OrderResult(
            order_id="ORD001",
            client_order_id="CLI001",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=10,
            limit_price=None,
            status=OrderStatus.SUBMITTED,
        )
        await guard.register(order)
        assert guard.record_count == 1

        cached = await guard.check("CLI001")
        assert cached is not None
        assert cached.order_id == "ORD001"
        test_pass("등록된 ID → 기존 OrderResult 반환")

        # 다른 ID는 None
        result2 = await guard.check("CLI002")
        assert result2 is None
        test_pass("다른 ID는 영향 없음")

    run(_test())


# ──────────────────────────────────────────────────────────────
# 6. ErrorClassifier 테스트
# ──────────────────────────────────────────────────────────────

def test_error_classifier():
    print("\n[6] ErrorClassifier 테스트")
    from local_server.broker.kiwoom.error_classifier import ErrorClassifier
    from sv_core.broker.models import ErrorCategory
    import httpx

    clf = ErrorClassifier()

    # API 응답 분류
    normal = clf.classify_api_response({"rt_cd": "0", "msg_cd": ""})
    assert normal == ErrorCategory.TRANSIENT  # 정상은 TRANSIENT (호출자가 무시)
    test_pass("정상 응답 → TRANSIENT")

    perm = clf.classify_api_response({"rt_cd": "1", "msg_cd": "OPSQ0009"})
    assert perm == ErrorCategory.PERMANENT
    test_pass("주문 수량 오류 → PERMANENT")

    auth = clf.classify_api_response({"rt_cd": "1", "msg_cd": "EGW00123"})
    assert auth == ErrorCategory.AUTH
    test_pass("토큰 만료 → AUTH")

    rl = clf.classify_api_response({"rt_cd": "1", "msg_cd": "EGW00201"})
    assert rl == ErrorCategory.RATE_LIMIT
    test_pass("속도 제한 → RATE_LIMIT")

    # 재시도 가능 여부
    assert clf.is_retryable(ErrorCategory.TRANSIENT)
    assert clf.is_retryable(ErrorCategory.RATE_LIMIT)
    assert not clf.is_retryable(ErrorCategory.PERMANENT)
    assert not clf.is_retryable(ErrorCategory.AUTH)
    test_pass("is_retryable 분류 확인")

    # 재인증 필요 여부
    assert clf.needs_reauth(ErrorCategory.AUTH)
    assert not clf.needs_reauth(ErrorCategory.TRANSIENT)
    test_pass("needs_reauth 분류 확인")

    # 일반 예외 분류
    import httpx
    timeout_exc = httpx.TimeoutException("timeout")
    cat = clf.classify_exception(timeout_exc)
    assert cat == ErrorCategory.TRANSIENT
    test_pass("TimeoutException → TRANSIENT")


# ──────────────────────────────────────────────────────────────
# 7. MockAdapter 테스트
# ──────────────────────────────────────────────────────────────

def test_mock_adapter():
    print("\n[7] MockAdapter 테스트")
    from local_server.broker.mock.adapter import MockAdapter
    from sv_core.broker.models import OrderSide, OrderType, OrderStatus, QuoteEvent

    async def _test():
        adapter = MockAdapter(initial_cash=Decimal("10000000"))

        # 미연결 상태에서 오류
        try:
            await adapter.get_balance()
            test_fail("미연결 오류", "예외가 발생해야 함")
        except RuntimeError:
            test_pass("미연결 상태 오류 확인")

        # 연결
        await adapter.connect()
        assert adapter.is_connected
        test_pass("connect() 성공")

        # 잔고 조회
        balance = await adapter.get_balance()
        assert balance.cash == Decimal("10000000")
        assert balance.positions == []
        test_pass("초기 잔고 조회")

        # 현재가 조회
        quote = await adapter.get_quote("005930")
        assert quote.symbol == "005930"
        assert quote.price == Decimal("75000")
        test_pass("현재가 조회 (기본값)")

        # 매수 주문
        order = await adapter.place_order(
            client_order_id="CLI001",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=10,
        )
        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == 10
        test_pass("매수 주문 즉시 체결")

        # 잔고 차감 확인
        balance2 = await adapter.get_balance()
        expected_cash = Decimal("10000000") - Decimal("75000") * 10
        assert balance2.cash == expected_cash
        assert len(balance2.positions) == 1
        assert balance2.positions[0].symbol == "005930"
        assert balance2.positions[0].qty == 10
        test_pass("매수 후 잔고/포지션 갱신 확인")

        # 잔고 부족 오류
        try:
            await adapter.place_order(
                client_order_id="CLI002",
                symbol="005930",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                qty=100000,  # 엄청 많이
            )
            test_fail("잔고 부족 오류", "예외가 발생해야 함")
        except ValueError:
            test_pass("잔고 부족 ValueError 확인")

        # 매도 주문
        sell_order = await adapter.place_order(
            client_order_id="CLI003",
            symbol="005930",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            qty=5,
        )
        assert sell_order.status == OrderStatus.FILLED
        test_pass("매도 주문 즉시 체결")

        # 포지션 5주 남음
        balance3 = await adapter.get_balance()
        assert balance3.positions[0].qty == 5
        test_pass("매도 후 포지션 수량 감소 확인")

        # 가격 변경 후 시세 확인
        adapter.set_price("005930", Decimal("80000"))
        quote2 = await adapter.get_quote("005930")
        assert quote2.price == Decimal("80000")
        test_pass("set_price() 가격 변경 확인")

        # 구독
        received = []
        await adapter.subscribe_quotes(["005930"], lambda e: received.append(e))
        adapter.fire_quote_event(QuoteEvent(
            symbol="005930",
            price=Decimal("81000"),
            volume=500,
        ))
        assert len(received) == 1
        assert received[0].price == Decimal("81000")
        test_pass("fire_quote_event() 콜백 호출 확인")

        # 보유 수량 부족 오류
        try:
            await adapter.place_order(
                client_order_id="CLI004",
                symbol="005930",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                qty=100,
            )
            test_fail("보유 수량 부족 오류", "예외가 발생해야 함")
        except ValueError:
            test_pass("보유 수량 부족 ValueError 확인")

        # reset
        adapter.reset()
        balance4 = await adapter.get_balance()
        assert balance4.cash == Decimal("10000000")
        assert balance4.positions == []
        test_pass("reset() 후 상태 초기화 확인")

        # 연결 해제
        await adapter.disconnect()
        assert not adapter.is_connected
        test_pass("disconnect() 성공")

    run(_test())


# ──────────────────────────────────────────────────────────────
# 8. AdapterFactory 테스트
# ──────────────────────────────────────────────────────────────

def test_adapter_factory():
    print("\n[8] AdapterFactory 테스트")
    from local_server.broker.factory import AdapterFactory, create_adapter
    from local_server.broker.mock.adapter import MockAdapter

    # mock 타입 생성
    adapter = AdapterFactory.create("mock")
    assert isinstance(adapter, MockAdapter)
    test_pass("AdapterFactory.create('mock') → MockAdapter")

    # initial_cash 전달
    adapter2 = AdapterFactory.create("mock", initial_cash=Decimal("5000000"))
    assert isinstance(adapter2, MockAdapter)
    test_pass("AdapterFactory.create('mock', initial_cash=5000000)")

    # 편의 함수
    adapter3 = create_adapter("mock")
    assert isinstance(adapter3, MockAdapter)
    test_pass("create_adapter('mock') 편의 함수")

    # 알 수 없는 타입 오류
    try:
        AdapterFactory.create("unknown")
        test_fail("알 수 없는 타입 오류", "예외가 발생해야 함")
    except ValueError:
        test_pass("알 수 없는 broker_type → ValueError")

    # kiwoom 환경변수 누락 오류
    try:
        AdapterFactory.create("kiwoom")
        test_fail("환경변수 누락 오류", "예외가 발생해야 함")
    except EnvironmentError:
        test_pass("키움 환경변수 누락 → EnvironmentError")


# ──────────────────────────────────────────────────────────────
# 9. Reconciler 테스트 (인메모리)
# ──────────────────────────────────────────────────────────────

def test_reconciler():
    print("\n[9] Reconciler 테스트")
    from local_server.broker.kiwoom.reconciler import Reconciler, RECONCILE_ORPHAN
    from sv_core.broker.models import OrderResult, OrderSide, OrderType, OrderStatus
    from unittest.mock import AsyncMock

    async def _test():
        # 미체결 조회를 모킹
        mock_order_client = AsyncMock()
        mock_order_client.get_open_orders.return_value = []  # 서버에 미체결 없음

        reconciler = Reconciler(mock_order_client, interval=999.0)

        # 주문 등록
        order = OrderResult(
            order_id="ORD001",
            client_order_id="CLI001",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=10,
            limit_price=None,
            status=OrderStatus.SUBMITTED,
        )
        reconciler.register_order(order)
        assert reconciler.local_order_count == 1
        test_pass("주문 등록 확인")

        # 대사 실행 → 서버에 없으니 ORPHAN
        events = await reconciler.reconcile_once()
        assert len(events) == 1
        assert events[0].event_type == RECONCILE_ORPHAN
        test_pass("ORPHAN 이벤트 감지 확인")

        # ORPHAN 후 상태가 FILLED로 갱신됨
        assert reconciler._local_orders["ORD001"].status == OrderStatus.FILLED
        test_pass("ORPHAN 주문 → FILLED로 자동 갱신")

        # 이벤트 콜백
        received_events = []
        reconciler.on_event(lambda e: received_events.append(e))
        reconciler.register_order(OrderResult(
            order_id="ORD002",
            client_order_id="CLI002",
            symbol="000660",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            qty=5,
            limit_price=Decimal("180000"),
            status=OrderStatus.SUBMITTED,
        ))
        await reconciler.reconcile_once()
        assert len(received_events) == 1
        test_pass("이벤트 콜백 호출 확인")

    run(_test())


# ──────────────────────────────────────────────────────────────
# 실행 진입점
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_models,
        test_broker_adapter_abc,
        test_rate_limiter,
        test_state_machine,
        test_idempotency_guard,
        test_error_classifier,
        test_mock_adapter,
        test_adapter_factory,
        test_reconciler,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  [ERROR] {test_fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            import traceback
            print(f"  [ERROR] {test_fn.__name__}: {type(e).__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"결과: {passed}개 통과, {failed}개 실패")
    sys.exit(0 if failed == 0 else 1)
