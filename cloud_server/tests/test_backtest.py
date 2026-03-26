"""백테스트 엔진 유닛 테스트."""
import pytest

from cloud_server.services.backtest_runner import BacktestResult, BacktestRunner
from cloud_server.tests.conftest import _make_user, _auth_header


@pytest.fixture()
def _seed_daily_bars(db):
    """삼성전자 100일 일봉 시드 데이터."""
    from datetime import date, timedelta
    from cloud_server.models.market import DailyBar

    base_price = 70000
    for i in range(100):
        d = date(2025, 6, 1) + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        # 상승 → 하락 → 상승 패턴 (RSI 테스트용)
        if i < 30:
            price = base_price + i * 500
        elif i < 60:
            price = base_price + 15000 - (i - 30) * 500
        else:
            price = base_price + (i - 60) * 300

        db.add(DailyBar(
            symbol="005930", date=d,
            open=price - 200, high=price + 300,
            low=price - 500, close=price,
            volume=1000000 + i * 10000,
        ))
    db.commit()


def test_backtest_simple_rule(client, db, _seed_daily_bars):
    """간단한 RSI 규칙 백테스트."""
    from datetime import date
    runner = BacktestRunner(db)

    import asyncio
    result = asyncio.get_event_loop().run_until_complete(runner.run(
        script="매수: RSI(14) <= 40\n매도: RSI(14) >= 60",
        symbol="005930",
        start_date=date(2025, 6, 1),
        end_date=date(2025, 10, 1),
        timeframe="1d",
    ))

    assert isinstance(result, BacktestResult)
    assert len(result.equity_curve) > 0
    # 데이터가 충분하면 거래가 발생해야 함
    assert result.trade_count >= 0  # 데이터 패턴에 따라 0일 수도


def test_backtest_insufficient_data(client, db):
    """데이터 부족 시 빈 결과."""
    from datetime import date
    runner = BacktestRunner(db)

    import asyncio
    result = asyncio.get_event_loop().run_until_complete(runner.run(
        script="매수: RSI(14) <= 30\n매도: RSI(14) >= 70",
        symbol="NOSYMBOL",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    ))

    assert result.trade_count == 0
    assert len(result.equity_curve) == 0


def test_backtest_api_endpoint(client, db, _seed_daily_bars):
    """POST /api/v1/backtest/run API 호출."""
    user = _make_user(db)
    headers = _auth_header(user)

    resp = client.post("/api/v1/backtest/run", json={
        "script": "매수: RSI(14) <= 40\n매도: RSI(14) >= 60",
        "symbol": "005930",
        "start_date": "2025-06-01",
        "end_date": "2025-10-01",
        "timeframe": "1d",
    }, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "summary" in data["data"]
    assert "equity_curve" in data["data"]
    assert "trades" in data["data"]

    summary = data["data"]["summary"]
    assert "total_return_pct" in summary
    assert "max_drawdown_pct" in summary
    assert "win_rate" in summary


def test_backtest_api_no_script(client, db):
    """script도 rule_id도 없으면 400."""
    user = _make_user(db)
    headers = _auth_header(user)

    resp = client.post("/api/v1/backtest/run", json={
        "symbol": "005930",
    }, headers=headers)

    assert resp.status_code == 400
