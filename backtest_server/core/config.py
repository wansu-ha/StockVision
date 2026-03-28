"""백테스트 서버 설정."""
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    ENV: str = os.environ.get("ENV", "development")

    # 데이터 서버 URL (같은 VM에서 localhost)
    DATA_SERVER_URL: str = os.environ.get("DATA_SERVER_URL", "http://localhost:4030")

    # 클라우드 서버 URL (결과 전송용)
    CLOUD_SERVER_URL: str = os.environ.get("CLOUD_SERVER_URL", "http://localhost:4010")

    # 내부 API 인증
    API_SECRET: str = os.environ.get("BACKTEST_API_SECRET", "")

    # 워커 설정
    MAX_WORKERS: int = int(os.environ.get("BACKTEST_MAX_WORKERS", "3"))
    MAX_QUEUE_SIZE: int = int(os.environ.get("BACKTEST_MAX_QUEUE", "20"))
    JOB_TIMEOUT_SECONDS: int = int(os.environ.get("BACKTEST_TIMEOUT", "300"))  # 5분


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
