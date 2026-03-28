"""봉 데이터 조회 + ingest API."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from itertools import groupby

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from data_server.core.auth import verify_api_key
from data_server.core.database import get_db
from data_server.services.market_repository import MarketRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["bars"], dependencies=[Depends(verify_api_key)])


# ── 봉 조회 ──────────────────────────────────────────────────────


@router.get("/bars/{symbol}")
async def get_bars(
    symbol: str,
    timeframe: str = Query("1d", pattern="^(1m|5m|15m|1h|1d|1w|1mo)$"),
    start: date = Query(default=None),
    end: date = Query(default=None),
    limit: int = Query(default=1000, le=5000),
    db: Session = Depends(get_db),
):
    """봉 데이터 조회. 분봉/일봉/주봉/월봉 지원."""
    repo = MarketRepository(db)

    if timeframe in ("1m", "5m", "15m", "1h"):
        return _get_minute_bars(repo, symbol, start, end, timeframe, limit)

    # 일봉 계열
    if start is None:
        start = date.today() - timedelta(days=365)
    if end is None:
        end = date.today()

    bars = repo.get_daily_bars(symbol, start, end)
    data = [
        {
            "date": str(b.date), "open": b.open, "high": b.high,
            "low": b.low, "close": b.close, "volume": b.volume,
        }
        for b in bars
    ]

    if timeframe != "1d" and data:
        data = _aggregate_daily(data, timeframe)

    if len(data) > limit:
        data = data[-limit:]

    return {"success": True, "data": data, "count": len(data), "timeframe": timeframe}


def _get_minute_bars(
    repo: MarketRepository, symbol: str,
    start: date | None, end: date | None,
    timeframe: str, limit: int,
) -> dict:
    if start is None:
        start = date.today() - timedelta(days=30)
    if end is None:
        end = date.today()

    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.max.time())

    rows = repo.get_minute_bars(symbol, start_dt, end_dt, limit)
    data = [
        {
            "timestamp": r.timestamp.isoformat(), "open": r.open,
            "high": r.high, "low": r.low, "close": r.close, "volume": r.volume,
        }
        for r in rows
    ]

    if timeframe != "1m" and data:
        data = _aggregate_minute(data, timeframe)

    return {"success": True, "data": data, "count": len(data), "timeframe": timeframe}


# ── 집계 ──────────────────────────────────────────────────────


def _aggregate_daily(bars: list[dict], timeframe: str) -> list[dict]:
    def week_key(b):
        d = date.fromisoformat(b["date"])
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"

    def month_key(b):
        d = date.fromisoformat(b["date"])
        return f"{d.year}-{d.month:02d}"

    key_fn = week_key if timeframe == "1w" else month_key
    return _aggregate(bars, key_fn, date_field="date")


def _aggregate_minute(bars: list[dict], timeframe: str) -> list[dict]:
    minutes = {"5m": 5, "15m": 15, "1h": 60}
    bucket_min = minutes.get(timeframe, 5)

    def bucket_key(b):
        t = datetime.fromisoformat(b["timestamp"])
        floored = (t.minute // bucket_min) * bucket_min
        return t.replace(minute=floored, second=0, microsecond=0).isoformat()

    return _aggregate(bars, bucket_key, date_field="timestamp")


def _aggregate(bars: list[dict], key_fn, date_field: str) -> list[dict]:
    result = []
    for _, group in groupby(bars, key=key_fn):
        gl = list(group)
        result.append({
            date_field: gl[0][date_field],
            "open": gl[0]["open"],
            "high": max(b["high"] for b in gl if b.get("high") is not None),
            "low": min(b["low"] for b in gl if b.get("low") is not None),
            "close": gl[-1]["close"],
            "volume": sum(b.get("volume") or 0 for b in gl),
        })
    return result


# ── Ingest ────────────────────────────────────────────────────


class MinuteBarItem(BaseModel):
    symbol: str
    timestamp: str
    open: int
    high: int
    low: int
    close: int
    volume: int


class IngestRequest(BaseModel):
    bars: list[MinuteBarItem]


@router.post("/bars/ingest")
async def ingest_minute_bars(
    payload: IngestRequest,
    db: Session = Depends(get_db),
):
    """로컬 서버에서 수집한 분봉 ingest."""
    repo = MarketRepository(db)
    count = 0
    for item in payload.bars:
        ts = _parse_timestamp(item.timestamp)
        if ts is None:
            continue
        repo.upsert_minute_bar(
            item.symbol, ts,
            item.open, item.high, item.low, item.close, item.volume,
        )
        count += 1
    db.commit()
    return {"success": True, "count": count}


def _parse_timestamp(ts_str: str) -> datetime | None:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M%S", "%Y%m%d%H%M"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None
