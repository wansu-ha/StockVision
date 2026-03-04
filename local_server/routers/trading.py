from fastapi import APIRouter
from engine.scheduler import get_scheduler

router = APIRouter(prefix="/api/strategy", tags=["trading"])


@router.post("/start")
def strategy_start():
    scheduler = get_scheduler()
    if scheduler:
        scheduler.resume()
    return {"success": True, "message": "전략 엔진 시작됨"}


@router.post("/stop")
def strategy_stop():
    scheduler = get_scheduler()
    if scheduler:
        scheduler.pause()
    return {"success": True, "message": "전략 엔진 중지됨"}
