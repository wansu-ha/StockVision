"""상태 라우터.

GET /api/status — 서버/브로커/전략 엔진 상태 조회
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from local_server.engine.safeguard import KillSwitchLevel
from local_server.storage.credential import has_credential, KEY_CLOUD_ACCESS_TOKEN

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    summary="서버/브로커/엔진 상태 조회",
)
async def get_status(request: Request) -> dict[str, Any]:
    """현재 로컬 서버의 종합 상태를 반환한다."""
    engine = getattr(request.app.state, "engine", None)
    broker = getattr(request.app.state, "broker", None)

    engine_running = engine.is_running if engine else False
    broker_connected = broker.is_connected if broker else False

    safeguard_data: dict[str, Any] = {}
    if engine:
        sg = engine.safeguard.state
        safeguard_data = {
            "kill_switch": sg.kill_switch.name,
            "loss_lock": sg.loss_lock,
            "trading_enabled": engine.safeguard.is_trading_enabled(),
        }

    return {
        "success": True,
        "data": {
            "server": "running",
            "broker": {
                "connected": broker_connected,
                "has_credentials": has_credential(KEY_CLOUD_ACCESS_TOKEN),
            },
            "strategy_engine": {
                "running": engine_running,
                **safeguard_data,
            },
        },
        "count": 1,
    }
