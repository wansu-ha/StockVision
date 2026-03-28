"""백테스트 서버 — 연산 전담."""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from backtest_server.core.config import settings
from backtest_server.services.queue_manager import queue_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("백테스트 서버 시작 (workers=%d)", settings.MAX_WORKERS)
    queue_manager.start()
    yield
    queue_manager.stop()
    logger.info("백테스트 서버 종료")


app = FastAPI(
    title="StockVision Backtest Server",
    version="1.0.0",
    lifespan=lifespan,
)

from backtest_server.api.backtest import router as backtest_router
app.include_router(backtest_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {
        "success": True,
        "status": "healthy",
        "service": "backtest-server",
        **queue_manager.stats,
    }
