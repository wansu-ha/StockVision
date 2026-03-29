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
from local_server.routers import account, alerts as alerts_router, auth, config as config_router, logs, results, rules, status, trading, ws
from local_server.routers import quote as quote_router, broker as broker_router
from local_server.routers.bars import router as bars_router
from local_server.routers.condition_status import router as condition_router

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

    # 클라우드 WS 릴레이 클라이언트 시작
    ws_relay_task_ref: asyncio.Task | None = None
    cloud_url = cfg.get("cloud.url")
    if cloud_url:
        from local_server.cloud.ws_relay_client import WsRelayClient, set_ws_relay_client
        ws_url = cfg.get("cloud.ws_url", "")
        if not ws_url:
            # http → ws, https → wss 자동 변환
            ws_url = cloud_url.replace("https://", "wss://").replace("http://", "ws://")
            ws_url = ws_url.rstrip("/") + "/ws/relay"

        access_token, _ = load_cloud_tokens()
        if access_token:
            ws_client = WsRelayClient()

            # command 핸들러 등록 (킬스위치, arm 등)
            async def _handle_remote_command(msg: dict) -> None:
                from local_server.cloud._command_handler import handle_command
                await handle_command(app, msg)
            ws_client.set_command_handler(_handle_remote_command)

            set_ws_relay_client(ws_client)
            try:
                await asyncio.wait_for(ws_client.start(ws_url, access_token), timeout=10)
                logger.info("클라우드 WS 릴레이 시작: %s", ws_url)
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning("클라우드 WS 릴레이 연결 실패 (서버 시작은 계속): %s", e)

    # 클라우드 하트비트 시작 (WS 연결 여부와 관계없이 — HTTP 폴백용)
    heartbeat_task: asyncio.Task | None = None
    if cloud_url:
        from local_server.cloud.heartbeat import start_heartbeat
        heartbeat_task = asyncio.create_task(start_heartbeat())
        logger.info("클라우드 하트비트 시작: %s", cloud_url)

    # 자동 업데이트 체크
    update_mgr = None
    try:
        from local_server.updater.manager import get_update_manager
        from local_server.updater.installer import get_install_dir
        update_mgr = get_update_manager()

        # pending_rollback.json 마커 처리
        marker = get_install_dir() / "pending_rollback.json"
        if marker.exists():
            import json as _json
            try:
                data = _json.loads(marker.read_text())
                marker_status = data.get("status")
                if marker_status == "rolled_back":
                    logger.warning(
                        "업데이트 실패: v%s → v%s 롤백됨",
                        data.get("from_version"), data.get("to_version"),
                    )
                    update_mgr.state.status = "rolled_back"
                    update_mgr.state.last_error = (
                        f"v{data.get('to_version')} 업데이트 실패, "
                        f"v{data.get('from_version')}으로 복원됨"
                    )
                    marker.unlink()
                elif marker_status in ("installing", "verifying"):
                    # .bat이 처리 중 — 마커 유지
                    logger.info("pending_rollback 마커 (status=%s) — .bat 처리 대기", marker_status)
                else:
                    logger.warning("pending_rollback 알 수 없는 상태: %s — 마커 삭제", marker_status)
                    marker.unlink()
            except Exception:
                logger.warning("pending_rollback.json 파싱 실패 — 마커 삭제")
                marker.unlink(missing_ok=True)

        await update_mgr.startup()
        if update_mgr.state.info and update_mgr.state.info.available:
            logger.info("업데이트 가능: %s → %s", update_mgr.state.info.current, update_mgr.state.info.latest)
            # 자동 다운로드
            if cfg.get("update.auto_enabled", True):
                asyncio.create_task(update_mgr.start_download())
        # 백그라운드 루프 (체크 + 설치)
        await update_mgr.start_background_tasks()
    except Exception as e:
        logger.warning("업데이트 체크 실패 (서버 시작은 계속): %s", e)

    # 브로커 자동 연결 (키 있으면 서버 시작 시 자동 연결)
    app.state.broker = None
    app.state.broker_reason = "disconnected"
    try:
        from local_server.broker.factory import create_broker_from_config
        broker = create_broker_from_config()
        await asyncio.wait_for(broker.connect(), timeout=15)
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

    # HealthWatchdog 시작
    from local_server.engine.alert_monitor import AlertMonitor
    from local_server.engine.health_watchdog import HealthWatchdog
    app.state.alert_monitor = AlertMonitor(config=cfg.get("alerts"))
    watchdog = HealthWatchdog(alert_monitor=app.state.alert_monitor)
    if app.state.broker:
        watchdog.set_broker(app.state.broker)
    # 엔진은 나중에 시작될 수 있으므로 app.state에 watchdog 저장 (엔진 시작 시 주입)
    app.state.watchdog = watchdog
    await watchdog.start()
    logger.info("HealthWatchdog 시작")

    # 업데이트 설치 안전 조건 콜백 주입
    if update_mgr:
        def can_install_now() -> bool:
            """엔진 정지 + 미체결 없음."""
            engine = getattr(app.state, "strategy_engine", None)
            if engine and getattr(engine, "running", False):
                return False
            broker = getattr(app.state, "broker", None)
            if broker:
                try:
                    # has_pending_orders 미구현 → get_open_orders 길이로 대체
                    orders = broker.get_open_orders()
                    if orders:
                        return False
                except Exception:
                    pass
            return True
        update_mgr.set_install_guard(can_install_now)

    # 업데이트 이벤트 → 토스트 알림 연결
    if update_mgr and tray_thread is not None:
        from local_server.utils.toast import show_toast

        def _on_update_event(event: str, message: str) -> None:
            show_toast("StockVision", message)

        update_mgr.set_event_callback(_on_update_event)

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

    # HealthWatchdog 중지
    wd = getattr(app.state, "watchdog", None)
    if wd:
        await wd.stop()
        logger.info("HealthWatchdog 중지")

    # WS 릴레이 클라이언트 종료
    from local_server.cloud.ws_relay_client import get_ws_relay_client
    ws_client = get_ws_relay_client()
    if ws_client:
        await ws_client.stop()
        logger.info("클라우드 WS 릴레이 종료")

    # 업데이트 백그라운드 태스크 종료
    if update_mgr:
        await update_mgr.shutdown()

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
    origins: list[str] = cfg.get("cors.origins")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(account.router, prefix="/api/account", tags=["계좌"])
    app.include_router(alerts_router.router, prefix="/api", tags=["경고 설정"])
    app.include_router(auth.router, prefix="/api/auth", tags=["인증"])
    app.include_router(config_router.router, prefix="/api/config", tags=["설정"])
    app.include_router(status.router, prefix="/api/status", tags=["상태"])
    app.include_router(trading.router, prefix="/api", tags=["매매"])
    app.include_router(rules.router, prefix="/api/rules", tags=["규칙"])
    app.include_router(results.router, prefix="/api/rules", tags=["규칙 결과"])
    app.include_router(logs.router, prefix="/api/logs", tags=["로그"])
    app.include_router(quote_router.router, prefix="/api/quote", tags=["시세"])
    app.include_router(broker_router.router, prefix="/api/broker", tags=["브로커"])
    app.include_router(bars_router, tags=["분봉"])
    app.include_router(condition_router)
    app.include_router(ws.router, tags=["WebSocket"])

    from local_server.routers import devices as devices_router
    app.include_router(devices_router.router, tags=["디바이스"])
    from local_server.routers import update as update_router
    app.include_router(update_router.router)

    import time as _time
    _start_time = _time.monotonic()

    @app.get("/health", tags=["헬스체크"])
    async def health_check() -> dict:
        """서버 헬스체크 엔드포인트."""
        from local_server.updater.manager import get_update_manager
        mgr = get_update_manager()
        return {
            "status": "ok", "version": app.version, "app": "stockvision",
            "uptime": int(_time.monotonic() - _start_time),
            "update_status": mgr.state.to_dict(),
        }

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
    import os

    # PyInstaller exe (--noconsole): sys.stdout/stderr가 None → 더미 스트림으로 대체
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    configure_logging()

    # 다중 인스턴스 방지 (Named Mutex)
    from local_server.utils.mutex import acquire_mutex
    if not acquire_mutex("StockVision"):
        logger.info("이미 실행 중 — 종료합니다.")
        sys.exit(0)

    cfg = get_config()
    port = cfg.get("server.port", 4020)

    # 딥링크 프로토콜 등록/검증
    _ensure_deeplink()

    # sys.argv 화이트리스트 검증
    _parse_deeplink_argv()

    # 소켓 직접 생성 — SO_REUSEADDR로 TIME_WAIT/ghost 바인딩 회피
    import socket as _socket
    host = cfg.get("server.host", "127.0.0.1")
    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError:
        logger.error("포트 %d이(가) 이미 사용 중입니다.", port)
        sys.exit(1)
    sock.listen(128)
    sock.setblocking(False)

    # PyInstaller exe에서는 모듈 문자열 import가 실패하므로 앱 객체 직접 전달
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)

    import asyncio
    asyncio.run(server.serve(sockets=[sock]))
