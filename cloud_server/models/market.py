"""
시장 데이터 모델

- StockMaster: 종목 마스터 정보
- DailyBar: 일봉 OHLCV 데이터
- MinuteBar: 분봉 OHLCV 데이터
"""
from datetime import date, datetime

from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Float, ForeignKey, Index,
    Integer, String, UniqueConstraint,
)

from cloud_server.core.database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class StockMaster(Base):
    """종목 마스터 정보 (상장 종목 목록)"""
    __tablename__ = "stock_master"

    symbol     = Column(String(10), primary_key=True)
    name       = Column(String(100), nullable=False)
    market     = Column(String(10), nullable=True)   # KOSPI | KOSDAQ | OVERSEAS
    sector     = Column(String(50), nullable=True)
    is_active  = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("idx_stock_market", "market"),
    )


class DailyBar(Base):
    """일봉 OHLCV 데이터 (장 마감 후 저장, 5년+ 보관)"""
    __tablename__ = "daily_bars"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    symbol     = Column(String(10), nullable=False)
    date       = Column(Date, nullable=False)
    open       = Column(Integer, nullable=True)
    high       = Column(Integer, nullable=True)
    low        = Column(Integer, nullable=True)
    close      = Column(Integer, nullable=True)
    volume     = Column(BigInteger, nullable=True)
    change_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_daily_symbol_date"),
        Index("idx_daily_symbol_date", "symbol", "date"),
    )


class MinuteBar(Base):
    """분봉 OHLCV 데이터 (실시간 수신, 1년 보관)"""
    __tablename__ = "minute_bars"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    symbol     = Column(String(10), nullable=False)
    timestamp  = Column(DateTime, nullable=False)  # KST 1분 단위
    open       = Column(Integer, nullable=True)
    high       = Column(Integer, nullable=True)
    low        = Column(Integer, nullable=True)
    close      = Column(Integer, nullable=True)
    volume     = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uq_minute_symbol_ts"),
        Index("idx_minute_symbol_ts", "symbol", "timestamp"),
    )
