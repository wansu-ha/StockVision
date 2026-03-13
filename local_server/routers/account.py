"""계좌 라우터.

GET /api/account/balance — 잔고 + 보유종목 조회
GET /api/account/orders  — 미체결 주문 조회
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from local_server.core.local_auth import require_local_secret

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_broker(request: Request):
    """app.state에서 브로커 인스턴스를 가져온다."""
    broker = getattr(request.app.state, "broker", None)
    if not broker or not broker.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="브로커 미연결. 증권사 키를 확인하세요.",
        )
    return broker


@router.get(
    "/balance",
    summary="잔고 + 보유종목 조회",
)
async def get_balance(
    request: Request,
    _: None = Depends(require_local_secret),
) -> dict[str, Any]:
    """브로커에서 잔고와 보유종목을 조회한다."""
    broker = _get_broker(request)

    try:
        result = await broker.get_balance()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"잔고 조회 실패: {e}",
        ) from e

    positions = [
        {
            "symbol": p.symbol,
            "qty": p.qty,
            "avg_price": float(p.avg_price),
            "current_price": float(p.current_price),
            "eval_amount": float(p.eval_amount),
            "unrealized_pnl": float(p.unrealized_pnl),
            "unrealized_pnl_rate": float(p.unrealized_pnl_rate),
        }
        for p in result.positions
    ]

    return {
        "success": True,
        "data": {
            "cash": float(result.cash),
            "total_eval": float(result.total_eval),
            "positions": positions,
        },
        "count": len(positions),
    }


@router.get(
    "/orders",
    summary="미체결 주문 조회",
)
async def get_open_orders(
    request: Request,
    _: None = Depends(require_local_secret),
) -> dict[str, Any]:
    """브로커에서 미체결 주문 목록을 조회한다."""
    broker = _get_broker(request)

    try:
        orders = await broker.get_open_orders()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"미체결 조회 실패: {e}",
        ) from e

    items = [
        {
            "order_id": o.order_id,
            "symbol": o.symbol,
            "side": o.side.value,
            "qty": o.qty,
            "filled_qty": o.filled_qty,
            "status": o.status.value,
            "order_type": o.order_type.value if o.order_type else None,
            "limit_price": float(o.limit_price) if o.limit_price else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in orders
    ]

    return {
        "success": True,
        "data": items,
        "count": len(items),
    }
