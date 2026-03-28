"""데이터 서버 DB 연결."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from data_server.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI 의존성 주입용 DB 세션."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """스케줄러 등 의존성 주입 밖에서 사용."""
    return SessionLocal()
