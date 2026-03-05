"""
전략 규칙 모델

- TradingRule: 사용자 정의 매매 규칙
  - 조건: buy_conditions, sell_conditions (JSON)
  - 버전: version (클라이언트 동기화, 충돌 감지)
"""
from datetime import datetime

from sqlalchemy import (
    JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer,
    String, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from cloud_server.core.database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class TradingRule(Base):
    """사용자 매매 규칙"""
    __tablename__ = "trading_rules"

    id     = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name   = Column(String(100), nullable=False)
    symbol = Column(String(10), nullable=False)

    # 조건 JSON: { "operator": "AND"|"OR", "conditions": [...] }
    buy_conditions  = Column(JSON, nullable=True)
    sell_conditions = Column(JSON, nullable=True)

    # 설정
    order_type         = Column(String(10), default="market", nullable=False)  # market | limit
    qty                = Column(Integer, nullable=False)
    max_position_count = Column(Integer, default=5, nullable=False)
    budget_ratio       = Column(Float, default=0.2, nullable=False)

    # 상태
    is_active  = Column(Boolean, default=True, nullable=False)
    version    = Column(Integer, default=1, nullable=False)  # 클라이언트 동기화용
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=True)

    user = relationship("User", back_populates="trading_rules")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_rule_name"),
        Index("idx_user_rules", "user_id"),
    )
