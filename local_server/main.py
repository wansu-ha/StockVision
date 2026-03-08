"""로컬 서버 FastAPI 앱 진입점.

사용자 PC에서 실행되며, 키움 브로커와 전략 엔진을 호스팅한다.
프론트엔드와 localhost로 통신하고, 클라우드 서버와는 아웃바운드만 통신한다.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from local_server.config import get_config
from local_server.core.local_auth import generate_secret
from local_server.routers import auth, config as config_router, logs, rules, status, trading, ws

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """FastAPI 앱 생명주기 관리.

    시작 시: 설정 로드, 수면 방지 활성화, 시스템 트레이 시작, 하트비트 시작
    종료 시: 하트비트 중지, 시스템 트레이 종료, 수면 방지 해제
    """
    cfg = get_config()

    # --- 시작 훅 ---
    logger.info("로컬 서버 시작 중...")

    # shared secret 생성 (CSRF 방어)
    app.state.local_secret = generate_secret()
    logger.info("local_secret 생성 완료")

    # token.dat → Keyring 마이그레이션 (H1)
    _migrate_token_dat()

    # 수면 방지 활성화
    if cfg.get("sleep_prevent"):
        from local_server.utils.sleep_prevent import enable_sleep_prevention
        enable_sleep_prevention()
        logger.info("수면 방지 활성화")

    # 시스템 트레이 시작 (별도 스레드)
    tray_thread = None
    try:
        from local_server.tray.tray_app import start_tray
        tray_thread = start_tray()
        logger.info("시스템 트레이 시작")
    except Exception as e:
        logger.warning("시스템 트레이 시작 실패 (GUI 환경이 아닐 수 있음): %s", e)

    # 클라우드 하트비트 시작
    heartbeat_task: asyncio.Task | None = None
    cloud_url = cfg.get("cloud.url")
    if cloud_url:
        from local_server.cloud.heartbeat import start_heartbeat
        heartbeat_task = asyncio.create_task(start_heartbeat())
        logger.info("클라우드 하트비트 시작: %s", cloud_url)

    # 트레이 아이콘 초록으로 전환
    if tray_thread is not None:
        try:
            from local_server.tray.tray_app import update_tray_status
            update_tray_status("ok")
        except Exception:
            pass

    logger.info("로컬 서버 준비 완료 (port=%s)", cfg.get("server.port"))

    yield  # 앱 실행 중

    # --- 종료 훅 ---
    logger.info("로컬 서버 종료 중...")

    # 하트비트 태스크 취소
    if heartbeat_task and not heartbeat_task.done():
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        logger.info("클라우드 하트비트 중지")

    # 시스템 트레이 종료
    if tray_thread is not None:
        try:
            from local_server.tray.tray_app import stop_tray
            stop_tray()
            logger.info("시스템 트레이 종료")
        except Exception as e:
            logger.warning("시스템 트레이 종료 실패: %s", e)

    # 수면 방지 해제
    if cfg.get("sleep_prevent"):
        from local_server.utils.sleep_prevent import disable_sleep_prevention
        disable_sleep_prevention()
        logger.info("수면 방지 해제")

    logger.info("로컬 서버 종료 완료")


def _migrate_token_dat() -> None:
    """기존 token.dat가 있으면 Keyring으로 이전 후 파일 삭제 (H1)."""
    from pathlib import Path
    import os
    token_dat = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "StockVision" / "token.dat"
    if not token_dat.exists():
        return
    token = token_dat.read_text(encoding="utf-8").strip()
    if token:
        from local_server.storage.credential import save_credential, KEY_CLOUD_REFRESH_TOKEN
        save_credential(KEY_CLOUD_REFRESH_TOKEN, token)
    token_dat.unlink()
    logger.info("token.dat → Keyring 마이그레이션 완료")


def create_app() -> FastAPI:
    """FastAPI 앱 인스턴스를 생성하고 설정한다."""
    cfg = get_config()

    app = FastAPI(
        title="StockVision 로컬 서버",
        description="키움 브로커 연동 및 전략 엔진 호스팅 서버",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS 미들웨어 (Step 8)
    origins: list[str] = cfg.get("cors.origins") or [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(auth.router, prefix="/api/auth", tags=["인증"])
    app.include_router(config_router.router, prefix="/api/config", tags=["설정"])
    app.include_router(status.router, prefix="/api/status", tags=["상태"])
    app.include_router(trading.router, prefix="/api", tags=["매매"])
    app.include_router(rules.router, prefix="/api/rules", tags=["규칙"])
    app.include_router(logs.router, prefix="/api/logs", tags=["로그"])
    app.include_router(ws.router, tags=["WebSocket"])

    @app.get("/health", tags=["헬스체크"])
    async def health_check() -> dict:
        """서버 헬스체크 엔드포인트."""
        return {"status": "ok", "version": app.version}

    return app


def configure_logging() -> None:
    """로깅 설정."""
    cfg = get_config()
    log_level = cfg.get("log_level", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


app = create_app()


if __name__ == "__main__":
    configure_logging()
    cfg = get_config()
    uvicorn.run(
        "local_server.main:app",
        host=cfg.get("server.host", "127.0.0.1"),
        port=cfg.get("server.port"),
        reload=False,
        log_level="info",
    )
