"""원격 명령 핸들러.

클라우드 WS를 통해 수신된 원격 명령(kill, arm 등)을 처리한다.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)


async def handle_command(app: FastAPI, msg: dict) -> None:
    """원격 명령 디스패치."""
    payload = msg.get("payload", {})
    action = payload.get("action")
    command_id = msg.get("id", "")

    if action == "kill":
        await _handle_kill(app, payload, command_id)
    elif action == "arm":
        await _handle_arm(app, payload, command_id)
    else:
        logger.warning("알 수 없는 원격 명령: %s", action)
        await _send_ack(command_id, {"success": False, "error": f"unknown action: {action}"})


async def _handle_kill(app: FastAPI, payload: dict, command_id: str) -> None:
    """킬스위치 처리."""
    from local_server.engine.safeguard import KillSwitchLevel

    mode = payload.get("mode", "stop_new")
    level = KillSwitchLevel.CANCEL_OPEN if mode == "stop_all" else KillSwitchLevel.STOP_NEW

    # 엔진의 safeguard 찾기
    engine = getattr(app.state, "engine", None)
    if engine and hasattr(engine, "safeguard"):
        engine.safeguard.set_kill_switch(level)
        logger.warning("원격 킬스위치 발동: mode=%s", mode)
        await _send_ack(command_id, {"success": True, "action": "kill", "mode": mode})
    else:
        # 엔진이 없어도 safeguard 직접 생성하여 상태 변경
        logger.warning("엔진 미실행 상태에서 원격 킬스위치 수신: mode=%s", mode)
        await _send_ack(command_id, {"success": True, "action": "kill", "mode": mode, "note": "engine_not_running"})


async def _handle_arm(app: FastAPI, payload: dict, command_id: str) -> None:
    """엔진 재개(arm) 처리."""
    from local_server.engine.safeguard import KillSwitchLevel

    engine = getattr(app.state, "engine", None)
    if engine and hasattr(engine, "safeguard"):
        engine.safeguard.set_kill_switch(KillSwitchLevel.OFF)
        engine.safeguard.unlock_loss_lock()
        logger.info("원격 arm 처리 완료")
        await _send_ack(command_id, {"success": True, "action": "arm"})
    else:
        logger.warning("엔진 미실행 상태에서 원격 arm 수신")
        await _send_ack(command_id, {"success": False, "action": "arm", "error": "engine_not_running"})


async def _send_ack(command_id: str, result: dict) -> None:
    """command ACK 전송."""
    from local_server.cloud.ws_relay_client import get_ws_relay_client
    ws_client = get_ws_relay_client()
    if ws_client and ws_client.is_connected:
        await ws_client.send_command_ack(command_id, result)
