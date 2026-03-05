"""규칙 동기화 라우터.

POST /api/rules/sync — 클라우드 서버에서 매매 규칙을 가져와 캐시
GET  /api/rules      — 현재 캐시된 규칙 목록 조회
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from local_server.config import get_config
from local_server.cloud.client import CloudClient
from local_server.storage.rules_cache import get_rules_cache

logger = logging.getLogger(__name__)

router = APIRouter()


class RulesSyncRequest(BaseModel):
    """규칙 동기화 요청 바디 (선택적 규칙 직접 제공)."""

    rules: list[dict[str, Any]] | None = None  # None이면 클라우드에서 자동 fetch


@router.post(
    "/sync",
    summary="클라우드에서 매매 규칙 동기화",
)
async def sync_rules(body: RulesSyncRequest | None = None) -> dict[str, Any]:
    """클라우드 서버에서 매매 규칙을 가져와 로컬 캐시에 저장한다.

    body.rules가 있으면 직접 제공된 규칙으로 캐시를 갱신한다.
    없으면 클라우드 URL에서 규칙을 가져온다.
    """
    cache = get_rules_cache()

    if body and body.rules is not None:
        # 직접 제공된 규칙으로 동기화
        rules = body.rules
    else:
        # 클라우드에서 규칙 fetch
        cfg = get_config()
        cloud_url = cfg.get("cloud.url")
        if not cloud_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="클라우드 URL이 설정되지 않았습니다. /api/config에서 cloud.url을 설정하세요.",
            )

        client = CloudClient(base_url=cloud_url)
        try:
            rules = await client.fetch_rules()
        except Exception as e:
            logger.error("클라우드에서 규칙 fetch 실패: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"클라우드 서버 규칙 조회 실패: {e}",
            ) from e

    cache.sync(rules)
    logger.info("규칙 동기화 완료: %d개", len(rules))

    return {
        "success": True,
        "data": {"synced_count": len(rules)},
        "count": len(rules),
    }


@router.get(
    "",
    summary="현재 캐시된 규칙 목록 조회",
)
async def get_rules() -> dict[str, Any]:
    """로컬에 캐시된 매매 규칙 목록을 반환한다."""
    cache = get_rules_cache()
    rules = cache.get_rules()
    return {"success": True, "data": rules, "count": len(rules)}
