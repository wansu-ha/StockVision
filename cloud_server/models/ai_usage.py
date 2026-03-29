"""AI 크레딧 사용량 추적 모델"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Date, ForeignKey, Integer, String, UniqueConstraint

from cloud_server.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AIUsage(Base):
    """일별 AI 토큰 사용량"""
    __tablename__ = "ai_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    tokens_used = Column(Integer, nullable=False, default=0)
    tokens_limit = Column(Integer, nullable=False)  # 해당 일자 한도 스냅샷
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_ai_usage_user_date"),
    )
