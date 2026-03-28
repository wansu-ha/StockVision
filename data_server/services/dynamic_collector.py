"""동적 수집 — 요청 데이터 미존재 시 즉시 수집."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

# 메모리 태스크 저장소 (서버 재시작 시 유실 — 백테스트 재요청하면 됨)
_tasks: dict[str, dict[str, Any]] = {}


def create_collection_task(
    symbol: str, timeframe: str, start: date, end: date,
) -> str:
    """수집 태스크 생성 → task_id 반환."""
    task_id = f"col-{uuid.uuid4().hex[:8]}"
    _tasks[task_id] = {
        "status": "pending",
        "symbol": symbol,
        "timeframe": timeframe,
        "start": str(start),
        "end": str(end),
        "progress": 0,
        "message": "수집 대기중...",
    }
    # 백그라운드 실행
    asyncio.create_task(_run_collection(task_id, symbol, timeframe, start, end))
    return task_id


def get_task_status(task_id: str) -> dict | None:
    return _tasks.get(task_id)


async def _run_collection(
    task_id: str, symbol: str, timeframe: str, start: date, end: date,
) -> None:
    """실제 수집 실행."""
    task = _tasks[task_id]
    task["status"] = "collecting"
    task["message"] = f"{symbol} {timeframe} 데이터 수집중..."

    try:
        if timeframe == "1d":
            await _collect_daily(task_id, symbol, start, end)
        else:
            await _collect_minute(task_id, symbol, start, end)
        task["status"] = "done"
        task["progress"] = 100
        task["message"] = "수집 완료"
    except Exception as e:
        logger.exception("수집 실패: %s", e)
        task["status"] = "failed"
        task["message"] = f"수집 실패: {e}"


async def _collect_daily(task_id: str, symbol: str, start: date, end: date) -> None:
    """yfinance로 일봉 수집."""
    task = _tasks[task_id]
    task["message"] = f"{symbol} 일봉 수집중 (yfinance)..."
    task["progress"] = 10

    import yfinance as yf
    from data_server.core.database import get_db_session
    from data_server.services.market_repository import MarketRepository

    # 한국 종목이면 .KS/.KQ 추가
    ticker_symbol = _to_yfinance_symbol(symbol)
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(start=str(start), end=str(end))

    if hist.empty:
        task["message"] = f"{symbol} 데이터 없음"
        return

    task["progress"] = 50
    db = get_db_session()
    try:
        repo = MarketRepository(db)
        for idx, row in hist.iterrows():
            bar_date = idx.date() if hasattr(idx, "date") else idx
            repo.save_daily_bar(symbol, bar_date, {
                "open": int(row["Open"]) if row["Open"] else None,
                "high": int(row["High"]) if row["High"] else None,
                "low": int(row["Low"]) if row["Low"] else None,
                "close": int(row["Close"]) if row["Close"] else None,
                "volume": int(row["Volume"]) if row["Volume"] else None,
            })
        task["progress"] = 90
        task["data_count"] = len(hist)
    finally:
        db.close()


async def _collect_minute(task_id: str, symbol: str, start: date, end: date) -> None:
    """분봉 수집 (향후 키움 REST API 연동)."""
    task = _tasks[task_id]
    task["message"] = f"{symbol} 분봉 수집 — 아직 미구현"
    task["progress"] = 0
    # TODO: 키움 REST API로 분봉 수집 구현


def _to_yfinance_symbol(symbol: str) -> str:
    """종목코드 → yfinance 심볼 변환."""
    if symbol.startswith("^") or symbol.startswith("USD"):
        return symbol  # 지수/환율은 그대로
    if symbol.isdigit() and len(symbol) == 6:
        return f"{symbol}.KS"  # 한국 종목 기본 KOSPI
    return symbol
