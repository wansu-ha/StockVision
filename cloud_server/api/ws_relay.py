"""WebSocket 릴레이 엔드포인트.

/ws/relay — 로컬 서버 전용 (상태 전송, heartbeat, ACK 수신)
/ws/remote — 원격 디바이스 전용 (상태 수신, 명령 전송)

인증: 첫 메시지 auth 패턴 (query string 노출 방지)
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

from cloud_server.core.security import verify_jwt
from cloud_server.services.relay_manager import get_relay_manager, get_session_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket 릴레이"])

AUTH_TIMEOUT = 10  # 초 — 첫 auth 메시지 대기 시간


async def _wait_auth(ws: WebSocket, require_device_id: bool = False) -> dict | None:
    """첫 메시지로 auth를 받아 JWT 검증. 실패 시 None."""
    try:
        msg = await asyncio.wait_for(ws.receive_json(), timeout=AUTH_TIMEOUT)
    except (asyncio.TimeoutError, Exception):
        await ws.close(code=4001, reason="auth_timeout")
        return None

    if msg.get("type") != "auth":
        await ws.close(code=4001, reason="first_message_must_be_auth")
        return None

    token = msg.get("payload", {}).get("token", "")
    try:
        payload = verify_jwt(token)
    except JWTError:
        await ws.close(code=4001, reason="invalid_token")
        return None

    result = {
        "user_id": payload["sub"],
        "email": payload.get("email", ""),
        "jwt_exp": payload.get("exp", 0),
    }

    if require_device_id:
        device_id = msg.get("payload", {}).get("device_id")
        if not device_id:
            await ws.close(code=4002, reason="device_id_required")
            return None
        result["device_id"] = device_id

    return result


@router.websocket("/ws/relay")
async def ws_relay(ws: WebSocket):
    """로컬 서버 전용 WS 엔드포인트."""
    await ws.accept()

    auth = await _wait_auth(ws)
    if auth is None:
        return

    user_id = auth["user_id"]
    relay = get_relay_manager()
    relay.register_local(user_id, ws)

    # 재연결 시 pending 큐 flush
    await relay.flush_pending_commands(user_id)

    try:
        while True:
            msg = await ws.receive_json()
            await relay.handle_local_message(user_id, msg)
    except WebSocketDisconnect:
        logger.info("로컬 WS 연결 해제: user=%s", user_id)
    except Exception as e:
        logger.error("로컬 WS 오류: user=%s, error=%s", user_id, e)
    finally:
        relay.unregister_local(user_id)


@router.websocket("/ws/remote")
async def ws_remote(ws: WebSocket):
    """원격 디바이스 전용 WS 엔드포인트."""
    await ws.accept()

    auth = await _wait_auth(ws, require_device_id=True)
    if auth is None:
        return

    user_id = auth["user_id"]
    device_id = auth["device_id"]
    jwt_exp = auth.get("jwt_exp", 0)

    session_mgr = get_session_manager()
    if not session_mgr.register(user_id, device_id, ws, jwt_exp=jwt_exp):
        await ws.close(code=4003, reason="max_devices_exceeded")
        return

    relay = get_relay_manager()

    try:
        while True:
            msg = await ws.receive_json()
            msg_type = msg.get("type")

            # pong 응답 — 무시 (ping_loop이 전송 실패로 감지)
            if msg_type == "pong":
                continue

            # JWT 갱신 (클라이언트가 토큰 refresh 후 전송)
            if msg_type == "re_auth":
                token = msg.get("payload", {}).get("token", "")
                try:
                    payload = verify_jwt(token)
                    session_mgr.refresh_jwt(user_id, device_id, payload.get("exp", 0))
                    await ws.send_json({"type": "auth_ok"})
                except JWTError:
                    await ws.send_json({"type": "auth_failed"})
                continue

            await relay.handle_device_message(user_id, device_id, msg)
    except WebSocketDisconnect:
        logger.info("디바이스 WS 연결 해제: user=%s, device=%s", user_id, device_id)
    except Exception as e:
        logger.error("디바이스 WS 오류: user=%s, device=%s, error=%s", user_id, device_id, e)
    finally:
        session_mgr.unregister(user_id, device_id)
