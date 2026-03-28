"""내부 API 인증."""
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from backtest_server.core.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    if not settings.API_SECRET:
        return
    if api_key != settings.API_SECRET:
        raise HTTPException(status_code=401, detail="유효하지 않은 API Key")
