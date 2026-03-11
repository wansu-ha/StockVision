"""로그 조회 라우터.

GET /api/logs — 체결/에러 로그 조회 (필터, 페이지네이션)
GET /api/logs/summary — 날짜별 로그 타입별 건수 요약
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from local_server.core.local_auth import require_local_secret

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
    "/summary",
    summary="로그 요약",
)
async def log_summary(
    date: str | None = Query(
        None,
        description="요약 기준 날짜 (YYYY-MM-DD). 미지정 시 오늘.",
    ),
    _: None = Depends(require_local_secret),
) -> dict[str, Any]:
    """특정 날짜 이후 로그 타입별 건수를 반환한다."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    db = get_log_db()
    counts = db.count_by_type(date)

    return {
        "success": True,
        "data": {
            "date": date,
            "signals": counts.get(LOG_TYPE_STRATEGY, 0),
            "fills": counts.get(LOG_TYPE_FILL, 0),
            "orders": counts.get(LOG_TYPE_ORDER, 0),
            "errors": counts.get(LOG_TYPE_ERROR, 0),
        },
        "count": 1,
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
    date_from: str | None = Query(None, description="시작 날짜 필터 (YYYY-MM-DD)"),
    _: None = Depends(require_local_secret),
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
        date_from=date_from,
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
