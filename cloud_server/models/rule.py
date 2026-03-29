"""
전략 규칙 모델

- TradingRule: 사용자 정의 매매 규칙
  - 조건: buy_conditions, sell_conditions (JSON)
  - 버전: version (클라이언트 동기화, 충돌 감지)
"""
from datetime import datetime

from sqlalchemy import (
    JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint,
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

    # DSL 스크립트 (v2 — 하위 호환: 기존 규칙은 null)
    script = Column(Text, nullable=True)

    # 하위 호환 (v1 JSON 조건 — 마이그레이션 완료 후 제거)
    buy_conditions  = Column(JSON, nullable=True)
    sell_conditions = Column(JSON, nullable=True)

    # 주문 설정 (v2 JSON — null이면 개별 컬럼 폴백)
    execution = Column(JSON, nullable=True)
    trigger_policy = Column(JSON, nullable=True, default={"frequency": "ONCE_PER_DAY"})
    priority = Column(Integer, default=0, nullable=False)

    # 설정 (v1 개별 컬럼 — execution 폴백용)
    order_type         = Column(String(10), default="market", nullable=False)  # market | limit
    qty                = Column(Integer, nullable=False)
    max_position_count = Column(Integer, default=5, nullable=False)
    budget_ratio       = Column(Float, default=0.2, nullable=False)

    # DSL 상수 파라미터 메타데이터 (자동 추출)
    parameters = Column(JSON, nullable=True)
    # Expected format:
    # {"기간": {"type": "number", "default": 14}, "tf": {"type": "string", "default": "1d"}}

    # DSL 정식 파싱 결과 (저장 시 parse_v2 실행 → 자동 생성)
    dsl_meta = Column(JSON, nullable=True)
    # Expected format:
    # {"constants": [...], "custom_functions": [...], "rules": [...],
    #  "parse_status": "ok"|"error", "is_v2": true, "errors": []}

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
