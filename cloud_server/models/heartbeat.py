"""
하트비트 모델

로컬 서버가 클라우드 서버에 주기적으로 상태를 보고.
UUID는 로컬 설치 시 1회 생성 (개인정보 아님).
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from cloud_server.core.database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class Heartbeat(Base):
    """로컬 서버 하트비트 로그"""
    __tablename__ = "heartbeats"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    uuid              = Column(String(50), nullable=False, index=True)  # 로컬 설치 고유 ID
    user_id           = Column(String(36), ForeignKey("users.id"), nullable=False)
    version           = Column(String(20), nullable=True)   # 로컬 서버 버전
    os                = Column(String(20), nullable=True)   # windows | mac | linux
    kiwoom_connected  = Column(Boolean, nullable=True)       # 키움 연결 여부
    engine_running    = Column(Boolean, nullable=True)       # 엔진 실행 여부
    active_rules_count = Column(Integer, nullable=True)     # 활성 규칙 수
    timestamp         = Column(DateTime, nullable=False)     # 로컬 타임스탬프
    created_at        = Column(DateTime, default=_utcnow, nullable=False)

    user = relationship("User", back_populates="heartbeats")

    __table_args__ = (
        Index("idx_heartbeat_uuid_user", "uuid", "user_id"),
    )
