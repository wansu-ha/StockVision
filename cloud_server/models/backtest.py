"""백테스트 실행 이력 모델."""
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Float, Integer, String
from sqlalchemy.types import JSON

from cloud_server.core.database import Base


class BacktestExecution(Base):
    """백테스트 실행 결과 저장."""
    __tablename__ = "backtest_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), nullable=False, index=True)
    rule_id = Column(Integer, nullable=True, index=True)  # inline script일 때 null
    symbol = Column(String(10), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    timeframe = Column(String(5), nullable=False, default="1d")
    initial_cash = Column(Float, nullable=False, default=10_000_000)
    summary = Column(JSON, nullable=False)  # {total_return_pct, mdd, win_rate, ...}
    trade_count = Column(Integer, nullable=False, default=0)
    executed_at = Column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
