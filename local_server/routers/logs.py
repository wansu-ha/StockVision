"""로그 조회 라우터.

GET /api/logs — 체결/에러 로그 조회 (필터, 페이지네이션)
GET /api/logs/summary — 날짜별 로그 타입별 건수 요약
GET /api/logs/daily-pnl — 일일 실현손익
GET /api/logs/timeline — intent_id 기반 타임라인 조회
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query

from local_server.core.local_auth import require_local_secret

from local_server.storage.log_db import (
    get_log_db,
    LOG_TYPE_FILL,
    LOG_TYPE_ORDER,
    LOG_TYPE_ERROR,
    LOG_TYPE_SYSTEM,
    LOG_TYPE_STRATEGY,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 허용 로그 타입
VALID_LOG_TYPES = {
    LOG_TYPE_FILL,
    LOG_TYPE_ORDER,
    LOG_TYPE_ERROR,
    LOG_TYPE_SYSTEM,
    LOG_TYPE_STRATEGY,
}


@router.get(
    "/summary",
    summary="로그 요약",
)
async def log_summary(
    date: str | None = Query(
        None,
        description="요약 기준 날짜 (YYYY-MM-DD). 미지정 시 오늘.",
    ),
    _: None = Depends(require_local_secret),
) -> dict[str, Any]:
    """특정 날짜 이후 로그 타입별 건수를 반환한다."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    db = get_log_db()
    counts = db.count_by_type(date)

    return {
        "success": True,
        "data": {
            "date": date,
            "signals": counts.get(LOG_TYPE_STRATEGY, 0),
            "fills": counts.get(LOG_TYPE_FILL, 0),
            "orders": counts.get(LOG_TYPE_ORDER, 0),
            "errors": counts.get(LOG_TYPE_ERROR, 0),
        },
        "count": 1,
    }


