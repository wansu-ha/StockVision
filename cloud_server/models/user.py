"""
사용자 인증 모델

- User: 사용자 계정
- RefreshToken: Refresh Token Rotation 지원
- EmailVerificationToken: 이메일 인증 링크
- PasswordResetToken: 비밀번호 재설정 링크
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from cloud_server.core.database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    """사용자 계정"""
    __tablename__ = "users"

    id             = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email          = Column(String(255), unique=True, nullable=False, index=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    password_hash  = Column(String(255), nullable=True)
    nickname       = Column(String(100), nullable=True)
    role           = Column(String(20), default="user", nullable=False)  # "user" | "admin"
    is_active      = Column(Boolean, default=True, nullable=False)
    deleted_at     = Column(DateTime, nullable=True, default=None)  # S4: Soft-Delete
    created_at     = Column(DateTime, default=_utcnow, nullable=False)
    last_login_at  = Column(DateTime, nullable=True)

    refresh_tokens        = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    email_verify_tokens   = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    trading_rules         = relationship("TradingRule", back_populates="user", cascade="all, delete-orphan")
    heartbeats            = relationship("Heartbeat", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    """Refresh Token (SHA-256 해시 저장, Rotation 지원)"""
    __tablename__ = "refresh_tokens"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id    = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hex
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    rotated_at = Column(DateTime, nullable=True)  # Rotation 추적용

    user = relationship("User", back_populates="refresh_tokens")


class EmailVerificationToken(Base):
    """이메일 인증 토큰 (24시간 TTL) — S5: SHA-256 해시 저장"""
    __tablename__ = "email_verification_tokens"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id    = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, index=True)  # S5: hash_token(raw)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="email_verify_tokens")


class PasswordResetToken(Base):
    """비밀번호 재설정 토큰 (10분 TTL) — S5: SHA-256 해시 저장"""
    __tablename__ = "password_reset_tokens"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id    = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, index=True)  # S5: hash_token(raw)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="password_reset_tokens")
