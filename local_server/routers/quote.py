"""시세 라우터.

GET /api/quote/{symbol} — 단건 시세 조회 (브로커 REST)
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from local_server.core.local_auth import require_local_secret

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{symbol}",
    summary="단건 시세 조회",
)
async def get_quote(
    symbol: str,
    request: Request,
    _: None = Depends(require_local_secret),
) -> dict[str, Any]:
    """브로커 REST API로 종목의 현재 시세를 조회한다."""
    broker = getattr(request.app.state, "broker", None)
    if not broker or not broker.is_connected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="브로커 미연결. 증권사 키를 확인하세요.",
        )

    try:
        quote = await broker.get_quote(symbol)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"시세 조회 실패: {e}",
        ) from e

    return {
        "success": True,
        "data": {
            "symbol": quote.symbol,
            "price": float(quote.price),
            "volume": quote.volume,
            "bid_price": float(quote.bid_price) if quote.bid_price is not None else None,
            "ask_price": float(quote.ask_price) if quote.ask_price is not None else None,
            "timestamp": quote.timestamp.isoformat() if quote.timestamp else None,
        },
        "count": 1,
    }
