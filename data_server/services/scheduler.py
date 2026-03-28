"""데이터 수집 스케줄러."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from data_server.core.config import settings

logger = logging.getLogger(__name__)


class DataScheduler:
    """데이터 수집 스케줄 관리."""

    def __init__(self):
        self._scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    def start(self) -> None:
        # 매일 장 마감 후 일봉 저장
        self._scheduler.add_job(
            save_daily_bars,
            CronTrigger(hour=settings.COLLECTOR_DAILY_SAVE_HOUR, minute=0),
            id="save_daily_bars",
            replace_existing=True,
        )
        # 매일 종목 마스터 갱신
        self._scheduler.add_job(
            update_stock_master,
            CronTrigger(hour=settings.COLLECTOR_MASTER_UPDATE_HOUR, minute=0),
            id="update_stock_master",
            replace_existing=True,
        )
        # yfinance 보조 수집 (해외 지수, 환율)
        self._scheduler.add_job(
            collect_yfinance_indices,
            CronTrigger(hour=settings.COLLECTOR_YFINANCE_HOUR, minute=0),
            id="collect_yfinance",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("데이터 스케줄러 시작")

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info("데이터 스케줄러 종료")


scheduler = DataScheduler()


# ── 스케줄 작업 ─────────────────────────────────────────────────


async def save_daily_bars() -> None:
    """주요 종목 일봉 갱신 (yfinance)."""
    import yfinance as yf
    from data_server.core.database import get_db_session
    from data_server.services.market_repository import MarketRepository
    from data_server.models.market import StockMaster

    logger.info("일봉 갱신 시작")
    db = get_db_session()
    try:
        symbols = [s.symbol for s in db.query(StockMaster).filter(
            StockMaster.is_active.is_(True),
        ).all()]

        repo = MarketRepository(db)
        today = date.today()
        start = today - timedelta(days=7)  # 최근 1주 갱신

        for symbol in symbols:
            try:
                ticker_symbol = _to_yf(symbol)
                ticker = yf.Ticker(ticker_symbol)
                hist = ticker.history(start=str(start), end=str(today))
                for idx, row in hist.iterrows():
                    bar_date = idx.date() if hasattr(idx, "date") else idx
                    repo.save_daily_bar(symbol, bar_date, {
                        "open": int(row["Open"]) if row["Open"] else None,
                        "high": int(row["High"]) if row["High"] else None,
                        "low": int(row["Low"]) if row["Low"] else None,
                        "close": int(row["Close"]) if row["Close"] else None,
                        "volume": int(row["Volume"]) if row["Volume"] else None,
                    })
            except Exception as e:
                logger.warning("일봉 갱신 실패 %s: %s", symbol, e)

        logger.info("일봉 갱신 완료: %d종목", len(symbols))
    finally:
        db.close()


async def update_stock_master() -> None:
    """종목 마스터 갱신 — 향후 KRX/공공데이터포털 연동."""
    logger.info("종목 마스터 갱신 — 미구현 (기존 데이터 유지)")
    # TODO: 공공데이터포털 API로 종목 목록 갱신


async def collect_yfinance_indices() -> None:
    """해외 지수/환율 일봉 수집."""
    import yfinance as yf
    from data_server.core.database import get_db_session
    from data_server.services.market_repository import MarketRepository

    indices = ["^KS11", "^KQ11", "^GSPC", "^DJI", "^IXIC", "USDKRW=X"]
    logger.info("yfinance 지수/환율 수집 시작")

    db = get_db_session()
    try:
        repo = MarketRepository(db)
        today = date.today()
        start = today - timedelta(days=7)

        for symbol in indices:
            try:
                db_symbol = symbol.replace("=X", "")  # USDKRW=X → USDKRW
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=str(start), end=str(today))
                for idx, row in hist.iterrows():
                    bar_date = idx.date() if hasattr(idx, "date") else idx
                    repo.save_daily_bar(db_symbol, bar_date, {
                        "open": int(row["Open"]) if row["Open"] else None,
                        "high": int(row["High"]) if row["High"] else None,
                        "low": int(row["Low"]) if row["Low"] else None,
                        "close": int(row["Close"]) if row["Close"] else None,
                        "volume": int(row["Volume"]) if row["Volume"] else None,
                    })
            except Exception as e:
                logger.warning("지수 수집 실패 %s: %s", symbol, e)

        logger.info("yfinance 지수/환율 수집 완료")
    finally:
        db.close()


def _to_yf(symbol: str) -> str:
    if symbol.startswith("^") or "USD" in symbol:
        return symbol
    if symbol.isdigit() and len(symbol) == 6:
        return f"{symbol}.KS"
    return symbol
