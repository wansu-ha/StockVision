"""매매 라우터.

POST /api/strategy/start  — 전략 엔진 시작
POST /api/strategy/stop   — 전략 엔진 중지
POST /api/strategy/kill   — Kill Switch (신규 중지 또는 미체결 취소)
POST /api/strategy/unlock — 손실 락 해제
POST /api/trading/order   — 수동 주문 발행
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from local_server.routers.status import is_strategy_running, set_strategy_running
from local_server.storage.credential import has_credential, KEY_APP_KEY
from local_server.storage.log_db import get_log_db, LOG_TYPE_ORDER, LOG_TYPE_STRATEGY

logger = logging.getLogger(__name__)

router = APIRouter()


class KillSwitchRequest(BaseModel):
    """Kill Switch 요청 바디."""

    mode: Literal["STOP_NEW", "CANCEL_OPEN"] = Field(
        ...,
        description=(
            "STOP_NEW: 신규 주문 차단만 (기존 미체결 유지)\n"
            "CANCEL_OPEN: 신규 차단 + 미체결 주문 전량 취소"
        ),
    )


class OrderRequest(BaseModel):
    """수동 주문 요청 바디."""

    symbol: str = Field(..., description="종목 코드 (예: 005930)")
    side: Literal["BUY", "SELL"] = Field(..., description="매수/매도")
    qty: int = Field(..., gt=0, description="주문 수량")
    order_type: Literal["MARKET", "LIMIT"] = Field(
        "MARKET", alias="type", description="주문 유형"
    )
    limit_price: int | None = Field(None, description="지정가 (LIMIT 주문 시 필수)")

    model_config = {"populate_by_name": True}


@router.post(
    "/strategy/start",
    summary="전략 엔진 시작",
)
async def start_strategy() -> dict[str, Any]:
    """전략 엔진을 시작한다.

    자격증명이 없으면 400 오류를 반환한다.
    이미 실행 중이면 409를 반환한다.
    """
    if not has_credential(KEY_APP_KEY):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자격증명이 없습니다. /api/auth/token으로 먼저 인증하세요.",
        )

    if is_strategy_running():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="전략 엔진이 이미 실행 중입니다.",
        )

    # TODO: Unit 3 전략 엔진 연동
    set_strategy_running(True)
    get_log_db().write(LOG_TYPE_STRATEGY, "전략 엔진 시작")
    logger.info("전략 엔진 시작")

    return {"success": True, "data": {"strategy_engine": "running"}, "count": 1}


@router.post(
    "/strategy/stop",
    summary="전략 엔진 중지",
)
async def stop_strategy() -> dict[str, Any]:
    """전략 엔진을 중지한다."""
    if not is_strategy_running():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="전략 엔진이 실행 중이 아닙니다.",
        )

    # TODO: Unit 3 전략 엔진 연동
    set_strategy_running(False)
    get_log_db().write(LOG_TYPE_STRATEGY, "전략 엔진 중지")
    logger.info("전략 엔진 중지")

    return {"success": True, "data": {"strategy_engine": "stopped"}, "count": 1}


@router.post(
    "/strategy/kill",
    summary="Kill Switch — 전략 엔진 긴급 제동",
)
async def kill_strategy(body: KillSwitchRequest) -> dict[str, Any]:
    """전략 엔진에 Kill Switch를 발동한다.

    - STOP_NEW: 신규 주문 발행만 차단. 미체결 주문은 그대로 유지.
    - CANCEL_OPEN: 신규 주문 차단 + 미체결 주문 전량 취소 (Unit 1 BrokerAdapter 연동 후 구현).
    """
    log_db = get_log_db()

    if body.mode == "STOP_NEW":
        # 신규 주문 차단 — 전략 엔진을 중지 상태로 전환
        set_strategy_running(False)
        log_db.write(LOG_TYPE_STRATEGY, f"Kill Switch 발동 (모드: {body.mode})")
        logger.warning("Kill Switch 발동: STOP_NEW")
        return {
            "success": True,
            "data": {"mode": body.mode, "strategy_engine": "stopped", "open_orders": "retained"},
            "count": 1,
        }

    # CANCEL_OPEN — 전략 중지 + 미체결 취소 (브로커 연동 필요)
    set_strategy_running(False)
    log_db.write(LOG_TYPE_STRATEGY, f"Kill Switch 발동 (모드: {body.mode})")
    logger.warning("Kill Switch 발동: CANCEL_OPEN (미체결 취소는 Unit 1 완성 후 실제 동작)")
    # TODO: Unit 1 BrokerAdapter.cancel_order() 루프 연동
    return {
        "success": True,
        "data": {
            "mode": body.mode,
            "strategy_engine": "stopped",
            "open_orders": "cancel_requested_stub",
            "note": "stub — Unit 1 완성 후 실제 취소 처리로 교체",
        },
        "count": 1,
    }


@router.post(
    "/strategy/unlock",
    summary="손실 락 해제",
)
async def unlock_strategy() -> dict[str, Any]:
    """손실 한도 초과로 잠긴 전략 엔진의 락을 해제한다.

    락 해제 후 전략 엔진은 재시작 대기 상태가 된다.
    실제 재시작은 /api/strategy/start 호출 필요.
    """
    # TODO: Unit 3 전략 엔진의 손실 락 상태 관리 연동
    log_db = get_log_db()
    log_db.write(LOG_TYPE_STRATEGY, "손실 락 해제")
    logger.info("손실 락 해제 완료")
    return {
        "success": True,
        "data": {"message": "손실 락이 해제되었습니다. /api/strategy/start로 재시작하세요."},
        "count": 1,
    }


@router.post(
    "/trading/order",
    summary="수동 주문 발행",
)
async def place_order(body: OrderRequest) -> dict[str, Any]:
    """수동으로 주문을 발행한다.

    LIMIT 주문 시 limit_price가 필수다.
    """
    if body.order_type == "LIMIT" and body.limit_price is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="LIMIT 주문에는 limit_price가 필요합니다.",
        )

    if not has_credential(KEY_APP_KEY):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자격증명이 없습니다. /api/auth/token으로 먼저 인증하세요.",
        )

    # TODO: Unit 1 BrokerAdapter.place_order() 연동
    log_db = get_log_db()
    log_db.write(
        LOG_TYPE_ORDER,
        f"수동 주문: {body.side} {body.qty}주 {body.symbol} ({body.order_type})",
        symbol=body.symbol,
        meta={
            "side": body.side,
            "qty": body.qty,
            "order_type": body.order_type,
            "limit_price": body.limit_price,
        },
    )
    logger.info(
        "수동 주문: %s %d주 %s (%s)",
        body.side,
        body.qty,
        body.symbol,
        body.order_type,
    )

    return {
        "success": True,
        "data": {
            "order_no": "stub_order_001",
            "symbol": body.symbol,
            "side": body.side,
            "qty": body.qty,
            "type": body.order_type,
            "limit_price": body.limit_price,
            "note": "stub — Unit 1 완성 후 실제 주문으로 교체",
        },
        "count": 1,
    }
