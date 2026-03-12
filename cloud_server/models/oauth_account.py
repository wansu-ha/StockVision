"""OAuth 계정 모델.

한 사용자가 Google + Kakao를 동시에 연동할 수 있도록 별도 테이블.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from cloud_server.core.database import Base


class OAuthAccount(Base):
    """OAuth2 제공자 연동 정보"""
    __tablename__ = "oauth_accounts"

    id               = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id          = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    provider         = Column(String(20), nullable=False)    # 'google' | 'kakao'
    provider_user_id = Column(String(100), nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="oauth_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),
    )
