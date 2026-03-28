"""백테스트 API."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backtest_server.core.auth import verify_api_key
from backtest_server.services.queue_manager import QueueFullError, queue_manager

router = APIRouter(tags=["backtest"], dependencies=[Depends(verify_api_key)])


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    start_date: date
    end_date: date
    script: str
    initial_cash: float = 10_000_000
    commission_rate: float = 0.00015
    tax_rate: float = 0.0018
    slippage_rate: float = 0.001


@router.post("/backtest/run", status_code=202)
async def run_backtest(req: BacktestRequest):
    """백테스트 요청 → job_id 반환."""
    try:
        job = await queue_manager.submit(
            symbol=req.symbol,
            timeframe=req.timeframe,
            start_date=req.start_date,
            end_date=req.end_date,
            script=req.script,
            config={
                "initial_cash": req.initial_cash,
                "commission_rate": req.commission_rate,
                "tax_rate": req.tax_rate,
                "slippage_rate": req.slippage_rate,
            },
        )
    except QueueFullError:
        raise HTTPException(status_code=503, detail="서버 바쁨")

    return {
        "success": True,
        "job_id": job.job_id,
        "status": job.status,
        "queue_position": job.queue_position,
    }


@router.get("/backtest/jobs/{job_id}")
async def get_job_status(job_id: str):
    """작업 상태 조회."""
    job = queue_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")

    resp = {
        "success": True,
        "job_id": job.job_id,
        "status": job.status,
        "queue_position": job.queue_position,
        "progress": job.progress,
        "message": job.message,
    }
    if job.status == "done" and job.result:
        resp["result"] = job.result
    if job.status == "failed":
        resp["error"] = job.error
    return resp
