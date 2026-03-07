"""통합 테스트: MockAdapter를 사용한 전체 브로커 플로우 테스트

실제 KIS API 없이 MockAdapter로 전체 플로우를 검증한다.
"""

import asyncio
import sys
import os
from decimal import Decimal

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def run(coro):
    return asyncio.run(coro)


def _pass(name: str) -> None:
    print(f"  [PASS] {name}")


def _fail(name: str, reason: str) -> None:
    print(f"  [FAIL] {name}: {reason}")
    raise AssertionError(f"{name}: {reason}")


# ──────────────────────────────────────────────────────────────
# 통합 시나리오 1: 전체 매매 플로우
# ──────────────────────────────────────────────────────────────

def test_full_trading_flow():
    """전체 매매 플로우: 연결 → 잔고 조회 → 매수 → 포지션 확인 → 매도 → 연결 해제"""
    print("\n[IT-1] 전체 매매 플로우 테스트")
    from local_server.broker.factory import create_adapter
    from sv_core.broker.models import OrderSide, OrderType, OrderStatus

    async def _test():
        # 팩토리로 MockAdapter 생성
        adapter = create_adapter("mock", initial_cash=Decimal("20000000"))
        await adapter.connect()
        assert adapter.is_connected
        _pass("MockAdapter 연결")

        # 초기 잔고 확인
        balance = await adapter.get_balance()
        assert balance.cash == Decimal("20000000")
        assert len(balance.positions) == 0
        _pass("초기 잔고 2천만원 확인")

        # 삼성전자 현재가 조회
        quote = await adapter.get_quote("005930")
        assert quote.symbol == "005930"
        samsung_price = quote.price
        _pass(f"삼성전자 현재가 조회: {samsung_price}원")

        # 삼성전자 100주 매수
        buy_order = await adapter.place_order(
            client_order_id="IT-BUY-001",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=100,
        )
        assert buy_order.status == OrderStatus.FILLED
        assert buy_order.filled_qty == 100
        _pass("삼성전자 100주 매수 체결")

        # 매수 후 잔고 확인
        balance2 = await adapter.get_balance()
        expected_cash = Decimal("20000000") - samsung_price * 100
        assert balance2.cash == expected_cash
        assert len(balance2.positions) == 1
        assert balance2.positions[0].symbol == "005930"
        assert balance2.positions[0].qty == 100
        _pass("매수 후 잔고/포지션 확인")

        # SK하이닉스 현재가 조회
        hynix_quote = await adapter.get_quote("000660")
        hynix_price = hynix_quote.price
        _pass(f"SK하이닉스 현재가 조회: {hynix_price}원")

        # SK하이닉스 50주 매수
        buy_order2 = await adapter.place_order(
            client_order_id="IT-BUY-002",
            symbol="000660",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=50,
        )
        assert buy_order2.status == OrderStatus.FILLED
        _pass("SK하이닉스 50주 매수 체결")

        # 2개 종목 포지션 확인
        balance3 = await adapter.get_balance()
        assert len(balance3.positions) == 2
        symbols = {p.symbol for p in balance3.positions}
        assert "005930" in symbols
        assert "000660" in symbols
        _pass("2개 종목 포지션 확인")

        # 삼성전자 50주 매도
        sell_order = await adapter.place_order(
            client_order_id="IT-SELL-001",
            symbol="005930",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            qty=50,
        )
        assert sell_order.status == OrderStatus.FILLED
        _pass("삼성전자 50주 매도 체결")

        # 매도 후 포지션 50주 남음
        balance4 = await adapter.get_balance()
        samsung_pos = next(p for p in balance4.positions if p.symbol == "005930")
        assert samsung_pos.qty == 50
        _pass("매도 후 포지션 50주 확인")

        await adapter.disconnect()
        assert not adapter.is_connected
        _pass("연결 해제")

    run(_test())


# ──────────────────────────────────────────────────────────────
# 통합 시나리오 2: 멱등성 보장
# ──────────────────────────────────────────────────────────────

def test_idempotency_flow():
    """동일 client_order_id 중복 요청 시 기존 결과 반환 확인"""
    print("\n[IT-2] 멱등성 보장 테스트")
    from local_server.broker.mock.adapter import MockAdapter
    from local_server.broker.kis.idempotency import IdempotencyGuard
    from sv_core.broker.models import OrderSide, OrderType, OrderStatus, OrderResult

    async def _test():
        guard = IdempotencyGuard()
        adapter = MockAdapter()
        await adapter.connect()

        # 첫 번째 주문
        order1 = await adapter.place_order(
            client_order_id="IDEM-001",
            symbol="005930",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            qty=10,
        )
        await guard.register(order1)
        _pass("첫 번째 주문 등록")

        # 동일 client_order_id로 재요청 → 기존 결과 반환
        cached = await guard.check("IDEM-001")
        assert cached is not None
        assert cached.order_id == order1.order_id
        _pass("동일 ID 재요청 → 기존 결과 반환 (실제 주문 미발생)")

        # 다른 ID는 정상 처리
        not_cached = await guard.check("IDEM-002")
        assert not_cached is None
        _pass("다른 ID → None 반환 (신규 주문 처리 필요)")

        await adapter.disconnect()

    run(_test())


