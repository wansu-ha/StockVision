"""
StockVision 로컬 서버 (local-bridge)

- FastAPI + uvicorn, 포트 8765
- React ↔ 로컬 서버 WS 통신
- 클라우드(token.dat → JWT) 연동
- 키움 COM API 래퍼
- 1분 주기 규칙 평가 스케줄러
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import health, ws, config, kiwoom, trading, logs
from storage.config_manager import ConfigManager, set_config_manager
from cloud.auth_client import AuthClient, NeedsLoginError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

config_manager = ConfigManager()
set_config_manager(config_manager)
auth_client    = AuthClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 시작 ───────────────────────────────────────────────────
    logger.info("로컬 서버 시작 중...")
    from storage.log_db import init_db
    init_db()

    try:
        jwt = auth_client.refresh_jwt()
        cloud_config = auth_client.get_config(jwt)
        config_manager.load(cloud_config, jwt=jwt)
        logger.info("설정 로드 완료 — 자동 시작")
    except NeedsLoginError as e:
        logger.warning(f"자동 시작 불가: {e}")
        _notify_relogin()
    except Exception as e:
        logger.error(f"시작 오류: {e}")

    # 주문 큐 워커 시작
    from kiwoom.order import get_order_manager
    get_order_manager().start()

    # 스케줄러 시작
    from engine.scheduler import TradingScheduler, set_scheduler
    scheduler = TradingScheduler(config_manager)
    set_scheduler(scheduler)
    asyncio.create_task(scheduler.run())
    app.state.scheduler = scheduler

    # 하트비트 시작
    from cloud.heartbeat import HeartbeatWorker
    heartbeat = HeartbeatWorker()
    asyncio.create_task(heartbeat.run())

    yield

    # ── 종료 ───────────────────────────────────────────────────
    logger.info("로컬 서버 종료 중...")
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.stop()


def _notify_relogin():
    try:
        from tray import get_tray
        get_tray().notify("StockVision", "재로그인이 필요합니다. 브라우저에서 로그인해주세요.")
    except Exception:
        logger.warning("트레이 알림 불가 — 재로그인 필요")


app = FastAPI(title="StockVision Local Bridge", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ws.router)
app.include_router(config.router)
app.include_router(kiwoom.router)
app.include_router(trading.router)
app.include_router(logs.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8765, reload=False)
