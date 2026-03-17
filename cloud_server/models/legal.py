"""법적 문서 및 동의 기록 모델"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Column, Date, DateTime, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from cloud_server.core.database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class LegalDocument(Base):
    """약관/고지 문서 원문 + 버전"""
    __tablename__ = "legal_documents"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    doc_type       = Column(String(30), nullable=False)   # "terms" | "privacy" | "disclaimer"
    version        = Column(String(10), nullable=False)
    title          = Column(String(200), nullable=False)
    content_md     = Column(Text, nullable=False)
    effective_date = Column(Date, nullable=True)
    created_at     = Column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("doc_type", "version", name="uq_doc_type_version"),
    )


class LegalConsent(Base):
    """사용자별 약관 동의 기록"""
    __tablename__ = "legal_consents"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(String(36), ForeignKey("users.id"), nullable=False)
    doc_type    = Column(String(30), nullable=False)
    doc_version = Column(String(10), nullable=False)
    agreed_at   = Column(DateTime, default=_utcnow, nullable=False)
    ip_address  = Column(String(45), nullable=True)

    user = relationship("User", backref="legal_consents")

    __table_args__ = (
        Index("ix_consent_user_type", "user_id", "doc_type"),
    )
