"""
cloud_server 통합 테스트 공통 픽스처

- 인메모리 SQLite (StaticPool — 단일 연결 공유)
- FastAPI TestClient
- 헬퍼: 유저 생성, 인증 토큰 발급
"""
import os

# 테스트용 환경 변수 — 모듈 import 전에 설정
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests"
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud_server.core.security import create_jwt, hash_password
from cloud_server.models.user import User

# StaticPool로 모든 연결이 같은 인메모리 DB를 공유
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _setup_db():
    """매 테스트마다 테이블 생성/삭제 (격리)"""
    from cloud_server.core.database import Base

    # 모든 모델 import → Base.metadata 등록
    from cloud_server.models.user import User, RefreshToken, EmailVerificationToken, PasswordResetToken  # noqa: F401
    from cloud_server.models.rule import TradingRule  # noqa: F401
    from cloud_server.models.heartbeat import Heartbeat  # noqa: F401
    from cloud_server.models.market import StockMaster, DailyBar, MinuteBar, Watchlist  # noqa: F401
    from cloud_server.models.template import StrategyTemplate, BrokerServiceKey  # noqa: F401
    from cloud_server.models.fundamental import CompanyFinancial, CompanyDividend  # noqa: F401
    from cloud_server.models.ai import AIAnalysisLog  # noqa: F401
    from cloud_server.models.briefing import MarketBriefing  # noqa: F401
    from cloud_server.models.stock_briefing import StockBriefing  # noqa: F401
    from cloud_server.models.legal import LegalDocument, LegalConsent  # noqa: F401
    from cloud_server.models.pending_command import PendingCommand  # noqa: F401
    from cloud_server.models.audit_log import AuditLog  # noqa: F401
    from cloud_server.models.oauth_account import OAuthAccount  # noqa: F401
    from cloud_server.models.device import Device  # noqa: F401

    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def db():
    """테스트용 DB 세션"""
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    """TestClient (DB 의존성을 테스트 엔진으로 교체)"""
    from cloud_server.core.database import get_db
    from cloud_server.main import app

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def _make_user(db, email="test@example.com", password="test1234", role="user",
               verified=True, active=True) -> User:
    """테스트용 유저 생성 헬퍼"""
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        email_verified=verified,
        is_active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_header(user: User) -> dict:
    """JWT Authorization 헤더 생성"""
    token = create_jwt(user.id, user.email, role=user.role)
    return {"Authorization": f"Bearer {token}"}
