from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from datetime import datetime
from app.core.database import Base


class StockScore(Base):
    """종목 스코어링 결과 (스냅샷)"""
    __tablename__ = "stock_scores"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, nullable=False)
    symbol = Column(String(10), nullable=False)
    date = Column(DateTime, nullable=False)

    # 개별 지표 스코어 (0~100)
    rsi_score = Column(Float)
    macd_score = Column(Float)
    bollinger_score = Column(Float)
    ema_score = Column(Float)
    prediction_score = Column(Float)        # RF 예측 기반

    # 통합 스코어
    total_score = Column(Float, nullable=False)
    signal = Column(String(10))             # BUY, SELL, HOLD

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_score_date', 'stock_id', 'date'),
    )
