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

from local_server.__version__ import __version__ as _VERSION
from local_server.config import get_config
from local_server.core.local_auth import generate_secret
from local_server.routers import account, auth, config as config_router, logs, results, rules, status, trading, ws
from local_server.routers import quote as quote_router, broker as broker_router

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
        from local_server.tray.tray_app import start_tray, set_tray_auth
        tray_thread = start_tray()
        # 트레이 → 로컬 API 호출에 필요한 인증 정보 주입
        set_tray_auth(
            port=cfg.get("server.port", 4020),
            secret=app.state.local_secret,
        )
        logger.info("시스템 트레이 시작")
    except Exception as e:
        logger.warning("시스템 트레이 시작 실패 (GUI 환경이 아닐 수 있음): %s", e)

    # 활성 사용자 복원 + 자동 로그인
    from local_server.storage.credential import _restore_active_user, load_cloud_tokens, save_cloud_tokens
    last_user = cfg.get("auth.last_user")
    if last_user:
        _restore_active_user(last_user)

    access_token, refresh_token = load_cloud_tokens()
    if not access_token and refresh_token:
        cloud_url_for_refresh = cfg.get("cloud.url", "")
        if cloud_url_for_refresh:
            try:
                from local_server.cloud.client import CloudClient
                temp = CloudClient(base_url=cloud_url_for_refresh)
                tokens = await temp.refresh_access_token(refresh_token)
                save_cloud_tokens(tokens["access_token"], tokens["refresh_token"])
                logger.info("서버 시작 시 토큰 자동 갱신 완료")
            except Exception as e:
                logger.warning("서버 시작 시 토큰 자동 갱신 실패 (수동 로그인 필요): %s", e)

    # 클라우드 하트비트 시작
    heartbeat_task: asyncio.Task | None = None
    cloud_url = cfg.get("cloud.url")
    if cloud_url:
        from local_server.cloud.heartbeat import start_heartbeat
        heartbeat_task = asyncio.create_task(start_heartbeat())
        logger.info("클라우드 하트비트 시작: %s", cloud_url)

    # 브로커 자동 연결 (키 있으면 서버 시작 시 자동 연결)
    app.state.broker = None
    app.state.broker_reason = "disconnected"
    try:
        from local_server.broker.factory import create_broker_from_config
        broker = create_broker_from_config()
        await broker.connect()
        app.state.broker = broker
        app.state.broker_reason = "connected"
        logger.info("브로커 자동 연결 완료")
    except ValueError:
        # 자격증명 미등록 — 정상 (키 없이 시작)
        app.state.broker_reason = "no_credentials"
        logger.info("브로커 자격증명 미등록, 연결 없이 시작")
    except Exception as e:
        app.state.broker_reason = "connect_failed"
        logger.warning("브로커 자동 연결 실패: %s", e)

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

    # 브로커 연결 해제
    broker = getattr(app.state, "broker", None)
    if broker:
        try:
            await broker.disconnect()
            logger.info("브로커 연결 해제")
        except Exception as e:
            logger.warning("브로커 연결 해제 실패: %s", e)

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
        version=_VERSION,
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
    app.include_router(account.router, prefix="/api/account", tags=["계좌"])
    app.include_router(auth.router, prefix="/api/auth", tags=["인증"])
    app.include_router(config_router.router, prefix="/api/config", tags=["설정"])
    app.include_router(status.router, prefix="/api/status", tags=["상태"])
    app.include_router(trading.router, prefix="/api", tags=["매매"])
    app.include_router(rules.router, prefix="/api/rules", tags=["규칙"])
    app.include_router(results.router, prefix="/api/rules", tags=["규칙 결과"])
    app.include_router(logs.router, prefix="/api/logs", tags=["로그"])
    app.include_router(quote_router.router, prefix="/api/quote", tags=["시세"])
    app.include_router(broker_router.router, prefix="/api/broker", tags=["브로커"])
    app.include_router(ws.router, tags=["WebSocket"])

    @app.get("/health", tags=["헬스체크"])
    async def health_check() -> dict:
        """서버 헬스체크 엔드포인트."""
        return {"status": "ok", "version": app.version, "app": "stockvision"}

    return app


def configure_logging() -> None:
    """로깅 설정.

    콘솔 + 파일 로깅을 설정한다.
    console=False (exe)에서도 ~/.stockvision/logs/server.log에 기록된다.
    """
    from logging.handlers import RotatingFileHandler
    from pathlib import Path

    cfg = get_config()
    log_level = cfg.get("log_level", "INFO")
    level = getattr(logging, log_level, logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    # 콘솔 핸들러 (개발 시)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # 파일 핸들러 (exe에서도 로그 기록)
    log_dir = Path.home() / ".stockvision" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "server.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


app = create_app()


def _check_port(port: int) -> bool:
    """포트가 사용 가능한지 확인한다. 사용 중이면 False."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
        return True
    except OSError:
        logger.error("포트 %d이(가) 이미 사용 중입니다.", port)
        return False


def _ensure_deeplink() -> None:
    """딥링크 프로토콜이 현재 exe를 가리키는지 확인하고, 아니면 재등록."""
    try:
        from local_server.utils.deeplink import verify_protocol, register_protocol
        if not verify_protocol():
            register_protocol()
    except Exception as e:
        logger.warning("딥링크 프로토콜 등록/검증 실패: %s", e)


def _parse_deeplink_argv() -> None:
    """sys.argv에서 stockvision:// URI를 파싱하고 비허용 인자는 경고 로그."""
    import sys
    allowed_commands = {"launch"}

    for arg in sys.argv[1:]:
        if not arg.startswith("stockvision://"):
            continue
        # stockvision://launch → "launch"
        command = arg.removeprefix("stockvision://").strip("/")
        if command not in allowed_commands:
            logger.warning("알 수 없는 딥링크 명령 무시: %s", command)
        else:
            logger.info("딥링크 명령: %s", command)


if __name__ == "__main__":
    import sys

    configure_logging()

    # 다중 인스턴스 방지 (Named Mutex)
    from local_server.utils.mutex import acquire_mutex
    if not acquire_mutex("StockVision"):
        logger.info("이미 실행 중 — 종료합니다.")
        sys.exit(0)

    cfg = get_config()
    port = cfg.get("server.port", 4020)

    # 포트 점유 감지
    if not _check_port(port):
        sys.exit(1)

    # 딥링크 프로토콜 등록/검증
    _ensure_deeplink()

    # sys.argv 화이트리스트 검증
    _parse_deeplink_argv()

    # PyInstaller exe에서는 모듈 문자열 import가 실패하므로 앱 객체 직접 전달
    uvicorn.run(
        app,
        host=cfg.get("server.host", "127.0.0.1"),
        port=port,
        log_level="info",
    )