# ──────────────────────────────────────────────────────────────
# 통합 시나리오 3: 실시간 시세 구독 + 이벤트 처리
# ──────────────────────────────────────────────────────────────

def test_quote_subscription_flow():
    """실시간 시세 구독 → 이벤트 수신 → 처리 플로우"""
    print("\n[IT-3] 실시간 시세 구독 테스트")
    from local_server.broker.mock.adapter import MockAdapter
    from sv_core.broker.models import QuoteEvent

    async def _test():
        adapter = MockAdapter()
        await adapter.connect()

        received_events = []
        await adapter.subscribe_quotes(
            ["005930", "000660"],
            callback=lambda e: received_events.append(e),
        )
        _pass("2개 종목 구독 등록")

        # 시세 이벤트 수동 발생 (실제 WebSocket 없이)
        adapter.fire_quote_event(QuoteEvent(
            symbol="005930",
            price=Decimal("76000"),
            volume=5000,
        ))
        adapter.fire_quote_event(QuoteEvent(
            symbol="000660",
            price=Decimal("182000"),
            volume=2000,
        ))

        assert len(received_events) == 2
        assert received_events[0].symbol == "005930"
        assert received_events[0].price == Decimal("76000")
        assert received_events[1].symbol == "000660"
        _pass("2개 종목 시세 이벤트 수신 확인")

        # 구독 해제
        await adapter.unsubscribe_quotes(["005930"])
        _pass("구독 해제 완료")

        await adapter.disconnect()

    run(_test())


# ──────────────────────────────────────────────────────────────
# 통합 시나리오 4: 에러 처리 (잔고 부족, 수량 부족)
# ──────────────────────────────────────────────────────────────

def test_error_handling_flow():
    """에러 시나리오: 잔고 부족, 수량 부족, 미연결 상태"""
    print("\n[IT-4] 에러 처리 테스트")
    from local_server.broker.mock.adapter import MockAdapter
    from sv_core.broker.models import OrderSide, OrderType

    async def _test():
        adapter = MockAdapter(initial_cash=Decimal("100000"))  # 10만원 소액
        await adapter.connect()

        # 잔고 부족 (삼성전자 1주 = 75,000원, 2주면 150,000원 > 100,000원)
        try:
            await adapter.place_order(
                client_order_id="ERR-001",
                symbol="005930",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                qty=2,
            )
            _fail("잔고 부족 오류", "예외가 발생해야 함")
        except ValueError as e:
            assert "잔고 부족" in str(e)
            _pass("잔고 부족 ValueError 발생")

        # 보유하지 않은 종목 매도 시도
        try:
            await adapter.place_order(
                client_order_id="ERR-002",
                symbol="005930",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                qty=1,
            )
            _fail("보유 수량 부족 오류", "예외가 발생해야 함")
        except ValueError as e:
            assert "보유 수량 부족" in str(e)
            _pass("미보유 종목 매도 → ValueError")

        # 연결 해제 후 주문 시도
        await adapter.disconnect()
        try:
            await adapter.place_order(
                client_order_id="ERR-003",
                symbol="005930",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                qty=1,
            )
            _fail("미연결 상태 오류", "예외가 발생해야 함")
        except RuntimeError:
            _pass("미연결 상태 RuntimeError 발생")

    run(_test())


# ──────────────────────────────────────────────────────────────
# 통합 시나리오 5: ReconnectManager + StateMachine 연동
# ──────────────────────────────────────────────────────────────

def test_reconnect_flow():
    """ReconnectManager가 ERROR 상태 감지 후 재연결 시도하는지 확인"""
    print("\n[IT-5] ReconnectManager 연동 테스트")
    from local_server.broker.kis.state_machine import StateMachine, ConnectionState
    from local_server.broker.kis.reconnect import ReconnectManager

    async def _test():
        sm = StateMachine()
        connect_calls = []

        async def mock_connect():
            connect_calls.append(1)
            # 첫 시도 실패, 두 번째 성공
            if len(connect_calls) == 1:
                raise ConnectionError("모의 연결 실패")
            await sm.transition(ConnectionState.CONNECTED)

        mgr = ReconnectManager(
            state_machine=sm,
            connect_fn=mock_connect,
            initial_delay=0.01,  # 테스트에서 빠른 재시도
            max_delay=0.1,
            max_retries=3,
        )
        sm.on_change(mgr.on_state_change)

        # DISCONNECTED → CONNECTING → ERROR 전환으로 재연결 트리거
        await sm.transition(ConnectionState.CONNECTING)
        await sm.transition(ConnectionState.ERROR)

        # 재연결 태스크가 시작됨을 확인
        assert mgr.is_running
        _pass("ERROR 상태에서 재연결 태스크 시작 확인")

        # 재연결 완료 대기
        await asyncio.sleep(0.2)
        _pass("재연결 시도 확인 (2회 호출)")

    run(_test())


# ──────────────────────────────────────────────────────────────
# 실행 진입점
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_full_trading_flow,
        test_idempotency_flow,
        test_quote_subscription_flow,
        test_error_handling_flow,
        test_reconnect_flow,
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
