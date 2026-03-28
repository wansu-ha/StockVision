"""백테스트 작업 큐 관리."""
from __future__ import annotations

import asyncio
import logging
import uuid
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from backtest_server.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Job:
    job_id: str
    symbol: str
    timeframe: str
    start_date: date
    end_date: date
    script: str
    config: dict = field(default_factory=dict)
    status: str = "queued"        # queued, collecting, running, done, failed
    queue_position: int = 0
    progress: int = 0
    message: str = ""
    result: dict | None = None
    error: str | None = None


class QueueManager:
    """메모리 큐 + 워커 풀 관리."""

    def __init__(self):
        self._queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=settings.MAX_QUEUE_SIZE)
        self._jobs: dict[str, Job] = {}
        self._active_count = 0
        self._worker_task: asyncio.Task | None = None

    def start(self) -> None:
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("큐 매니저 시작 (workers=%d, queue=%d)", settings.MAX_WORKERS, settings.MAX_QUEUE_SIZE)

    def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()

    async def submit(
        self, symbol: str, timeframe: str,
        start_date: date, end_date: date,
        script: str, config: dict | None = None,
    ) -> Job:
        """작업 제출 → Job 반환."""
        if self._queue.full():
            raise QueueFullError()

        job = Job(
            job_id=f"bt-{uuid.uuid4().hex[:8]}",
            symbol=symbol, timeframe=timeframe,
            start_date=start_date, end_date=end_date,
            script=script, config=config or {},
        )
        self._jobs[job.job_id] = job
        await self._queue.put(job)
        job.queue_position = self._queue.qsize()
        job.message = f"대기중 ({job.queue_position}번째)"
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    @property
    def stats(self) -> dict:
        return {
            "active_jobs": self._active_count,
            "queued_jobs": self._queue.qsize(),
            "max_workers": settings.MAX_WORKERS,
        }

    async def _worker_loop(self) -> None:
        """워커 루프 — 동시 실행 제한."""
        sem = asyncio.Semaphore(settings.MAX_WORKERS)

        while True:
            job = await self._queue.get()
            await sem.acquire()
            asyncio.create_task(self._execute(job, sem))

    async def _execute(self, job: Job, sem: asyncio.Semaphore) -> None:
        """단일 작업 실행."""
        self._active_count += 1
        job.status = "running"
        job.message = "백테스트 실행중..."
        job.progress = 10

        try:
            result = await asyncio.wait_for(
                self._run_backtest(job),
                timeout=settings.JOB_TIMEOUT_SECONDS,
            )
            job.status = "done"
            job.progress = 100
            job.message = "완료"
            job.result = result
        except asyncio.TimeoutError:
            job.status = "failed"
            job.error = "타임아웃"
            job.message = f"타임아웃 ({settings.JOB_TIMEOUT_SECONDS}초)"
        except Exception as e:
            logger.exception("백테스트 실패: %s", e)
            job.status = "failed"
            job.error = str(e)
            job.message = f"실패: {e}"
        finally:
            self._active_count -= 1
            sem.release()
            # 대기열 순번 갱신
            self._update_positions()

    async def _run_backtest(self, job: Job) -> dict:
        """실제 백테스트 실행."""
        from backtest_server.services.runner import run_backtest, BacktestConfig
        from backtest_server.services.data_client import DataNotFoundError

        cfg = BacktestConfig(
            initial_cash=job.config.get("initial_cash", 10_000_000),
            commission_rate=job.config.get("commission_rate", 0.00015),
            tax_rate=job.config.get("tax_rate", 0.0018),
            slippage_rate=job.config.get("slippage_rate", 0.001),
        )

        try:
            result = await run_backtest(
                job.script, job.symbol,
                job.start_date, job.end_date,
                job.timeframe, cfg,
            )
        except DataNotFoundError as e:
            # 데이터 없음 → 수집 대기
            if e.task_id:
                job.status = "collecting"
                job.message = f"{e.symbol} {e.timeframe} 데이터 수집중..."
                await self._wait_collection(e.task_id, job)
                # 재시도
                result = await run_backtest(
                    job.script, job.symbol,
                    job.start_date, job.end_date,
                    job.timeframe, cfg,
                )
            else:
                raise

        return {
            "total_return_pct": result.total_return_pct,
            "cagr": result.cagr,
            "max_drawdown_pct": result.max_drawdown_pct,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
            "sharpe_ratio": result.sharpe_ratio,
            "avg_hold_bars": result.avg_hold_bars,
            "trade_count": result.trade_count,
            "total_commission": result.total_commission,
            "total_tax": result.total_tax,
            "total_slippage": result.total_slippage,
            "equity_curve": result.equity_curve[-500:],  # 최대 500포인트
            "trades": [
                {
                    "entry_date": t.entry_date, "entry_price": t.entry_price,
                    "exit_date": t.exit_date, "exit_price": t.exit_price,
                    "qty": t.qty, "pnl": t.pnl, "pnl_pct": t.pnl_pct,
                    "hold_bars": t.hold_bars,
                }
                for t in result.trades
            ],
        }

    async def _wait_collection(self, task_id: str, job: Job) -> None:
        """동적 수집 완료 대기."""
        from backtest_server.services.data_client import check_collection_status

        for _ in range(120):  # 최대 10분
            await asyncio.sleep(5)
            status = await check_collection_status(task_id)
            progress = status.get("progress", 0)
            job.progress = progress
            job.message = status.get("message", "수집중...")
            if status.get("status") == "done":
                return
            if status.get("status") == "failed":
                raise RuntimeError(status.get("message", "수집 실패"))

        raise RuntimeError("수집 타임아웃")

    def _update_positions(self) -> None:
        pos = 1
        for job in self._jobs.values():
            if job.status == "queued":
                job.queue_position = pos
                job.message = f"대기중 ({pos}번째)"
                pos += 1


class QueueFullError(Exception):
    pass


# 싱글톤
queue_manager = QueueManager()
