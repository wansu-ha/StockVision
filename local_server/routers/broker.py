"""브로커 라우터.

POST /api/broker/reconnect — 브로커 수동 재연결
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from local_server.core.local_auth import require_local_secret

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/reconnect",
    summary="브로커 수동 재연결",
)
async def reconnect_broker(
    request: Request,
    _: None = Depends(require_local_secret),
) -> dict[str, Any]:
    """기존 브로커 연결을 해제하고 새로 연결한다.

    엔진 실행 중에는 안전을 위해 거부한다 (409 Conflict).
    키 변경 후 서버 재시작 없이 즉시 재연결할 때 사용한다.
    """
    engine = getattr(request.app.state, "engine", None)
    if engine and engine.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="엔진 실행 중에는 재연결할 수 없습니다. 먼저 중지하세요.",
        )

    # 기존 브로커 해제
    old_broker = getattr(request.app.state, "broker", None)
    if old_broker:
        try:
            await old_broker.disconnect()
        except Exception as e:
            logger.warning("기존 브로커 해제 중 오류: %s", e)
        request.app.state.broker = None

    # 새 브로커 생성 + 연결
    try:
        from local_server.broker.factory import create_broker_from_config
        broker = create_broker_from_config()
        await broker.connect()
    except ValueError as e:
        request.app.state.broker_reason = "no_credentials"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"자격증명 미등록: {e}",
        ) from e
    except Exception as e:
        request.app.state.broker_reason = "connect_failed"
        logger.error("브로커 재연결 실패: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"브로커 연결 실패: {e}",
        ) from e

    request.app.state.broker = broker
    request.app.state.broker_reason = "connected"
    logger.info("브로커 재연결 완료")

    return {
        "success": True,
        "data": {"broker": "connected"},
        "count": 1,
    }
