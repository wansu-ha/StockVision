from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from app.core.database import Base


class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    name             = Column(String(200), nullable=False)
    description      = Column(Text, nullable=True)
    category         = Column(String(100), nullable=True)
    difficulty       = Column(String(20), nullable=True)   # "초급" | "중급" | "고급"
    rule_json        = Column(JSON, nullable=True)          # TradingRule 포맷
    backtest_summary = Column(JSON, nullable=True)          # { cagr, mdd, sharpe }
    tags             = Column(JSON, nullable=True)          # list[str]
    is_active        = Column(Boolean, default=True, nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
