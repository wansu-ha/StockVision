"""PositionState 단위 테스트."""
from datetime import date, datetime, timedelta
import pytest
from local_server.engine.position_state import PositionState


def test_initial_state():
    ps = PositionState(symbol="005930")
    assert not ps.is_holding
    assert ps.entry_price == 0.0
    assert ps.total_qty == 0
    assert ps.bars_held == 0
    assert ps.days_held == 0
    assert ps.pnl_high == 0.0


def test_buy_creates_position():
    ps = PositionState(symbol="005930")
    ps.record_buy(10_000, 10)
    assert ps.is_holding
    assert ps.total_qty == 10
    assert ps.entry_price == 10_000.0
    assert ps.highest_price == 10_000.0
    assert ps.bars_held == 1
    assert ps.days_held == 1


def test_dca_weighted_avg():
    ps = PositionState(symbol="005930")
    ps.record_buy(10_000, 10)  # 비용 100,000
    ps.record_buy(8_000, 10)   # 비용 80,000 → 합산 180,000 / 20 = 9,000
    assert ps.total_qty == 20
    assert ps.entry_price == pytest.approx(9_000.0)
    assert ps.highest_price == 10_000.0  # 최고가는 첫 매수가


def test_sell_partial():
    ps = PositionState(symbol="005930")
    ps.record_buy(10_000, 10)
    ps.record_sell(4)
    assert ps.total_qty == 6
    assert ps.is_holding
    # 부분 청산 후 entry_price는 변경 없음
    assert ps.entry_price == pytest.approx(10_000.0)


def test_sell_all_resets():
    ps = PositionState(symbol="005930")
    ps.record_buy(10_000, 10)
    ps.record_execution(0)
    ps.func_state["k"] = 1
    ps.record_sell(10)
    assert not ps.is_holding
    assert ps.entry_price == 0.0
    assert ps.total_qty == 0
    assert ps.bars_held == 0
    assert ps.days_held == 0
    assert ps.execution_counts == {}
    assert ps.func_state == {}


def test_update_cycle():
    ps = PositionState(symbol="005930")
    ps.record_buy(10_000, 10)
    assert ps.bars_held == 1
    ps.update_cycle(11_000)
    assert ps.bars_held == 2
    assert ps.highest_price == 11_000.0
    ps.update_cycle(9_000)
    assert ps.bars_held == 3
    assert ps.highest_price == 11_000.0  # 고점은 떨어지지 않음


def test_pnl_high_tracking():
    ps = PositionState(symbol="005930")
    ps.record_buy(10_000, 10)
    ps.update_cycle(11_000)  # +10%
    assert ps.pnl_high == pytest.approx(10.0)
    ps.update_cycle(9_000)   # -10% — pnl_high 유지
    assert ps.pnl_high == pytest.approx(10.0)
    ps.update_cycle(12_000)  # +20%
    assert ps.pnl_high == pytest.approx(20.0)


def test_to_context():
    ps = PositionState(symbol="005930")
    ps.record_buy(10_000, 10)
    ps.update_cycle(11_000)
    ctx = ps.to_context(11_000)
    assert ctx["수익률"] == pytest.approx(10.0)
    assert ctx["보유수량"] == 10
    assert ctx["진입가"] == 10_000.0
    assert ctx["수익률고점"] == pytest.approx(10.0)
    assert "고점 대비" in ctx
    assert ctx["보유봉"] == 2


def test_reentry_after_full_sell():
    ps = PositionState(symbol="005930")
    ps.record_buy(10_000, 10)
    ps.record_sell(10)
    assert not ps.is_holding
    # 재진입
    ps.record_buy(9_000, 5)
    assert ps.is_holding
    assert ps.entry_price == 9_000.0
    assert ps.total_qty == 5
    assert ps.bars_held == 1


def test_execution_count():
    ps = PositionState(symbol="005930")
    ps.record_buy(10_000, 10)
    ps.record_execution(0)
    ps.record_execution(0)
    ps.record_execution(1)
    assert ps.execution_counts[0] == 2
    assert ps.execution_counts[1] == 1
    assert ps.execution_counts.get(2) is None


def test_update_day():
    ps = PositionState(symbol="005930")
    today = date(2026, 3, 29)
    at = datetime(2026, 3, 29, 9, 30)
    ps.record_buy(10_000, 10, at=at)
    assert ps.days_held == 1
    # 같은 날 — 증가 없음
    ps.update_day(today)
    assert ps.days_held == 1
    # 다음 날
    ps.update_day(date(2026, 3, 30))
    assert ps.days_held == 2
    assert ps.last_trade_date == date(2026, 3, 30)
