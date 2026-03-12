"""시장 브리핑 DB 모델 (1일 1행)"""
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Integer, String, Text

from cloud_server.core.database import Base


class MarketBriefing(Base):
    """시장 브리핑 (1일 1행)"""
    __tablename__ = "market_briefings"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    date         = Column(Date, nullable=False, unique=True, index=True)
    summary      = Column(Text, nullable=False)
    sentiment    = Column(String(30), nullable=False)    # bearish~bullish
    indices_json = Column(Text, nullable=False)           # JSON 직렬화
    source       = Column(String(10), nullable=False)     # "claude" | "stub"
    token_input  = Column(Integer)
    token_output = Column(Integer)
    model        = Column(String(100))
    generated_at = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))
