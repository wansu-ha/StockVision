"""디바이스 모델.

등록된 원격 디바이스 메타데이터. E2E 키는 클라우드에 저장하지 않음.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from cloud_server.core.database import Base


class Device(Base):
    """등록된 디바이스"""
    __tablename__ = "devices"

    id            = Column(String(50), primary_key=True, default=lambda: str(uuid4())[:8])
    user_id       = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name          = Column(String(100), nullable=True)     # "iPhone 15", "Chrome - Windows"
    platform      = Column(String(20), nullable=True)      # 'web' | 'android' | 'ios'
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at  = Column(DateTime, nullable=True)
    last_ip       = Column(String(45), nullable=True)
    is_active     = Column(Boolean, default=True)

    user = relationship("User", backref="devices")
