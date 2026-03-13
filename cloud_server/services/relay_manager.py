"""릴레이 매니저 — 로컬↔원격 메시지 라우팅.

로컬 서버 WS 연결 레지스트리, 메시지 라우팅, 오프라인 명령 큐 관리.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime

from fastapi import WebSocket
from sqlalchemy.orm import Session

from cloud_server.core.database import get_db_session

logger = logging.getLogger(__name__)


class RateLimiter:
    """인메모리 rate limiter (user_id 기반)."""

    def __init__(self, max_commands_per_min: int = 10, max_total_per_min: int = 60):
        self._max_cmd = max_commands_per_min
        self._max_total = max_total_per_min
        # user_id → list of timestamps
        self._cmd_log: dict[str, list[float]] = defaultdict(list)
        self._total_log: dict[str, list[float]] = defaultdict(list)

    def check(self, user_id: str, msg_type: str) -> bool:
        """요청 허용 여부. False면 rate limit 초과."""
        now = time.time()
        cutoff = now - 60

        # 전체 메시지 제한
        total = self._total_log[user_id]
        total[:] = [t for t in total if t > cutoff]
        if len(total) >= self._max_total:
            return False
        total.append(now)

        # command 타입 추가 제한
        if msg_type == "command":
            cmds = self._cmd_log[user_id]
            cmds[:] = [t for t in cmds if t > cutoff]
            if len(cmds) >= self._max_cmd:
                return False
            cmds.append(now)

        return True

    def cleanup(self, user_id: str) -> None:
        """연결 해제 시 정리."""
        self._cmd_log.pop(user_id, None)
        self._total_log.pop(user_id, None)


class RelayManager:
    """로컬 서버 WS 연결 레지스트리 + 메시지 라우팅."""

    def __init__(self) -> None:
        self._local_connections: dict[str, WebSocket] = {}
        self._rate_limiter = RateLimiter()

    def register_local(self, user_id: str, ws: WebSocket) -> None:
        """로컬 서버 WS 등록."""
        old = self._local_connections.get(user_id)
        if old is not None:
            logger.warning("로컬 이중 연결 교체: user=%s", user_id)
        self._local_connections[user_id] = ws
        logger.info("로컬 등록: user=%s", user_id)

    def unregister_local(self, user_id: str) -> None:
        """로컬 서버 WS 해제."""
        self._local_connections.pop(user_id, None)
        self._rate_limiter.cleanup(user_id)
        logger.info("로컬 해제: user=%s", user_id)

    def is_local_online(self, user_id: str) -> bool:
        return user_id in self._local_connections

    async def send_to_local(self, user_id: str, message: dict) -> bool:
        """로컬 서버에 메시지 전송. 실패 시 False."""
        ws = self._local_connections.get(user_id)
        if ws is None:
            return False
        try:
            await ws.send_json(message)
            return True
        except Exception:
            logger.warning("로컬 전송 실패: user=%s", user_id)
            return False

    async def handle_local_message(self, user_id: str, msg: dict) -> None:
        """로컬 서버에서 받은 메시지 처리."""
        msg_type = msg.get("type")

        if msg_type == "heartbeat":
            await self._handle_heartbeat(user_id, msg)
        elif msg_type == "state":
            await self._relay_to_devices(user_id, msg)
        elif msg_type == "alert":
            await self._relay_to_devices(user_id, msg)
        elif msg_type == "command_ack":
            await self._relay_command_ack(user_id, msg)
        else:
            logger.debug("알 수 없는 로컬 메시지 타입: %s", msg_type)

    async def handle_device_message(
        self, user_id: str, device_id: str, msg: dict
    ) -> None:
        """원격 디바이스에서 받은 메시지 처리."""
        msg_type = msg.get("type")

        if not self._rate_limiter.check(user_id, msg_type or ""):
            session_mgr = get_session_manager()
            await session_mgr.send_to_device(
                user_id, device_id,
                {"type": "error", "payload": {"code": 429, "message": "rate limit exceeded"}},
            )
            return

        if msg_type == "command":
            await self._handle_command(user_id, device_id, msg)
        elif msg_type == "sync_request":
            await self.send_to_local(user_id, msg)
        elif msg_type == "ack":
            pass  # 로깅만
        else:
            logger.debug("알 수 없는 디바이스 메시지 타입: %s", msg_type)

        # 감사 로그
        if msg_type in ("command", "sync_request"):
            self._write_audit_log(user_id, device_id, msg_type, msg.get("payload"))

    async def flush_pending_commands(self, user_id: str) -> None:
        """로컬 재연결 시 pending 큐 flush."""
        try:
            db = get_db_session()
            try:
                from cloud_server.models.pending_command import PendingCommand
                pending = (
                    db.query(PendingCommand)
                    .filter(
                        PendingCommand.user_id == user_id,
                        PendingCommand.status == "pending",
                    )
                    .order_by(PendingCommand.created_at)
                    .all()
                )
                for cmd in pending:
                    sent = await self.send_to_local(user_id, {
                        "type": "command",
                        "id": f"pending-{cmd.id}",
                        "payload": cmd.payload,
                    })
                    if sent:
                        cmd.status = "executed"
                        cmd.executed_at = datetime.utcnow()
                if pending:
                    db.commit()
                    logger.info("pending 큐 flush: user=%s, count=%d", user_id, len(pending))
            finally:
                db.close()
        except Exception as e:
            logger.error("pending 큐 flush 실패: %s", e)

    # ── private ──

    async def _handle_heartbeat(self, user_id: str, msg: dict) -> None:
        """WS heartbeat 처리 → HeartbeatService 호출 → ack 응답."""
        try:
            db = get_db_session()
            try:
                from cloud_server.services.heartbeat_service import record_heartbeat
                payload = msg.get("payload", {})
                result = record_heartbeat(user_id, payload, db)
                await self.send_to_local(user_id, {
                    "type": "heartbeat_ack",
                    "id": msg.get("id"),
                    "ts": datetime.utcnow().isoformat(),
                    "payload": result,
                })
            finally:
                db.close()
        except Exception as e:
            logger.error("heartbeat 처리 실패: %s", e)

    async def _relay_to_devices(self, user_id: str, msg: dict) -> None:
        """로컬 → 디바이스 브로드캐스트."""
        session_mgr = get_session_manager()
        await session_mgr.broadcast_to_devices(user_id, msg)

    async def _relay_command_ack(self, user_id: str, msg: dict) -> None:
        """command_ack를 해당 디바이스로 전달."""
        payload = msg.get("payload", {})
        device_id = payload.get("device_id")
        if device_id:
            session_mgr = get_session_manager()
            await session_mgr.send_to_device(user_id, device_id, msg)
        else:
            # device_id 없으면 모든 디바이스에 브로드캐스트
            session_mgr = get_session_manager()
            await session_mgr.broadcast_to_devices(user_id, msg)

    async def _handle_command(
        self, user_id: str, device_id: str, msg: dict
    ) -> None:
        """디바이스 → 로컬 명령 전달 (오프라인 시 큐잉)."""
        sent = await self.send_to_local(user_id, msg)
        if not sent:
            # 오프라인 → pending 큐 저장
            self._save_pending_command(user_id, device_id, msg)
            session_mgr = get_session_manager()
            await session_mgr.send_to_device(user_id, device_id, {
                "type": "command_queued",
                "id": msg.get("id"),
                "payload": {"message": "로컬 오프라인 — 명령이 큐에 저장되었습니다."},
            })

    def _save_pending_command(self, user_id: str, device_id: str, msg: dict) -> None:
        """명령을 pending_commands 테이블에 저장."""
        try:
            db = get_db_session()
            try:
                from cloud_server.models.pending_command import PendingCommand
                cmd = PendingCommand(
                    user_id=user_id,
                    command_type=msg.get("payload", {}).get("action", "unknown"),
                    payload=msg.get("payload", {}),
                )
                db.add(cmd)
                db.commit()
                logger.info("pending 명령 저장: user=%s, action=%s", user_id, cmd.command_type)
            finally:
                db.close()
        except Exception as e:
            logger.error("pending 명령 저장 실패: %s", e)

    def _write_audit_log(
        self, user_id: str, device_id: str | None, action: str, detail: dict | None
    ) -> None:
        """감사 로그 기록."""
        try:
            db = get_db_session()
            try:
                from cloud_server.models.audit_log import AuditLog
                log = AuditLog(
                    user_id=user_id,
                    device_id=device_id,
                    action=action,
                    detail=detail,
                )
                db.add(log)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error("감사 로그 기록 실패: %s", e)


# ── 싱글톤 ──

_relay_manager: RelayManager | None = None
_session_manager = None  # SessionManager (순환 import 방지)


def get_relay_manager() -> RelayManager:
    global _relay_manager
    if _relay_manager is None:
        _relay_manager = RelayManager()
    return _relay_manager


def get_session_manager():
    """SessionManager 싱글톤 반환 (순환 import 방지)."""
    global _session_manager
    if _session_manager is None:
        from cloud_server.services.session_manager import SessionManager
        _session_manager = SessionManager()
    return _session_manager
