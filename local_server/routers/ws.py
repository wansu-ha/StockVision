"""
WebSocket 라우터: React ↔ 로컬 서버 실시간 통신

수신 타입 (React → 로컬):
  strategy_toggle  { rule_id, is_active }
  config_update    { key, value }
  jwt_unlock       { jwt }

송신 타입 (로컬 → React):
  execution_result { ... }
  kiwoom_status    { connected, mode }
  alert            { level, message }
  config_loaded    {}
"""
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ws"])

_clients: Set[WebSocket] = set()


async def broadcast(message: dict) -> None:
    """연결된 모든 React 클라이언트에 메시지 전송"""
    dead = set()
    for ws in _clients:
        try:
            await ws.send_text(json.dumps(message, ensure_ascii=False))
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _clients.add(ws)
    logger.info(f"WS 연결: {ws.client} (총 {len(_clients)}개)")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            data = msg.get("data", {})

            if msg_type == "jwt_unlock":
                await _handle_jwt_unlock(data.get("jwt", ""))
            elif msg_type == "strategy_toggle":
                await _handle_strategy_toggle(data)
            elif msg_type == "config_update":
                await _handle_config_update(data)
            else:
                logger.warning(f"알 수 없는 WS 메시지 타입: {msg_type}")

    except WebSocketDisconnect:
        logger.info(f"WS 연결 해제: {ws.client}")
    finally:
        _clients.discard(ws)


async def _handle_jwt_unlock(jwt: str) -> None:
    from cloud.auth_client import AuthClient
    from storage.config_manager import ConfigManager
    from main import config_manager

    try:
        auth = AuthClient()
        cloud_config = auth.get_config(jwt)
        config_manager.load(cloud_config, jwt=jwt)
        await broadcast({"type": "config_loaded", "data": {}})
        logger.info("JWT unlock 완료 — 설정 로드됨")
    except Exception as e:
        await broadcast({"type": "alert", "data": {"level": "error", "message": f"설정 로드 실패: {e}"}})


async def _handle_strategy_toggle(data: dict) -> None:
    from main import config_manager
    rule_id   = data.get("rule_id")
    is_active = data.get("is_active", False)
    config_manager.set_rule_active(rule_id, is_active)


async def _handle_config_update(data: dict) -> None:
    from main import config_manager
    config_manager.update(data)