@router.get("/daily-pnl", summary="일일 실현손익")
async def daily_pnl(
    date: str | None = Query(None, description="기준 날짜 (YYYY-MM-DD). 미지정 시 오늘."),
    _: None = Depends(require_local_secret),
) -> dict[str, Any]:
    """당일 FILL 로그의 실현손익을 합산하여 반환한다."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    db = get_log_db()
    fills, _ = db.query(log_type=LOG_TYPE_FILL, date_from=date, limit=1000)

    # 당일 FILL만 필터링
    today_fills = [f for f in fills if f["ts"].startswith(date)]

    realized_pnl = Decimal("0")
    win_count = 0
    loss_count = 0
    for fill in today_fills:
        pnl_raw = fill.get("meta", {}).get("realized_pnl")
        if pnl_raw is not None:
            pnl = Decimal(str(pnl_raw))
            realized_pnl += pnl
            if pnl > 0:
                win_count += 1
            elif pnl < 0:
                loss_count += 1

    fill_count = len(today_fills)
    win_rate = round(win_count / fill_count, 3) if fill_count > 0 else 0.0

    return {
        "success": True,
        "data": {
            "date": date,
            "realized_pnl": float(realized_pnl),
            "fill_count": fill_count,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": win_rate,
        },
        "count": 1,
    }


# ── 로그 타입 → 타임라인 상태 매핑 ──
_LOG_TYPE_TO_STATE = {
    LOG_TYPE_STRATEGY: "PROPOSED",
    LOG_TYPE_ORDER: "SUBMITTED",
    LOG_TYPE_FILL: "FILLED",
}

_BLOCK_REASONS = {"DUPLICATE_SYMBOL", "MAX_POSITIONS", "DAILY_BUDGET_EXCEEDED", "SELL_NO_HOLDING"}


def _log_to_state(log_type: str, meta: dict[str, Any]) -> str:
    if log_type in _LOG_TYPE_TO_STATE:
        return _LOG_TYPE_TO_STATE[log_type]
    if log_type == LOG_TYPE_ERROR:
        return "BLOCKED" if meta.get("block_reason") in _BLOCK_REASONS else "FAILED"
    return "UNKNOWN"


@router.get("/timeline", summary="타임라인 조회 (intent_id 기반)")
async def query_timeline(
    date_from: str = Query(..., description="시작 날짜 (YYYY-MM-DD, 필수)"),
    limit: int = Query(50, ge=1, le=500, description="최대 타임라인 항목 수"),
    symbol: str | None = Query(None, description="종목 코드 필터"),
    state: str | None = Query(None, description="최종 상태 필터 (FILLED, BLOCKED, FAILED)"),
    _: None = Depends(require_local_secret),
) -> dict[str, Any]:
    """intent_id 기반 타임라인 조회. 같은 intent_id의 로그를 하나의 항목으로 그룹핑한다."""
    db = get_log_db()
    all_logs, _ = db.query(date_from=date_from, limit=5000)

    # intent_id별 그룹핑
    groups: dict[str, list[dict[str, Any]]] = {}
    for log in all_logs:
        iid = log.get("intent_id")
        if not iid:
            continue
        groups.setdefault(iid, []).append(log)

    entries: list[dict[str, Any]] = []
    for intent_id, logs in groups.items():
        sorted_logs = sorted(logs, key=lambda x: x["ts"])
        steps = []
        final_state = "PROPOSED"
        entry_symbol = ""
        entry_side = ""
        rule_id = 0

        for log in sorted_logs:
            st = _log_to_state(log["log_type"], log.get("meta", {}))
            steps.append({
                "state": st,
                "ts": log["ts"],
                "message": log["message"],
                "meta": log.get("meta", {}),
            })
            final_state = st
            if not entry_symbol:
                entry_symbol = log.get("symbol") or ""
            meta = log.get("meta", {})
            if not rule_id and meta.get("rule_id"):
                rule_id = int(meta["rule_id"])
            if not entry_side and meta.get("side"):
                entry_side = str(meta["side"])

        # 필터 적용
        if symbol and entry_symbol != symbol:
            continue
        if state and final_state != state:
            continue

        # 소요 시간 계산
        started_at = sorted_logs[0]["ts"]
        ended_at = sorted_logs[-1]["ts"] if final_state in ("FILLED", "BLOCKED", "FAILED") else None
        duration_ms = None
        if ended_at and started_at != ended_at:
            try:
                start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                duration_ms = int((end - start).total_seconds() * 1000)
            except (ValueError, TypeError):
                pass

        entries.append({
            "intent_id": intent_id,
            "rule_id": rule_id,
            "symbol": entry_symbol,
            "side": entry_side or "BUY",
            "state": final_state,
            "steps": steps,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_ms": duration_ms,
        })

    entries.sort(key=lambda x: x["started_at"], reverse=True)
    entries = entries[:limit]

    return {
        "success": True,
        "data": {"items": entries, "total": len(entries)},
        "count": len(entries),
    }


@router.get(
    "",
    summary="로그 조회",
)
async def query_logs(
    log_type: str | None = Query(
        None,
        description=f"필터할 로그 종류: {', '.join(sorted(VALID_LOG_TYPES))}",
    ),
    symbol: str | None = Query(None, description="종목 코드 필터"),
    limit: int = Query(100, ge=1, le=1000, description="최대 조회 수"),
    offset: int = Query(0, ge=0, description="건너뛸 수"),
    date_from: str | None = Query(None, description="시작 날짜 필터 (YYYY-MM-DD)"),
    _: None = Depends(require_local_secret),
) -> dict[str, Any]:
    """체결/에러 로그를 조회한다.

    최신 순으로 정렬되어 반환된다.
    """
    # log_type 유효성 검사
    if log_type and log_type not in VALID_LOG_TYPES:
        return {
            "success": False,
            "data": {
                "error": f"유효하지 않은 log_type: {log_type}",
                "valid_types": sorted(VALID_LOG_TYPES),
            },
            "count": 0,
        }

    db = get_log_db()
    items, total = db.query(
        log_type=log_type,
        symbol=symbol,
        limit=limit,
        offset=offset,
        date_from=date_from,
    )

    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
        "count": len(items),
    }
