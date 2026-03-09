"""Alembic 환경 설정."""
from logging.config import fileConfig

from alembic import context

from cloud_server.core.config import settings
from cloud_server.core.database import Base

# 모든 모델 import (Base.metadata에 등록)
from cloud_server.models.user import User, RefreshToken, EmailVerificationToken, PasswordResetToken  # noqa: F401
from cloud_server.models.rule import TradingRule  # noqa: F401
from cloud_server.models.heartbeat import Heartbeat  # noqa: F401
from cloud_server.models.market import StockMaster, DailyBar, MinuteBar, Watchlist  # noqa: F401
from cloud_server.models.template import StrategyTemplate, BrokerServiceKey  # noqa: F401
from cloud_server.models.fundamental import CompanyFinancial, CompanyDividend  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.DATABASE_URL
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from cloud_server.core.database import engine
    connectable = engine
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
