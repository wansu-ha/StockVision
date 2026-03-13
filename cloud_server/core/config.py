"""
환경 변수 및 설정 관리

개발: .env 파일
운영: 시스템 환경 변수
"""
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """애플리케이션 설정"""

    # 환경
    ENV: str = os.environ.get("ENV", "development")  # development | production

    # 데이터베이스
    # 개발: SQLite, 운영: PostgreSQL
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        "sqlite:///./cloud_server.db",
    )

    # 보안
    # SEC-C2: SECRET_KEY 기본값 제거 — 미설정 시 시작 실패
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "")
    CONFIG_ENCRYPTION_KEY: str = os.environ.get("CONFIG_ENCRYPTION_KEY", "")

    # JWT
    JWT_EXPIRE_HOURS: int = int(os.environ.get("JWT_EXPIRE_HOURS", "1"))  # 1시간
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    # 이메일 (SMTP)
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER: str = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD: str = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.environ.get("SMTP_FROM", "noreply@stockvision.com")

    # 클라우드 서버 공개 URL (API 링크용)
    CLOUD_URL: str = os.environ.get("CLOUD_URL", "http://localhost:4010")

    # 프론트엔드 공개 URL (이메일 내 프론트 링크용)
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "http://localhost:5173")

    # DART OpenAPI (금융감독원 전자공시)
    DART_API_KEY: str = os.environ.get("DART_API_KEY", "")

    # AI (Claude API)
    ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    AI_DAILY_LIMIT: int = int(os.environ.get("AI_DAILY_LIMIT", "100"))
    AI_CACHE_TTL: int = int(os.environ.get("AI_CACHE_TTL", "3600"))
    AI_STOCK_LIMIT: int = int(os.environ.get("AI_STOCK_LIMIT", "50"))

    # Redis (AI 캐시 + 향후 rate_limit 공용)
    REDIS_URL: str = os.environ.get("REDIS_URL", "")

    # OAuth2 — Google
    GOOGLE_CLIENT_ID: str = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.environ.get("GOOGLE_REDIRECT_URI", "")

    # OAuth2 — Kakao
    KAKAO_CLIENT_ID: str = os.environ.get("KAKAO_CLIENT_ID", "")
    KAKAO_CLIENT_SECRET: str = os.environ.get("KAKAO_CLIENT_SECRET", "")
    KAKAO_REDIRECT_URI: str = os.environ.get("KAKAO_REDIRECT_URI", "")

    # 이메일 발송 (SendGrid)
    EMAIL_PROVIDER: str = os.environ.get("EMAIL_PROVIDER", "sendgrid")
    EMAIL_API_KEY: str = os.environ.get("EMAIL_API_KEY", "")
    EMAIL_FROM: str = os.environ.get("EMAIL_FROM", "noreply@stockvision.com")

    # 로컬 서버 버전 정보
    LOCAL_SERVER_LATEST_VERSION: str = os.environ.get("LOCAL_SERVER_LATEST_VERSION", "1.0.0")
    LOCAL_SERVER_MIN_SUPPORTED: str = os.environ.get("LOCAL_SERVER_MIN_SUPPORTED", "1.0.0")
    LOCAL_SERVER_DOWNLOAD_URL: str = os.environ.get(
        "LOCAL_SERVER_DOWNLOAD_URL",
        "https://github.com/stockvision/releases/latest",
    )

    # CORS 허용 오리진 (환경변수: 콤마 구분 문자열)
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.environ.get(
            "CORS_ORIGINS", "http://localhost:5173"
        ).split(",")
        if origin.strip()
    ]

    # Rate Limiting (in-memory, 프로덕션은 Redis)
    RATE_LIMIT_LOGIN: int = 10      # 로그인: 10회/시간/IP
    RATE_LIMIT_REGISTER: int = 5    # 가입: 5회/시간/IP
    RATE_LIMIT_FORGOT_PW: int = 3   # 비밀번호 재설정: 3회/시간/IP

    # 수집 스케줄 (KST 기준)
    COLLECTOR_WS_START_HOUR: int = 9    # 09:00 WS 시작
    COLLECTOR_DAILY_SAVE_HOUR: int = 16  # 16:00 일봉 저장
    COLLECTOR_MASTER_UPDATE_HOUR: int = 8   # 08:00 종목마스터 갱신
    COLLECTOR_YFINANCE_HOUR: int = 17   # 17:00 yfinance 수집
    COLLECTOR_INTEGRITY_HOUR: int = 18  # 18:00 정합성 체크


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """설정 인스턴스 반환 (싱글톤)."""
    return Settings()


def validate_settings() -> None:
    """SEC-C2: SECRET_KEY 미설정 시 시작 실패. lifespan에서 호출."""
    if not settings.SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY 환경 변수가 설정되지 않았습니다. 서버를 시작할 수 없습니다."
        )
    if not settings.CONFIG_ENCRYPTION_KEY:
        import logging
        logging.getLogger(__name__).warning(
            "CONFIG_ENCRYPTION_KEY 미설정 — 암호화 기능 사용 시 오류 발생"
        )


# 편의 접근 (import 시점에는 검증하지 않음, validate_settings()로 분리)
settings = get_settings()
