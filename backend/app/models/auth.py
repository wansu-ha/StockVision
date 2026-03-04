from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Boolean, DateTime, Integer, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


def _utcnow():
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id             = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email          = Column(String(255), unique=True, nullable=False, index=True)
    password_hash  = Column(String(255), nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    nickname       = Column(String(100), nullable=True)
    role           = Column(String(20), default="user", nullable=False)  # "user" | "admin"
    created_at     = Column(DateTime, default=_utcnow, nullable=False)

    refresh_tokens        = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    email_verify_tokens   = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    config_blob           = relationship("ConfigBlob", back_populates="user", uselist=False, cascade="all, delete-orphan")
    onboarding_state      = relationship("OnboardingState", back_populates="user", uselist=False, cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id    = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hex
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id    = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token      = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="email_verify_tokens")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id    = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token      = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="password_reset_tokens")


class ConfigBlob(Base):
    __tablename__ = "config_blobs"

    user_id    = Column(String(36), ForeignKey("users.id"), primary_key=True)
    blob       = Column(LargeBinary, nullable=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("User", back_populates="config_blob")


class OnboardingState(Base):
    __tablename__ = "onboarding_states"

    user_id          = Column(String(36), ForeignKey("users.id"), primary_key=True)
    step_completed   = Column(Integer, default=0, nullable=False)  # 0~6
    risk_accepted    = Column(Boolean, default=False, nullable=False)
    risk_accepted_at = Column(DateTime, nullable=True)
    completed_at     = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="onboarding_state")
