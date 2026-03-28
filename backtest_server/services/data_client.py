"""데이터 서버 HTTP 클라이언트."""
from __future__ import annotations

import logging
from datetime import date

import httpx

from backtest_server.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0


async def get_bars(
    symbol: str, timeframe: str, start: date, end: date,
) -> list[dict]:
    """데이터 서버에서 봉 데이터 조회."""
    url = f"{settings.DATA_SERVER_URL}/api/v1/bars/{symbol}"
    params = {
        "timeframe": timeframe,
        "start": str(start),
        "end": str(end),
        "limit": 5000,
    }
    headers = {}
    if settings.API_SECRET:
        headers["X-API-Key"] = settings.API_SECRET

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=headers)

    if resp.status_code == 404:
        data = resp.json()
        task_id = data.get("collection_task_id")
        raise DataNotFoundError(symbol, timeframe, task_id)

    resp.raise_for_status()
    body = resp.json()
    return body.get("data", [])


async def check_collection_status(task_id: str) -> dict:
    """동적 수집 상태 조회."""
    url = f"{settings.DATA_SERVER_URL}/api/v1/collection/{task_id}"
    headers = {}
    if settings.API_SECRET:
        headers["X-API-Key"] = settings.API_SECRET

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, headers=headers)

    resp.raise_for_status()
    return resp.json()


class DataNotFoundError(Exception):
    def __init__(self, symbol: str, timeframe: str, task_id: str | None = None):
        self.symbol = symbol
        self.timeframe = timeframe
        self.task_id = task_id
        super().__init__(f"데이터 없음: {symbol} {timeframe}")
