"""
전략 템플릿 모델 (어드민 관리)

- StrategyTemplate: 관리자가 제공하는 공개 전략 템플릿
- BrokerServiceKey: 서비스 증권사 API 키 (암호화 저장)
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text

from cloud_server.core.database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class StrategyTemplate(Base):
    """관리자 제공 전략 템플릿"""
    __tablename__ = "strategy_templates"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    name            = Column(String(100), nullable=False)
    description     = Column(Text, nullable=True)
    buy_conditions  = Column(JSON, nullable=True)
    sell_conditions = Column(JSON, nullable=True)
    default_params  = Column(JSON, nullable=True)   # qty, budget_ratio 등
    category        = Column(String(50), nullable=True)  # "기술적 지표", "모멘텀" 등
    is_public       = Column(Boolean, default=False, nullable=False)
    created_by      = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at      = Column(DateTime, default=_utcnow, nullable=False)
    updated_at      = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=True)


class BrokerServiceKey(Base):
    """서비스 증권사 API 키 (어드민 관리, api_secret은 AES-256-GCM 암호화)"""
    __tablename__ = "broker_service_keys"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    api_key      = Column(String(255), nullable=False)
    api_secret   = Column(String(512), nullable=False)  # hex 암호화
    app_name     = Column(String(100), nullable=True)
    is_active    = Column(Boolean, default=True, nullable=False)
    created_at   = Column(DateTime, default=_utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
