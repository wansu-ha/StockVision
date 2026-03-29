"""AI 대화 히스토리 모델"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON

from cloud_server.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AIConversation(Base):
    """AI 대화 히스토리 (전략 빌더/기본 비서)"""
    __tablename__ = "ai_conversations"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    strategy_id = Column(Integer, ForeignKey("trading_rules.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=True)  # 첫 메시지 기반
    messages = Column(JSON, nullable=False, default=list)  # [{role, content, timestamp}]
    current_dsl = Column(Text, nullable=True)
    mode = Column(String(20), nullable=False, default="builder")  # builder | assistant
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
