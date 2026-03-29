"""조건 상태 API — spec §3.6 T5."""
from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(prefix="/api/conditions", tags=["conditions"])


@router.get("/status")
async def get_all_status():
    """모든 규칙의 최신 조건 상태."""
    from local_server.engine import get_engine
    engine = get_engine()
    if engine is None:
        return {"success": True, "data": {}, "count": 0}
    tracker = getattr(engine, "_condition_tracker", None)
    if tracker is None:
        return {"success": True, "data": {}, "count": 0}
    data = tracker.get_all_latest()
    return {"success": True, "data": data, "count": len(data)}


@router.get("/status/{rule_id}")
async def get_rule_status(rule_id: int):
    """특정 규칙의 조건 상태."""
    from local_server.engine import get_engine
    engine = get_engine()
    if engine is None:
        return {"success": True, "data": None}
    tracker = getattr(engine, "_condition_tracker", None)
    if tracker is None:
        return {"success": True, "data": None}
    return {"success": True, "data": tracker.get_latest(rule_id)}
