"""WebSocket 라우터.

WS /ws — 실시간 가격/주문/잔고 스트림

클라이언트가 연결하면 ConnectionManager에 등록되어
브로드캐스트 메시지를 수신할 수 있다.

메시지 형식:
  {
    "type": "price_update" | "execution" | "status_change" | "system",
    "data": { ... }
  }

type 값 규칙:
  - price_update : 호가/현재가 갱신 이벤트 (QuoteEvent)
  - execution    : 주문 체결 이벤트
  - status_change: 주문 상태 변경 이벤트
  - system       : 서버 시스템 메시지 (연결, 에러 등)

side 값: "buy" | "sell" (소문자)
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import hmac

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# WS 메시지 타입 상수 — 브로드캐스트 시 이 상수를 사용한다
WS_TYPE_PRICE_UPDATE = "price_update"    # 호가/현재가 갱신 (QuoteEvent)
WS_TYPE_EXECUTION = "execution"          # 체결 이벤트
WS_TYPE_STATUS_CHANGE = "status_change"  # 주문 상태 변경
WS_TYPE_ALERT = "alert"                  # 실시간 경고


class ConnectionManager:
    """WebSocket 연결 관리자.

    연결된 모든 클라이언트에 메시지를 브로드캐스트한다.
    """

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        """클라이언트 연결을 수락하고 목록에 추가한다."""
        await ws.accept()
        self._connections.append(ws)
        logger.info("WebSocket 클라이언트 연결: %s (총 %d개)", id(ws), len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        """클라이언트 연결을 목록에서 제거한다."""
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info("WebSocket 클라이언트 해제: %s (총 %d개)", id(ws), len(self._connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """모든 연결된 클라이언트에 메시지를 전송한다.

        전송 실패한 클라이언트는 목록에서 제거한다.
        """
        if not self._connections:
            return

        text = json.dumps(message, ensure_ascii=False)
        broken: list[WebSocket] = []

        for ws in list(self._connections):
            try:
                await ws.send_text(text)
            except Exception as e:
                logger.debug("브로드캐스트 실패 (클라이언트 제거): %s", e)
                broken.append(ws)

        for ws in broken:
            self.disconnect(ws)

    def connection_count(self) -> int:
        """현재 연결된 클라이언트 수를 반환한다."""
        return len(self._connections)


# 전역 연결 관리자 (앱 전체에서 공유)
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """전역 ConnectionManager 인스턴스를 반환한다."""
    return manager


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """WebSocket 엔드포인트.

    AS-1: 연결 후 5초 내 첫 프레임으로 auth 메시지를 받아 인증한다.
    query param 대신 메시지 기반 인증 (로그/히스토리 노출 방지).
    """
    await ws.accept()

    # 첫 프레임 인증 (5초 타임아웃)
    expected = ws.app.state.local_secret
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=5.0)
        auth_msg = json.loads(raw)
        if auth_msg.get("type") != "auth" or not hmac.compare_digest(
            auth_msg.get("secret", ""), expected
        ):
            await ws.close(code=4003, reason="Unauthorized")
            return
    except asyncio.TimeoutError:
        await ws.close(code=4003, reason="Auth timeout")
        return
    except Exception:
        await ws.close(code=4003, reason="Auth failed")
        return

    # 인증 성공 → ConnectionManager에 등록
    manager._connections.append(ws)
    logger.info("WebSocket 클라이언트 연결: %s (총 %d개)", id(ws), len(manager._connections))
    try:
        # 연결 확인 메시지
        await ws.send_json(
            {
                "type": "system",
                "data": {
                    "message": "StockVision 로컬 서버에 연결되었습니다.",
                    "connections": manager.connection_count(),
                },
            }
        )

        # 메시지 수신 루프
        while True:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=60.0)
                msg = json.loads(raw)
                msg_type = msg.get("type", "unknown")

                # ping 처리
                if msg_type == "ping":
                    await ws.send_json({"type": "pong", "data": {}})
                else:
                    # 기타 메시지는 로깅만 (추후 확장)
                    logger.debug("WebSocket 수신: %s", msg_type)

            except asyncio.TimeoutError:
                # 60초 동안 메시지 없으면 ping 전송
                await ws.send_json({"type": "ping", "data": {}})

    except WebSocketDisconnect:
        logger.info("WebSocket 클라이언트 정상 해제")
    except Exception as e:
        logger.error("WebSocket 오류: %s", e)
    finally:
        manager.disconnect(ws)
