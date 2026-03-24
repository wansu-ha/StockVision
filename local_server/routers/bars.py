"""분봉 조회 API.

GET /api/v1/bars/{symbol}?resolution=1m&start=...&end=...
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from local_server.core.local_auth import require_local_secret
from local_server.storage.minute_bar import aggregate_bars, get_minute_bar_store

router = APIRouter(prefix="/api/v1/bars", tags=["bars"])


@router.get("/{symbol}")
async def get_bars(
    symbol: str,
    resolution: str = Query("1m", pattern="^(1m|5m|15m|1h)$"),
    start: str | None = Query(None),
    end: str | None = Query(None),
    _: None = Depends(require_local_secret),
):
    """분봉 조회. 5m/15m/1h는 1분봉 집계."""
    store = get_minute_bar_store()
    bars_1m = store.get_bars(symbol, start, end)

    if resolution != "1m":
        data = aggregate_bars(bars_1m, resolution)
    else:
        data = bars_1m

    return {
        "success": True,
        "data": data,
        "count": len(data),
        "resolution": resolution,
        "source": "local_db",
    }
