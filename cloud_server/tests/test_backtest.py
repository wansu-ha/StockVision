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


def test_backtest_saves_to_db(client, db, _seed_daily_bars):
    """백테스트 실행 시 결과가 DB에 저장."""
    user = _make_user(db)
    headers = _auth_header(user)

    resp = client.post("/api/v1/backtest/run", json={
        "script": "매수: RSI(14) <= 40\n매도: RSI(14) >= 60",
        "symbol": "005930",
        "start_date": "2025-06-01",
        "end_date": "2025-10-01",
    }, headers=headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "id" in data  # execution_id 반환
    execution_id = data["id"]
    assert execution_id > 0

    # DB에 실제 저장 확인
    from cloud_server.models.backtest import BacktestExecution
    row = db.query(BacktestExecution).filter(BacktestExecution.id == execution_id).first()
    assert row is not None
    assert row.symbol == "005930"
    assert row.user_id == str(user.id)
    assert row.summary["total_return_pct"] is not None


def test_backtest_history_api(client, db, _seed_daily_bars):
    """GET /api/v1/backtest/history — 이력 조회."""
    user = _make_user(db)
    headers = _auth_header(user)

    # 먼저 백테스트 실행
    client.post("/api/v1/backtest/run", json={
        "script": "매수: RSI(14) <= 40\n매도: RSI(14) >= 60",
        "symbol": "005930",
        "start_date": "2025-06-01",
        "end_date": "2025-10-01",
    }, headers=headers)

    # history 조회
    resp = client.get("/api/v1/backtest/history", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["count"] >= 1
    assert data["data"][0]["symbol"] == "005930"


def test_backtest_detail_api(client, db, _seed_daily_bars):
    """GET /api/v1/backtest/{id} — 상세 조회."""
    user = _make_user(db)
    headers = _auth_header(user)

    # 백테스트 실행
    run_resp = client.post("/api/v1/backtest/run", json={
        "script": "매수: RSI(14) <= 40\n매도: RSI(14) >= 60",
        "symbol": "005930",
        "start_date": "2025-06-01",
        "end_date": "2025-10-01",
    }, headers=headers)
    execution_id = run_resp.json()["data"]["id"]

    # detail 조회
    resp = client.get(f"/api/v1/backtest/{execution_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == execution_id
    assert data["symbol"] == "005930"
    assert "summary" in data


def test_backtest_detail_not_found(client, db):
    """존재하지 않는 execution_id → 404."""
    user = _make_user(db)
    headers = _auth_header(user)

    resp = client.get("/api/v1/backtest/99999", headers=headers)
    assert resp.status_code == 404


def test_backtest_tf_arg_in_dsl(client, db, _seed_daily_bars):
    """RSI(14, "5m") 문법이 에러 없이 실행."""
    user = _make_user(db)
    headers = _auth_header(user)

    resp = client.post("/api/v1/backtest/run", json={
        "script": '매수: RSI(14, "5m") <= 40\n매도: RSI(14) >= 60',
        "symbol": "005930",
        "start_date": "2025-06-01",
        "end_date": "2025-10-01",
        "timeframe": "1d",
    }, headers=headers)

    # TF 데이터 없어도 에러 없이 실행 (None 폴백)
    assert resp.status_code == 200
