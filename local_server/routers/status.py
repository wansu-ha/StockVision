"""상태 라우터.

GET /api/status — 서버/브로커/전략 엔진 상태 조회
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from local_server.storage.credential import has_credential, KEY_APP_KEY

logger = logging.getLogger(__name__)

router = APIRouter()

# 전략 엔진 실행 상태 (인메모리, 재시작 시 초기화)
_strategy_running: bool = False


def set_strategy_running(running: bool) -> None:
    """전략 엔진 실행 상태를 갱신한다 (trading 라우터에서 호출)."""
    global _strategy_running
    _strategy_running = running


def is_strategy_running() -> bool:
    """전략 엔진이 실행 중인지 반환한다."""
    return _strategy_running


@router.get(
    "",
    summary="서버/브로커/엔진 상태 조회",
)
async def get_status() -> dict[str, Any]:
    """현재 로컬 서버의 종합 상태를 반환한다."""
    has_key = has_credential(KEY_APP_KEY)

    return {
        "success": True,
        "data": {
            "server": "running",
            "broker": {
                "connected": False,  # TODO: Unit 1 BrokerAdapter 연동 후 실제 상태 반영
                "has_credentials": has_key,
            },
            "strategy_engine": {
                "running": _strategy_running,
            },
        },
        "count": 1,
    }
