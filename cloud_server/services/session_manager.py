"""세션 매니저 — 원격 디바이스 WS 세션 관리.

동시 접속 제한, ping/pong, JWT 만료 추적, 브로드캐스트.
"""
from __future__ import annotations

import asyncio
import logging
import time

from fastapi import WebSocket

logger = logging.getLogger(__name__)

MAX_DEVICES_PER_USER = 5
PING_INTERVAL = 30  # 초
PONG_TIMEOUT = 10  # pong 응답 대기 시간


class SessionManager:
    """원격 디바이스 WS 세션 관리."""

    def __init__(self) -> None:
        # user_id → { device_id → WebSocket }
        self._sessions: dict[str, dict[str, WebSocket]] = {}
        # "user_id:device_id" → asyncio.Task
        self._ping_tasks: dict[str, asyncio.Task] = {}
        # "user_id:device_id" → JWT exp timestamp (epoch)
        self._jwt_exp: dict[str, float] = {}

    def register(
        self, user_id: str, device_id: str, ws: WebSocket, jwt_exp: float = 0
    ) -> bool:
        """디바이스 세션 등록. 초과 시 False."""
        if user_id not in self._sessions:
            self._sessions[user_id] = {}

        user_sessions = self._sessions[user_id]

        # 같은 디바이스 재연결이면 기존 ping 정리 후 교체
        if device_id in user_sessions:
            self._cancel_ping(user_id, device_id)
            logger.info("디바이스 재연결: user=%s, device=%s", user_id, device_id)

        # 동시 세션 제한
        if device_id not in user_sessions and len(user_sessions) >= MAX_DEVICES_PER_USER:
            logger.warning("디바이스 수 초과: user=%s, count=%d", user_id, len(user_sessions))
            return False

        user_sessions[device_id] = ws
        key = f"{user_id}:{device_id}"
        if jwt_exp > 0:
            self._jwt_exp[key] = jwt_exp
        self._start_ping(user_id, device_id, ws)
        logger.info("디바이스 등록: user=%s, device=%s (총 %d)", user_id, device_id, len(user_sessions))
        return True

    def unregister(self, user_id: str, device_id: str) -> None:
        """디바이스 세션 해제."""
        self._cancel_ping(user_id, device_id)
        key = f"{user_id}:{device_id}"
        self._jwt_exp.pop(key, None)
        user_sessions = self._sessions.get(user_id)
        if user_sessions:
            user_sessions.pop(device_id, None)
            if not user_sessions:
                self._sessions.pop(user_id, None)
        logger.info("디바이스 해제: user=%s, device=%s", user_id, device_id)

    def refresh_jwt(self, user_id: str, device_id: str, jwt_exp: float) -> None:
        """JWT 갱신 시 만료 시각 업데이트."""
        key = f"{user_id}:{device_id}"
        self._jwt_exp[key] = jwt_exp
        logger.debug("JWT 갱신: user=%s, device=%s, exp=%s", user_id, device_id, jwt_exp)

    # ── ping/pong ──

    def _start_ping(self, user_id: str, device_id: str, ws: WebSocket) -> None:
        key = f"{user_id}:{device_id}"
        task = asyncio.create_task(self._ping_loop(user_id, device_id, ws))
        self._ping_tasks[key] = task

    def _cancel_ping(self, user_id: str, device_id: str) -> None:
        key = f"{user_id}:{device_id}"
        task = self._ping_tasks.pop(key, None)
        if task and not task.done():
            task.cancel()

    async def _ping_loop(self, user_id: str, device_id: str, ws: WebSocket) -> None:
        """주기적 ping 전송 + JWT 만료 검사."""
        key = f"{user_id}:{device_id}"
        try:
            while True:
                await asyncio.sleep(PING_INTERVAL)

                # JWT 만료 검사
                exp = self._jwt_exp.get(key, 0)
                if exp > 0 and time.time() > exp:
                    logger.info("JWT 만료 — 세션 종료: user=%s, device=%s", user_id, device_id)
                    try:
                        await ws.send_json({"type": "auth_expired"})
                        await ws.close(code=4004, reason="token_expired")
                    except Exception:
                        pass
                    self.unregister(user_id, device_id)
                    return

                # ping 전송
                try:
                    await ws.send_json({"type": "ping", "ts": int(time.time())})
                except Exception:
                    logger.info("ping 전송 실패 — 세션 종료: user=%s, device=%s", user_id, device_id)
                    self.unregister(user_id, device_id)
                    return
        except asyncio.CancelledError:
            pass

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
