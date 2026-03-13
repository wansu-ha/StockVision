"""종목별 AI 분석 결과 DB 모델 (1종목 1일 1행)"""
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Integer, String, Text, UniqueConstraint

from cloud_server.core.database import Base


class StockBriefing(Base):
    """종목별 AI 분석 결과 (1종목 1일 1행)"""
    __tablename__ = "stock_briefings"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    symbol       = Column(String(10), nullable=False, index=True)
    date         = Column(Date, nullable=False, index=True)
    summary      = Column(Text, nullable=False)
    sentiment    = Column(String(30), nullable=False)   # bearish ~ bullish
    source       = Column(String(10), nullable=False)   # "claude" | "stub"
    token_input  = Column(Integer)
    token_output = Column(Integer)
    model        = Column(String(100))
    generated_at = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_stock_briefing_symbol_date"),
    )
