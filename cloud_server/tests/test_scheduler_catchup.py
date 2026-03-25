"""스케줄러 catch-up 테스트 (RM-2).

서버 재시작 시 누락 작업 보정 로직 검증.
"""
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from cloud_server.tests.conftest import _TestSession, _make_user

KST = ZoneInfo("Asia/Seoul")


@pytest.fixture()
def scheduler():
    """CollectorScheduler 인스턴스 (스케줄러 미시작)."""
    from cloud_server.collector.scheduler import CollectorScheduler
    return CollectorScheduler()


# ── 1. catch-up: 누락 작업 보정 호출 확인 ──


@pytest.mark.asyncio
async def test_catchup_calls_missed_jobs(db, scheduler):
    """DB에 오늘 데이터 없고 시각이 지났으면 보정 함수 호출."""
    fake_now = datetime(2026, 3, 25, 18, 30, tzinfo=KST)

    with patch("cloud_server.collector.scheduler.get_db_session", return_value=_TestSession()):
        scheduler.update_stock_master = AsyncMock()
        scheduler.save_daily_bars = AsyncMock()
        scheduler.collect_yfinance = AsyncMock()
        scheduler.check_data_integrity = AsyncMock()
        scheduler._run_briefing = AsyncMock()
        scheduler._run_stock_analysis = AsyncMock()

        await scheduler.catch_up_missed_jobs(_now=fake_now)

    # DB 비어있으므로 모든 작업 호출
    scheduler.update_stock_master.assert_called_once()
    scheduler.save_daily_bars.assert_called_once()
    scheduler.collect_yfinance.assert_called_once()
    scheduler.check_data_integrity.assert_called_once()
    scheduler._run_briefing.assert_called_once()
    scheduler._run_stock_analysis.assert_called_once()


# ── 2. catch-up: 이미 실행된 작업은 skip ──


@pytest.mark.asyncio
async def test_catchup_skips_already_done(db, scheduler):
    """DB에 오늘 데이터가 있으면 해당 작업 skip."""
    from cloud_server.models.market import StockMaster, DailyBar
    from cloud_server.models.briefing import MarketBriefing
    from cloud_server.models.stock_briefing import StockBriefing

    today = date(2026, 3, 25)

    # stock_master: 최근 갱신 (1시간 전)
    sm = StockMaster(symbol="005930", name="삼성전자", market="KOSPI",
                     updated_at=datetime(2026, 3, 25, 9, 30))
    db.add(sm)

    # daily_bars: 오늘 데이터 존재
    bar = DailyBar(symbol="005930", date=today, open=70000, high=71000,
                   low=69000, close=70500, volume=1000000)
    db.add(bar)

    # yfinance 인덱스 bar 존재
    from cloud_server.services.yfinance_service import DEFAULT_SYMBOLS
    for sym in DEFAULT_SYMBOLS[:2]:
        db.add(DailyBar(symbol=sym, date=today, open=100, high=101,
                        low=99, close=100, volume=5000))

    # briefing: 오늘 브리핑 존재
    briefing = MarketBriefing(
        date=today, summary="OK", sentiment="neutral",
        indices_json="{}", source="stub",
    )
    db.add(briefing)

    # stock_analysis: 오늘 분석 존재
    analysis = StockBriefing(
        symbol="005930", date=today, summary="OK",
        sentiment="neutral", source="stub",
    )
    db.add(analysis)
    db.commit()

    fake_now = datetime(2026, 3, 25, 18, 30, tzinfo=KST)

    with patch("cloud_server.collector.scheduler.get_db_session", return_value=_TestSession()):
        scheduler.update_stock_master = AsyncMock()
        scheduler.save_daily_bars = AsyncMock()
        scheduler.collect_yfinance = AsyncMock()
        scheduler.check_data_integrity = AsyncMock()
        scheduler._run_briefing = AsyncMock()
        scheduler._run_stock_analysis = AsyncMock()

        await scheduler.catch_up_missed_jobs(_now=fake_now)

    # stock_master: 최근 갱신 → skip
    scheduler.update_stock_master.assert_not_called()
    # daily_bars: 오늘 bar 존재 → skip
    scheduler.save_daily_bars.assert_not_called()
    # briefing: 오늘 브리핑 존재 → skip
    scheduler._run_briefing.assert_not_called()
    # stock_analysis: 오늘 분석 존재 → skip
    scheduler._run_stock_analysis.assert_not_called()
    # integrity_check: 항상 실행
    scheduler.check_data_integrity.assert_called_once()


# ── 3. KIS WS guard: 이미 실행 중이면 skip ──


@pytest.mark.asyncio
async def test_kis_ws_guard_skip_if_running(scheduler):
    """KIS WS가 이미 실행 중이면 start_kis_ws()는 아무것도 하지 않음."""
    mock_task = MagicMock()
    mock_task.done.return_value = False
    scheduler._listen_task = mock_task

    await scheduler.start_kis_ws()

    # kis_collector가 None인 채로 유지 (guard가 작동)
    assert scheduler.kis_collector is None
