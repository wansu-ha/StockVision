"""
데이터베이스 초기화

모든 모델을 import하여 Base.metadata에 등록 후 테이블 생성.
"""
from cloud_server.core.database import Base, engine

# 모든 모델 import (Base.metadata에 테이블 등록)
from cloud_server.models.user import User, RefreshToken, EmailVerificationToken, PasswordResetToken  # noqa: F401
from cloud_server.models.rule import TradingRule  # noqa: F401
from cloud_server.models.heartbeat import Heartbeat  # noqa: F401
from cloud_server.models.market import StockMaster, DailyBar, MinuteBar  # noqa: F401
from cloud_server.models.template import StrategyTemplate, KiwoomServiceKey  # noqa: F401


def init_db() -> None:
    """모든 테이블 생성 (존재하면 건너뜀)"""
    Base.metadata.create_all(bind=engine)
    print("[OK] 데이터베이스 테이블 생성 완료")


if __name__ == "__main__":
    init_db()
