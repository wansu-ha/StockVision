"""시장 데이터 레포지토리 — DB CRUD."""
import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from data_server.models.market import DailyBar, MinuteBar, StockMaster

logger = logging.getLogger(__name__)


class MarketRepository:
    """시장 데이터 접근 레이어."""

    def __init__(self, db: Session):
        self.db = db

    # ── StockMaster ───────────────────────────────────────────────

    def upsert_stock_master(
        self, symbol: str, name: str, market: str, sector: str | None = None,
    ) -> None:
        existing = self.db.query(StockMaster).filter(
            StockMaster.symbol == symbol,
        ).first()
        if existing:
            existing.name = name
            existing.market = market
            existing.sector = sector
            existing.updated_at = datetime.utcnow()
        else:
            self.db.add(StockMaster(
                symbol=symbol, name=name, market=market,
                sector=sector, is_active=True,
            ))

    def get_all_stocks(
        self, market: str | None = None, search: str | None = None,
    ) -> list[StockMaster]:
        q = self.db.query(StockMaster).filter(StockMaster.is_active.is_(True))
        if market:
            q = q.filter(StockMaster.market == market)
        if search:
            q = q.filter(
                (StockMaster.name.contains(search))
                | (StockMaster.symbol.contains(search))
            )
        return q.order_by(StockMaster.symbol).all()

    def get_stock(self, symbol: str) -> StockMaster | None:
        return self.db.query(StockMaster).filter(
            StockMaster.symbol == symbol,
        ).first()

    # ── DailyBar ─────────────────────────────────────────────────

    def save_daily_bar(self, symbol: str, bar_date: date, ohlcv: dict) -> DailyBar:
        existing = self.db.query(DailyBar).filter(
            DailyBar.symbol == symbol, DailyBar.date == bar_date,
        ).first()
        if existing:
            existing.open = ohlcv.get("open", existing.open)
            existing.high = ohlcv.get("high", existing.high)
            existing.low = ohlcv.get("low", existing.low)
            existing.close = ohlcv.get("close", existing.close)
            existing.volume = ohlcv.get("volume", existing.volume)
            existing.change_pct = ohlcv.get("change_pct", existing.change_pct)
            self.db.commit()
            return existing
        bar = DailyBar(
            symbol=symbol, date=bar_date,
            open=ohlcv.get("open"), high=ohlcv.get("high"),
            low=ohlcv.get("low"), close=ohlcv.get("close"),
            volume=ohlcv.get("volume"), change_pct=ohlcv.get("change_pct"),
        )
        self.db.add(bar)
        self.db.commit()
        return bar

    def get_daily_bars(
        self, symbol: str, start_date: date, end_date: date,
    ) -> list[DailyBar]:
        return (
            self.db.query(DailyBar)
            .filter(
                DailyBar.symbol == symbol,
                DailyBar.date >= start_date,
                DailyBar.date <= end_date,
            )
            .order_by(DailyBar.date)
            .all()
        )

    # ── MinuteBar ────────────────────────────────────────────────

    def upsert_minute_bar(
        self, symbol: str, ts: datetime,
        open_: int, high: int, low: int, close: int, volume: int,
    ) -> None:
        ts = ts.replace(second=0, microsecond=0)
        existing = self.db.query(MinuteBar).filter(
            MinuteBar.symbol == symbol, MinuteBar.timestamp == ts,
        ).first()
        if existing:
            existing.open = open_ or existing.open
            existing.high = max(existing.high or 0, high)
            existing.low = min(existing.low or 999999999, low)
            existing.close = close or existing.close
            existing.volume = volume or existing.volume
        else:
            self.db.add(MinuteBar(
                symbol=symbol, timestamp=ts,
                open=open_, high=high, low=low, close=close, volume=volume,
            ))

    def get_minute_bars(
        self, symbol: str, start_dt: datetime, end_dt: datetime, limit: int = 5000,
    ) -> list[MinuteBar]:
        return (
            self.db.query(MinuteBar)
            .filter(
                MinuteBar.symbol == symbol,
                MinuteBar.timestamp >= start_dt,
                MinuteBar.timestamp <= end_dt,
            )
            .order_by(MinuteBar.timestamp)
            .limit(limit)
            .all()
        )
