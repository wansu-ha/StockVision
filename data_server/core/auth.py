"""내부 API 인증 미들웨어."""
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from data_server.core.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """API Key 검증. 개발 환경에서는 비활성."""
    if not settings.API_SECRET:
        return  # 시크릿 미설정 → 인증 비활성 (개발용)
    if api_key != settings.API_SECRET:
        raise HTTPException(status_code=401, detail="유효하지 않은 API Key")
