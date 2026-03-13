"""
데이터베이스 연결 설정

개발: SQLite (./cloud_server.db)
운영: PostgreSQL (DATABASE_URL 환경변수)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from cloud_server.core.config import settings

# PostgreSQL이면 connect_args 불필요, SQLite만 check_same_thread 옵션 필요
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args: dict = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    # PostgreSQL: 커넥션 풀 설정
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI 의존성 주입용 DB 세션"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """스케줄러 등 의존성 주입 밖에서 사용"""
    return SessionLocal()
