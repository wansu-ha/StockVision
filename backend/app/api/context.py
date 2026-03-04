"""
GET /api/context — 시장 컨텍스트 API

- 인증 필요 (current_user)
- 캐시: 모듈 수준 메모리 캐시 (장 마감 후 갱신)
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.api.dependencies import current_user
from app.services.market_context import compute_market_context

router = APIRouter(prefix="/api", tags=["context"])
logger = logging.getLogger(__name__)

_cache: dict = {}
_cache_date: str = ""


def _get_context() -> dict:
    global _cache, _cache_date
    today = datetime.now(tz=timezone.utc).date().isoformat()
    if _cache_date == today and _cache:
        return _cache
    try:
        _cache      = compute_market_context()
        _cache_date = today
        logger.info("시장 컨텍스트 갱신 완료")
    except Exception as e:
        logger.error(f"시장 컨텍스트 계산 실패: {e}")
    return _cache


@router.get("/context")
def get_context(_user=Depends(current_user)):
    data = _get_context()
    return {"success": True, "data": data}
