"""데이터 서버 — 시장 데이터 저장·수집·제공."""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from data_server.core.config import settings
from data_server.core.database import Base, engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작: 테이블 생성
    Base.metadata.create_all(bind=engine)
    logger.info("데이터 서버 시작 (ENV=%s)", settings.ENV)

    # 스케줄러 시작
    from data_server.services.scheduler import scheduler
    scheduler.start()

    yield

    # 종료
    scheduler.stop()
    logger.info("데이터 서버 종료")


app = FastAPI(
    title="StockVision Data Server",
    version="1.0.0",
    lifespan=lifespan,
)

# 라우터 등록
from data_server.api.bars import router as bars_router
from data_server.api.stocks import router as stocks_router
from data_server.api.financials import router as financials_router
from data_server.api.collection import router as collection_router

app.include_router(bars_router, prefix="/api/v1")
app.include_router(stocks_router, prefix="/api/v1")
app.include_router(financials_router, prefix="/api/v1")
app.include_router(collection_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"success": True, "status": "healthy", "service": "data-server"}
