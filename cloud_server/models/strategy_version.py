"""전략 버전 스냅샷 모델"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from cloud_server.core.database import Base


class StrategyVersion(Base):
    """전략 DSL 버전 스냅샷"""
    __tablename__ = "strategy_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("trading_rules.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    script = Column(Text, nullable=False)
    message = Column(String(500), nullable=True)  # 변경 요약
    created_by = Column(String(20), default="user")  # user | ai
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("rule_id", "version", name="uq_strategy_version"),
    )
