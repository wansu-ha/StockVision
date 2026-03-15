"""상태 라우터.

GET /api/status — 서버/브로커/전략 엔진 상태 조회
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from local_server.engine.safeguard import KillSwitchLevel
from local_server.storage.credential import (
    load_credential,
    KEY_KIWOOM_APP_KEY,
    KEY_KIWOOM_SECRET_KEY,
    KEY_APP_KEY,
    KEY_APP_SECRET,
)

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
    broker_reason: str = getattr(request.app.state, "broker_reason", "disconnected")

    engine_running = engine.is_running if engine else False
    broker_connected = broker.is_connected if broker else False

    safeguard_data: dict[str, Any] = {}
    if engine:
        sg = engine.safeguard.state
        safeguard_data = {
            "kill_switch": sg.kill_switch != KillSwitchLevel.OFF,
            "loss_lock": sg.loss_lock,
            "trading_enabled": engine.safeguard.is_trading_enabled(),
        }

    # is_mock 판단: 브로커 인스턴스 > config 순서
    def _resolve_is_mock(b: Any) -> bool:
        auth = getattr(b, "_auth", None) if b else None
        if auth is not None:
            return getattr(auth, "_is_mock", True)
        from local_server.config import get_config
        return get_config().get("broker.is_mock", True)

    # 브로커 키 마스킹 — 앞 4자만 노출
    def _mask(key_name: str) -> str | None:
        val = load_credential(key_name)
        if not val:
            return None
        return val[:4] + "*" * (len(val) - 4)

    credentials: dict[str, Any] = {
        "kiwoom": {
            "app_key": _mask(KEY_KIWOOM_APP_KEY),
            "secret_key": _mask(KEY_KIWOOM_SECRET_KEY),
        },
        "kis": {
            "app_key": _mask(KEY_APP_KEY),
            "app_secret": _mask(KEY_APP_SECRET),
        },
    }

    # 설정된 브로커 타입에 맞는 실제 키 존재 여부 확인
    from local_server.config import get_config as _get_config
    _broker_type = _get_config().get("broker.type", "kiwoom")
    if _broker_type == "kis":
        _has_creds = bool(load_credential(KEY_APP_KEY) and load_credential(KEY_APP_SECRET))
    else:
        _has_creds = bool(load_credential(KEY_KIWOOM_APP_KEY) and load_credential(KEY_KIWOOM_SECRET_KEY))

    return {
        "success": True,
        "data": {
            "server": "running",
            "broker": {
                "connected": broker_connected,
                "reason": broker_reason,
                "has_credentials": _has_creds,
                "credentials": credentials,
                "is_mock": _resolve_is_mock(broker),
            },
            "strategy_engine": {
                "running": engine_running,
                **safeguard_data,
            },
        },
        "count": 1,
    }
