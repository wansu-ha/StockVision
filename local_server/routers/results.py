"""규칙 최근 실행 결과 라우터.

GET /api/rules/last-results — 전체 규칙의 최근 결과 조회
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from local_server.engine.result_store import get_all_results, to_dict

router = APIRouter()


@router.get(
    "/last-results",
    summary="전체 규칙 최근 실행 결과 조회",
)
async def last_results() -> dict[str, Any]:
    """규칙별 최근 실행 결과를 반환한다."""
    results = get_all_results()
    data = [to_dict(r) for r in results.values()]
    return {"success": True, "data": data, "count": len(data)}
