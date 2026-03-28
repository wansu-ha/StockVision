"""데이터 서버 환경 변수 및 설정."""
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """데이터 서버 설정"""

    ENV: str = os.environ.get("ENV", "development")

    DATABASE_URL: str = os.environ.get(
        "DATA_DATABASE_URL",
        "postgresql://stockvision:stockvision@localhost:5432/stockvision",
    )

    # 내부 API 인증 (클라우드 서버 ↔ 데이터 서버)
    API_SECRET: str = os.environ.get("DATA_API_SECRET", "")

    # 수집 스케줄 (KST)
    COLLECTOR_DAILY_SAVE_HOUR: int = int(os.environ.get("COLLECTOR_DAILY_SAVE_HOUR", "16"))
    COLLECTOR_MASTER_UPDATE_HOUR: int = int(os.environ.get("COLLECTOR_MASTER_UPDATE_HOUR", "8"))
    COLLECTOR_YFINANCE_HOUR: int = int(os.environ.get("COLLECTOR_YFINANCE_HOUR", "17"))

    # DART OpenAPI
    DART_API_KEY: str = os.environ.get("DART_API_KEY", "")

    # 키움 API (분봉 수집용)
    KIWOOM_APP_KEY: str = os.environ.get("KIWOOM_APP_KEY", "")
    KIWOOM_SECRET_KEY: str = os.environ.get("KIWOOM_SECRET_KEY", "")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
