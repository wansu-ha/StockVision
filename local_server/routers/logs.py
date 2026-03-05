"""로그 조회 라우터.

GET /api/logs — 체결/에러 로그 조회 (필터, 페이지네이션)
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

from local_server.storage.log_db import (
    get_log_db,
    LOG_TYPE_FILL,
    LOG_TYPE_ORDER,
    LOG_TYPE_ERROR,
    LOG_TYPE_SYSTEM,
    LOG_TYPE_STRATEGY,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 허용 로그 타입
VALID_LOG_TYPES = {
    LOG_TYPE_FILL,
    LOG_TYPE_ORDER,
    LOG_TYPE_ERROR,
    LOG_TYPE_SYSTEM,
    LOG_TYPE_STRATEGY,
}


@router.get(
    "",
    summary="로그 조회",
)
async def query_logs(
    log_type: str | None = Query(
        None,
        description=f"필터할 로그 종류: {', '.join(sorted(VALID_LOG_TYPES))}",
    ),
    symbol: str | None = Query(None, description="종목 코드 필터"),
    limit: int = Query(100, ge=1, le=1000, description="최대 조회 수"),
    offset: int = Query(0, ge=0, description="건너뛸 수"),
) -> dict[str, Any]:
    """체결/에러 로그를 조회한다.

    최신 순으로 정렬되어 반환된다.
    """
    # log_type 유효성 검사
    if log_type and log_type not in VALID_LOG_TYPES:
        return {
            "success": False,
            "data": {
                "error": f"유효하지 않은 log_type: {log_type}",
                "valid_types": sorted(VALID_LOG_TYPES),
            },
            "count": 0,
        }

    db = get_log_db()
    items, total = db.query(
        log_type=log_type,
        symbol=symbol,
        limit=limit,
        offset=offset,
    )

    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
        "count": len(items),
    }
