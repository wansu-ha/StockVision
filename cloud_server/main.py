"""
클라우드 서버 FastAPI 앱

Phase 3 Unit 4 — 인증, 규칙 CRUD, 시세 수집, AI 컨텍스트, 어드민.

실행: python -m uvicorn cloud_server.main:app --reload --port 4010
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cloud_server.core.config import settings, validate_settings
from cloud_server.core.init_db import init_db

# 라우터 import
from cloud_server.api.auth import router as auth_router
from cloud_server.api.rules import router as rules_router
from cloud_server.api.heartbeat import router as heartbeat_router
from cloud_server.api.version import router as version_router
from cloud_server.api.admin import router as admin_router
from cloud_server.api.context import router as context_router
from cloud_server.api.sync import router as sync_router
from cloud_server.api.stocks import router as stocks_router
from cloud_server.api.watchlist import router as watchlist_router
from cloud_server.api.market_data import router as market_data_router

logger = logging.getLogger(__name__)

# 스케줄러 전역 인스턴스
_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 라이프사이클 핸들러"""
    global _scheduler

    # SEC-C2: SECRET_KEY 미설정 시 서버 시작 차단
    validate_settings()

    # 시작
    try:
        init_db()
    except Exception as e:
        logger.error(f"DB 초기화 실패: {e}")

    # DataAggregator 초기화
    try:
        from cloud_server.data.factory import create_aggregator, set_aggregator
        set_aggregator(create_aggregator())
        logger.info("[OK] DataAggregator 초기화 완료")
    except Exception as e:
        logger.error(f"DataAggregator 초기화 실패: {e}")

    try:
        from cloud_server.collector.scheduler import CollectorScheduler
        _scheduler = CollectorScheduler()
        _scheduler.start()
        logger.info("[OK] 수집 스케줄러 시작됨")
    except Exception as e:
        logger.error(f"수집 스케줄러 시작 실패: {e}")

    yield

    # 종료
    if _scheduler:
        _scheduler.stop()
        logger.info("[OK] 수집 스케줄러 중지됨")


app = FastAPI(
    title="StockVision Cloud Server",
    description="AI 기반 주식 시스템매매 플랫폼 — 클라우드 서버 (Phase 3)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 요청 로깅 미들웨어
@app.middleware("http")
async def request_logging(request: Request, call_next):
    trace_id = str(uuid.uuid4())[:8]
    start = time.time()

    # 로깅 제외 경로
    skip = {"/health", "/api/v1/version"}
    if request.url.path not in skip:
        logger.info(f"[{trace_id}] {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        elapsed = time.time() - start
        if request.url.path not in skip:
            logger.info(f"[{trace_id}] {response.status_code} ({elapsed:.3f}s)")
        response.headers["X-Process-Time"] = str(elapsed)
        return response
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"[{trace_id}] ERROR {request.url.path} ({elapsed:.3f}s): {e}")
        return JSONResponse(status_code=500, content={"success": False, "detail": "서버 내부 오류"})


# 라우터 등록
app.include_router(auth_router)
app.include_router(rules_router)
app.include_router(heartbeat_router)
app.include_router(version_router)
app.include_router(admin_router)
app.include_router(context_router)
app.include_router(sync_router)
app.include_router(market_data_router)
app.include_router(stocks_router)
app.include_router(watchlist_router)


# ── 기본 엔드포인트 ──────────────────────────────────────────────────


@app.get("/health")
async def health():
    """서버 상태 확인"""
    return {
        "success": True,
        "status": "healthy",
        "version": "1.0.0",
        "env": settings.ENV,
    }


@app.get("/")
async def root():
    return {
        "success": True,
        "message": "StockVision Cloud Server",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    from urllib.parse import urlparse
    port = urlparse(settings.CLOUD_URL).port or 4010
    uvicorn.run(app, host="0.0.0.0", port=port)
