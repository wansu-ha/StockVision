"""BYO API Key 모델 — 사용자 자체 Anthropic 키 암호화 저장"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from cloud_server.core.database import Base


class AIApiKey(Base):
    """사용자 BYO API Key (Fernet 암호화)"""
    __tablename__ = "ai_api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    encrypted_key = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
