"""세션 매니저 — 원격 디바이스 WS 세션 관리.

동시 접속 제한, ping/pong, 브로드캐스트.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

MAX_DEVICES_PER_USER = 5
PING_INTERVAL = 30  # 초


class SessionManager:
    """원격 디바이스 WS 세션 관리."""

    def __init__(self) -> None:
        # user_id → { device_id → WebSocket }
        self._sessions: dict[str, dict[str, WebSocket]] = {}
        self._ping_tasks: dict[str, asyncio.Task] = {}

    def register(self, user_id: str, device_id: str, ws: WebSocket) -> bool:
        """디바이스 세션 등록. 초과 시 False."""
        if user_id not in self._sessions:
            self._sessions[user_id] = {}

        user_sessions = self._sessions[user_id]

        # 같은 디바이스 재연결이면 교체
        if device_id in user_sessions:
            logger.info("디바이스 재연결: user=%s, device=%s", user_id, device_id)

        # 동시 세션 제한
        if device_id not in user_sessions and len(user_sessions) >= MAX_DEVICES_PER_USER:
            logger.warning("디바이스 수 초과: user=%s, count=%d", user_id, len(user_sessions))
            return False

        user_sessions[device_id] = ws
        logger.info("디바이스 등록: user=%s, device=%s (총 %d)", user_id, device_id, len(user_sessions))
        return True

    def unregister(self, user_id: str, device_id: str) -> None:
        """디바이스 세션 해제."""
        user_sessions = self._sessions.get(user_id)
        if user_sessions:
            user_sessions.pop(device_id, None)
            if not user_sessions:
                self._sessions.pop(user_id, None)
        logger.info("디바이스 해제: user=%s, device=%s", user_id, device_id)

    async def broadcast_to_devices(self, user_id: str, message: dict) -> None:
        """해당 사용자의 모든 디바이스에 메시지 전송."""
        user_sessions = self._sessions.get(user_id, {})
        dead: list[str] = []
        for device_id, ws in user_sessions.items():
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(device_id)
        for d in dead:
            self.unregister(user_id, d)

    async def send_to_device(
        self, user_id: str, device_id: str, message: dict
    ) -> bool:
        """특정 디바이스에 메시지 전송."""
        user_sessions = self._sessions.get(user_id, {})
        ws = user_sessions.get(device_id)
        if ws is None:
            return False
        try:
            await ws.send_json(message)
            return True
        except Exception:
            self.unregister(user_id, device_id)
            return False

    async def kill_session(self, user_id: str, device_id: str) -> None:
        """디바이스 세션 강제 종료."""
        user_sessions = self._sessions.get(user_id, {})
        ws = user_sessions.get(device_id)
        if ws:
            try:
                await ws.close(code=4003, reason="session_killed")
            except Exception:
                pass
            self.unregister(user_id, device_id)

    def get_device_count(self, user_id: str) -> int:
        return len(self._sessions.get(user_id, {}))
