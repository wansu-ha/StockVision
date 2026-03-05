"""
시장 데이터 레포지토리

MinuteBar, DailyBar, StockMaster CRUD.
1분봉 집계: 같은 timestamp의 기존 바가 있으면 OHLC 업데이트.
"""
import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from cloud_server.models.market import DailyBar, MinuteBar, StockMaster
from sv_core.broker.models import QuoteEvent  # C1: 정본 경로로 수정

logger = logging.getLogger(__name__)


class MarketRepository:
    """시장 데이터 접근 레이어"""

    def __init__(self, db: Session):
        self.db = db

    # ── StockMaster ───────────────────────────────────────────────────

    def upsert_stock_master(self, symbol: str, name: str, market: str, sector: str | None = None) -> None:
        """종목 마스터 추가/갱신 (upsert)"""
        existing = self.db.query(StockMaster).filter(StockMaster.symbol == symbol).first()
        if existing:
            existing.name = name
            existing.market = market
            existing.sector = sector
            existing.updated_at = datetime.utcnow()
        else:
            master = StockMaster(
                symbol=symbol,
                name=name,
                market=market,
                sector=sector,
                is_active=True,
            )
            self.db.add(master)

    # ── MinuteBar ────────────────────────────────────────────────────

    def save_minute_bar(self, event: QuoteEvent) -> MinuteBar:
        """
        분봉 저장 (1분 단위 집계).
        같은 symbol+timestamp가 있으면 high/low/close/volume 업데이트.
        """
        # C2/C3: timestamp는 Optional — None이면 현재 시각 사용
        raw_ts = event.timestamp if event.timestamp is not None else datetime.utcnow()
        ts = raw_ts.replace(second=0, microsecond=0)

        existing = self.db.query(MinuteBar).filter(
            MinuteBar.symbol == event.symbol,
            MinuteBar.timestamp == ts,
        ).first()

        if existing:
            # OHLC 업데이트
            if existing.high is None or event.price > existing.high:
                existing.high = event.price
            if existing.low is None or event.price < existing.low:
                existing.low = event.price
            existing.close = event.price
            if existing.volume is not None:
                existing.volume += event.volume
            else:
                existing.volume = event.volume
            self.db.commit()
            return existing

        bar = MinuteBar(
            symbol=event.symbol,
            timestamp=ts,
            open=event.price,
            high=event.price,
            low=event.price,
            close=event.price,
            volume=event.volume,
        )
        self.db.add(bar)
        self.db.commit()
        return bar

    def get_latest_price(self, symbol: str) -> int | None:
        """최신 시세 조회"""
        bar = self.db.query(MinuteBar).filter(
            MinuteBar.symbol == symbol
        ).order_by(MinuteBar.timestamp.desc()).first()
        return bar.close if bar else None

    # ── DailyBar ─────────────────────────────────────────────────────

    def save_daily_bar(self, symbol: str, bar_date: date, ohlcv: dict) -> DailyBar:
        """일봉 저장 (upsert)"""
        existing = self.db.query(DailyBar).filter(
            DailyBar.symbol == symbol,
            DailyBar.date == bar_date,
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
            symbol=symbol,
            date=bar_date,
            open=ohlcv.get("open"),
            high=ohlcv.get("high"),
            low=ohlcv.get("low"),
            close=ohlcv.get("close"),
            volume=ohlcv.get("volume"),
            change_pct=ohlcv.get("change_pct"),
        )
        self.db.add(bar)
        self.db.commit()
        return bar

    def get_daily_bars(self, symbol: str, start_date: date, end_date: date) -> list[DailyBar]:
        """일봉 범위 조회"""
        return self.db.query(DailyBar).filter(
            DailyBar.symbol == symbol,
            DailyBar.date >= start_date,
            DailyBar.date <= end_date,
        ).order_by(DailyBar.date).all()

    def has_daily_bar(self, symbol: str, bar_date: date) -> bool:
        """특정 날짜의 일봉 존재 여부"""
        return self.db.query(DailyBar).filter(
            DailyBar.symbol == symbol,
            DailyBar.date == bar_date,
        ).first() is not None
