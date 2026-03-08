"""매매 라우터.

POST /api/strategy/start  — 전략 엔진 시작
POST /api/strategy/stop   — 전략 엔진 중지
POST /api/strategy/kill   — Kill Switch (신규 중지 또는 미체결 취소)
POST /api/strategy/unlock — 손실 락 해제
POST /api/trading/order   — 수동 주문 발행
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from local_server.core.local_auth import require_local_secret
from local_server.engine import StrategyEngine, KillSwitchLevel, ExecutionResult
from local_server.broker.factory import create_broker_from_config
from local_server.routers.ws import get_connection_manager, WS_TYPE_EXECUTION
from local_server.storage.log_db import get_log_db, LOG_TYPE_FILL, LOG_TYPE_ORDER, LOG_TYPE_STRATEGY
from local_server.storage.rules_cache import get_rules_cache
from sv_core.broker.models import OrderSide, OrderType

logger = logging.getLogger(__name__)

router = APIRouter()


# ── 헬퍼 ──


def _get_engine(request: Request) -> StrategyEngine | None:
    """app.state에서 엔진 인스턴스를 가져온다."""
    return getattr(request.app.state, "engine", None)


def _on_execution(result: ExecutionResult) -> None:
    """엔진 실행 결과 콜백 — logs.db 기록 + WS 브로드캐스트."""
    log_db = get_log_db()
    log_db.write(
        LOG_TYPE_FILL,
        f"{result.side} {result.symbol} — {result.status.value}: {result.message}",
        symbol=result.symbol,
        meta={
            "rule_id": result.rule_id,
            "side": result.side,
            "order_id": result.order_id,
            "status": result.status.value,
            "realized_pnl": str(result.realized_pnl) if result.realized_pnl else None,
        },
    )

    ws_msg = {
        "type": WS_TYPE_EXECUTION,
        "data": {
            "rule_id": result.rule_id,
            "symbol": result.symbol,
            "side": result.side.lower(),
            "status": result.status.value,
            "order_id": result.order_id,
            "message": result.message,
        },
    }
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(get_connection_manager().broadcast(ws_msg))
    except RuntimeError:
        pass


# ── 요청 모델 ──


class KillSwitchRequest(BaseModel):
    """Kill Switch 요청 바디."""

    mode: Literal["STOP_NEW", "CANCEL_OPEN", "OFF"] = Field(
        ...,
        description=(
            "STOP_NEW: 신규 주문 차단만 (기존 미체결 유지)\n"
            "CANCEL_OPEN: 신규 차단 + 미체결 주문 전량 취소\n"
            "OFF: Kill Switch 해제 (수동 재개)"
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


# ── 전략 엔진 ──


@router.post(
    "/strategy/start",
    summary="전략 엔진 시작",
)
async def start_strategy(request: Request, _: None = Depends(require_local_secret)) -> dict[str, Any]:
    """전략 엔진을 시작한다.

    브로커 자격증명으로 어댑터를 생성하고, 규칙 캐시를 로드한 뒤 엔진을 시작한다.
    """
    engine = _get_engine(request)
    if engine and engine.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="전략 엔진이 이미 실행 중입니다.",
        )

    try:
        broker = create_broker_from_config()
        await broker.connect()
    except (ValueError, ConnectionError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"브로커 연결 실패: {e}",
        ) from e

    engine = StrategyEngine(broker)
    engine.set_rules(get_rules_cache().get_rules())
    engine.set_on_execution(_on_execution)
    request.app.state.engine = engine
    request.app.state.broker = broker

    await engine.start()

    get_log_db().write(LOG_TYPE_STRATEGY, "전략 엔진 시작")
    logger.info("전략 엔진 시작")
    return {"success": True, "data": {"strategy_engine": "running"}, "count": 1}


@router.post(
    "/strategy/stop",
    summary="전략 엔진 중지",
)
async def stop_strategy(request: Request, _: None = Depends(require_local_secret)) -> dict[str, Any]:
    """전략 엔진을 중지하고 브로커 연결을 해제한다."""
    engine = _get_engine(request)
    if not engine or not engine.is_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="전략 엔진이 실행 중이 아닙니다.",
        )

    await engine.stop()

    broker = getattr(request.app.state, "broker", None)
    if broker:
        await broker.disconnect()
        request.app.state.broker = None

    request.app.state.engine = None

    get_log_db().write(LOG_TYPE_STRATEGY, "전략 엔진 중지")
    logger.info("전략 엔진 중지")
    return {"success": True, "data": {"strategy_engine": "stopped"}, "count": 1}


@router.post(
    "/strategy/kill",
    summary="Kill Switch — 전략 엔진 긴급 제동",
)
async def kill_strategy(
    body: KillSwitchRequest,
    request: Request,
    _: None = Depends(require_local_secret),
) -> dict[str, Any]:
    """전략 엔진에 Kill Switch를 발동/해제한다.

    - STOP_NEW: 신규 주문 차단. 엔진은 계속 평가 (모니터링 유지).
    - CANCEL_OPEN: 신규 차단 + 미체결 주문 전량 취소.
    - OFF: Kill Switch 해제 (수동 재개).
    """
    engine = _get_engine(request)
    log_db = get_log_db()

    _LEVEL_MAP = {
        "STOP_NEW": KillSwitchLevel.STOP_NEW,
        "CANCEL_OPEN": KillSwitchLevel.CANCEL_OPEN,
        "OFF": KillSwitchLevel.OFF,
    }
    level = _LEVEL_MAP[body.mode]

    if engine:
        engine.safeguard.set_kill_switch(level)

    log_db.write(LOG_TYPE_STRATEGY, f"Kill Switch: {body.mode}")
    logger.warning("Kill Switch: %s", body.mode)

    result_data: dict[str, Any] = {"mode": body.mode, "open_orders": "retained"}

    # CANCEL_OPEN: 미체결 주문 전량 취소
    if body.mode == "CANCEL_OPEN":
        broker = getattr(request.app.state, "broker", None)
        cancelled = 0
        if broker and broker.is_connected:
            try:
                open_orders = await broker.get_open_orders()
                for order in open_orders:
                    try:
                        await broker.cancel_order(order.order_id)
                        cancelled += 1
                    except Exception as e:
                        logger.error("미체결 취소 실패 (order_id=%s): %s", order.order_id, e)
            except Exception as e:
                logger.error("미체결 조회 실패: %s", e)
        result_data["open_orders"] = f"cancelled_{cancelled}"

    return {"success": True, "data": result_data, "count": 1}


@router.post(
    "/strategy/unlock",
    summary="손실 락 해제",
)
async def unlock_strategy(request: Request, _: None = Depends(require_local_secret)) -> dict[str, Any]:
    """손실 한도 초과로 잠긴 전략 엔진의 락을 해제한다."""
    engine = _get_engine(request)
    if engine:
        engine.safeguard.unlock_loss_lock()

    log_db = get_log_db()
    log_db.write(LOG_TYPE_STRATEGY, "손실 락 해제")
    logger.info("손실 락 해제 완료")
    return {
        "success": True,
        "data": {"message": "손실 락이 해제되었습니다."},
        "count": 1,
    }


# ── 수동 주문 ──


@router.post(
    "/trading/order",
    summary="수동 주문 발행",
)
async def place_order(
    body: OrderRequest,
    request: Request,
    _: None = Depends(require_local_secret),
) -> dict[str, Any]:
    """수동으로 주문을 발행한다."""
    if body.order_type == "LIMIT" and body.limit_price is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="LIMIT 주문에는 limit_price가 필요합니다.",
        )

    broker = getattr(request.app.state, "broker", None)
    if not broker or not broker.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="브로커가 연결되어 있지 않습니다. 전략 엔진을 먼저 시작하세요.",
        )

    order_side = OrderSide.BUY if body.side == "BUY" else OrderSide.SELL
    order_type = OrderType.LIMIT if body.order_type == "LIMIT" else OrderType.MARKET
    limit_price = Decimal(str(body.limit_price)) if body.limit_price else None
    client_order_id = f"manual-{uuid.uuid4().hex[:8]}"

    try:
        result = await broker.place_order(
            client_order_id=client_order_id,
            symbol=body.symbol,
            side=order_side,
            order_type=order_type,
            qty=body.qty,
            limit_price=limit_price,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"주문 실행 실패: {e}",
        ) from e

    log_db = get_log_db()
    log_db.write(
        LOG_TYPE_ORDER,
        f"수동 주문: {body.side} {body.qty}주 {body.symbol} ({body.order_type})",
        symbol=body.symbol,
        meta={"side": body.side, "qty": body.qty, "order_id": result.order_id},
    )

    return {
        "success": True,
        "data": {
            "order_id": result.order_id,
            "symbol": body.symbol,
            "side": body.side,
            "qty": body.qty,
            "type": body.order_type,
            "status": result.status.value,
        },
        "count": 1,
    }
