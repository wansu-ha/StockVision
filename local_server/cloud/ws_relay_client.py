"""클라우드 WS 릴레이 클라이언트.

클라우드 서버의 /ws/relay에 연결하여:
- heartbeat를 WS로 전송
- 상태(state) 메시지를 전송
- 원격 명령(command)을 수신하여 처리
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from uuid import uuid4

import websockets
from websockets.asyncio.client import ClientConnection

from local_server.config import get_config

logger = logging.getLogger(__name__)

# 재연결 backoff 설정
_MIN_BACKOFF = 1
_MAX_BACKOFF = 60


class WsRelayClient:
    """클라우드 WS 릴레이 클라이언트."""

    def __init__(self) -> None:
        self._ws: ClientConnection | None = None
        self._connected = False
        self._running = False
        self._task: asyncio.Task | None = None
        self._backoff = _MIN_BACKOFF
        self._jwt_token: str = ""
        self._cloud_ws_url: str = ""
        # 외부에서 등록하는 command 핸들러
        self._command_handler: Callable[[dict], Coroutine] | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def set_command_handler(self, handler: Callable[[dict], Coroutine]) -> None:
        """command 수신 시 호출할 핸들러 등록."""
        self._command_handler = handler

    async def start(self, cloud_ws_url: str, jwt_token: str) -> None:
        """WS 연결 시작 (무한 루프)."""
        self._cloud_ws_url = cloud_ws_url
        self._jwt_token = jwt_token
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """WS 연결 종료."""
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("WS 릴레이 클라이언트 종료")

    def update_token(self, new_token: str) -> None:
        """JWT 토큰 갱신 (refresh 후 호출)."""
        self._jwt_token = new_token

    async def send(self, message: dict) -> bool:
        """메시지 전송. 실패 시 False."""
        if not self._ws or not self._connected:
            return False
        try:
            await self._ws.send(json.dumps(message, ensure_ascii=False))
            return True
        except Exception as e:
            logger.warning("WS 전송 실패: %s", e)
            self._connected = False
            return False

    async def send_state(self, state_data: dict, encrypted_for: dict | None = None) -> bool:
        """상태 메시지 전송."""
        msg: dict[str, Any] = {
            "v": 1,
            "type": "state",
            "id": str(uuid4())[:8],
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": state_data,
        }
        if encrypted_for:
            msg["encrypted_for"] = encrypted_for
        return await self.send(msg)

    async def send_alert(self, alert_data: dict) -> bool:
        """경고 메시지 전송."""
        return await self.send({
            "v": 1,
            "type": "alert",
            "id": str(uuid4())[:8],
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": alert_data,
        })

    async def send_heartbeat(self, payload: dict) -> None:
        """WS heartbeat 전송."""
        await self.send({
            "v": 1,
            "type": "heartbeat",
            "id": str(uuid4())[:8],
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        })

    async def send_command_ack(self, command_id: str, result: dict) -> bool:
        """명령 ACK 전송."""
        return await self.send({
            "v": 1,
            "type": "command_ack",
            "id": str(uuid4())[:8],
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": {"command_id": command_id, **result},
        })

    # ── private ──

    async def _run_loop(self) -> None:
        """연결 유지 루프 (재연결 포함)."""
        while self._running:
            try:
                await self._connect()
                self._backoff = _MIN_BACKOFF
                await self._recv_loop()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("WS 연결 끊김: %s (재연결 %ds 후)", e, self._backoff)

            if not self._running:
                break

            self._connected = False
            await asyncio.sleep(self._backoff)
            self._backoff = min(self._backoff * 2, _MAX_BACKOFF)

    async def _connect(self) -> None:
        """WS 연결 수립 + auth."""
        logger.info("클라우드 WS 연결 중: %s", self._cloud_ws_url)
        self._ws = await websockets.connect(self._cloud_ws_url)

        # 첫 메시지: auth
        auth_msg = {
            "type": "auth",
            "payload": {"token": self._jwt_token},
        }
        await self._ws.send(json.dumps(auth_msg))
        self._connected = True
        self._backoff = _MIN_BACKOFF
        logger.info("클라우드 WS 연결 완료")

    async def _recv_loop(self) -> None:
        """메시지 수신 루프."""
        if not self._ws:
            return
        async for raw in self._ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            if msg_type == "heartbeat_ack":
                self._handle_heartbeat_ack(msg)
            elif msg_type == "command":
                await self._handle_command(msg)
            elif msg_type == "error":
                logger.warning("클라우드 오류: %s", msg.get("payload"))
            else:
                logger.debug("알 수 없는 메시지 타입: %s", msg_type)

    def _handle_heartbeat_ack(self, msg: dict) -> None:
        """heartbeat_ack 처리 → 버전 체크는 heartbeat 모듈에 위임."""
        # heartbeat 모듈에서 이 데이터를 polling 대신 받을 수 있도록
        # 이벤트나 콜백으로 전달할 수 있음. 초기에는 로깅만.
        logger.debug("heartbeat_ack 수신")

    async def _handle_command(self, msg: dict) -> None:
        """원격 명령 수신 → 핸들러 호출."""
        if self._command_handler:
            try:
                await self._command_handler(msg)
            except Exception as e:
                logger.error("command 핸들러 오류: %s", e)
        else:
            logger.warning("command 핸들러 미등록, 무시: %s", msg.get("payload"))


# 싱글톤
_ws_client: WsRelayClient | None = None


def get_ws_relay_client() -> WsRelayClient | None:
    """WS 릴레이 클라이언트 인스턴스 반환."""
    return _ws_client


def set_ws_relay_client(client: WsRelayClient) -> None:
    """WS 릴레이 클라이언트 인스턴스 설정."""
    global _ws_client
    _ws_client = client
