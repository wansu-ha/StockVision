"""시스템 트레이 아이콘 모듈.

pystray를 사용하여 Windows 시스템 트레이에 아이콘을 표시한다.
FastAPI 앱과 별도 스레드에서 실행된다.

트레이 기능:
  - 더블클릭 → 브라우저로 대시보드 열기
  - 우클릭 메뉴: 상태, 대시보드 열기, 엔진 토글, Kill Switch, 종료
  - 아이콘 색상: 🟢 정상 / 🟡 경고 / 🔴 오류
"""
from __future__ import annotations

import logging
import os
import signal
import threading
import webbrowser
from typing import Any, Literal

logger = logging.getLogger(__name__)

# pystray, Pillow는 GUI 환경에서만 사용 가능
try:
    import pystray
    from PIL import Image, ImageDraw

    _PYSTRAY_AVAILABLE = True
except ImportError:
    _PYSTRAY_AVAILABLE = False
    logger.warning("pystray 또는 Pillow 없음 — 시스템 트레이 비활성화")


TrayStatus = Literal["ok", "warning", "error"]

# 로컬 API 인증 정보 (main.py lifespan에서 설정)
_local_secret: str | None = None
_local_port: int = 4020


def set_tray_auth(port: int, secret: str) -> None:
    """main.py lifespan에서 호출. 트레이 → API 호출에 필요한 인증 정보 설정."""
    global _local_secret, _local_port
    _local_secret, _local_port = secret, port


# 상태별 아이콘 색상
_STATUS_COLORS: dict[TrayStatus, tuple[int, int, int, int]] = {
    "ok": (34, 197, 94, 255),       # green-500
    "warning": (234, 179, 8, 255),  # yellow-500
    "error": (239, 68, 68, 255),    # red-500
}

# 전역 트레이 상태
_tray_icon: "pystray.Icon | None" = None
_tray_thread: threading.Thread | None = None
_current_status: TrayStatus = "error"  # 시작 시 빨간색, 준비 완료 시 초록으로 전환


def _create_icon_image(status: TrayStatus = "ok", size: int = 64) -> "Image.Image":
    """상태에 따라 색상이 다른 트레이 아이콘을 생성한다."""
    from PIL import Image, ImageDraw

    color = _STATUS_COLORS.get(status, _STATUS_COLORS["error"])
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 원형 배경
    draw.ellipse((2, 2, size - 2, size - 2), fill=color)
    # 'S' 표시 영역 (흰색 사각형)
    margin = size // 4
    draw.rectangle(
        (margin, margin, size - margin, size - margin),
        fill=(255, 255, 255, 200),
    )
    return img


def _status_text() -> str:
    """현재 상태에 따른 표시 텍스트."""
    labels: dict[TrayStatus, str] = {
        "ok": "정상 운영 중",
        "warning": "주의 필요",
        "error": "연결 오류",
    }
    return labels.get(_current_status, "알 수 없음")


def _on_open_dashboard(icon: Any, item: Any) -> None:
    """대시보드 열기 핸들러."""
    webbrowser.open("http://localhost:5173")
    logger.info("브라우저로 대시보드 열기")


def _on_open_status(icon: Any, item: Any) -> None:
    """상태 API 열기 핸들러."""
    from local_server.config import get_config
    cfg = get_config()
    port = cfg.get("server.port")
    webbrowser.open(f"http://127.0.0.1:{port}/api/status")


def _on_toggle_engine(icon: Any, item: Any) -> None:
    """엔진 시작/중지 토글 — 로컬 API를 호출하여 실제 엔진을 제어한다."""
    from local_server.cloud.heartbeat import _engine_running
    action = "stop" if _engine_running else "start"
    threading.Thread(
        target=_call_engine_api,
        args=(action,),
        daemon=True,
    ).start()


def _call_engine_api(action: str) -> None:
    """로컬 서버 전략 엔진 API를 호출한다."""
    try:
        import httpx
    except ImportError:
        logger.error("httpx 미설치 — 트레이 엔진 제어 불가")
        return

    url = f"http://127.0.0.1:{_local_port}/api/strategy/{action}"
    headers = {"X-Local-Secret": _local_secret or ""}
    try:
        resp = httpx.post(url, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info("트레이 엔진 %s 성공", action)
    except Exception as e:
        logger.error("트레이 엔진 %s 실패: %s", action, e)
        try:
            from local_server.utils.toast import show_toast
            show_toast("엔진 제어 실패", str(e))
        except Exception:
            pass


def _on_kill_switch(icon: Any, item: Any) -> None:
    """긴급 정지 (Kill Switch)."""
    from local_server.cloud.heartbeat import set_engine_running
    set_engine_running(False)
    update_tray_status("warning")
    logger.warning("트레이 Kill Switch 발동: 전략 엔진 중지")

    try:
        from local_server.utils.toast import show_toast
        show_toast("StockVision 긴급 정지", "전략 엔진이 중지되었습니다.")
    except Exception:
        pass


def _on_toggle_autostart(icon: Any, item: Any) -> None:
    """자동 시작 토글."""
    from local_server.utils.autostart import is_autostart_enabled, enable_autostart, disable_autostart
    if is_autostart_enabled():
        disable_autostart()
        logger.info("자동 시작 해제")
    else:
        enable_autostart()
        logger.info("자동 시작 등록")


def _autostart_checked(_item: Any) -> bool:
    """자동 시작 메뉴 체크 상태."""
    try:
        from local_server.utils.autostart import is_autostart_enabled
        return is_autostart_enabled()
    except Exception:
        return False


def _on_quit(icon: Any, item: Any) -> None:
    """종료 핸들러."""
    logger.info("트레이 종료 메뉴 선택")
    icon.stop()
    os.kill(os.getpid(), signal.SIGINT)


def _engine_label(_item: Any) -> str:
    """엔진 토글 메뉴 동적 라벨."""
    from local_server.cloud.heartbeat import _engine_running
    return "엔진 중지" if _engine_running else "엔진 시작"


def start_tray() -> threading.Thread | None:
    """시스템 트레이 아이콘을 별도 스레드에서 시작한다."""
    global _tray_icon, _tray_thread, _current_status

    if not _PYSTRAY_AVAILABLE:
        logger.warning("시스템 트레이를 사용할 수 없습니다 (pystray 미설치)")
        return None

    _current_status = "error"  # 시작 시 빨간색
    icon_image = _create_icon_image(_current_status)

    menu = pystray.Menu(
        pystray.MenuItem("StockVision", None, enabled=False),
        pystray.MenuItem(lambda _: f"  {_status_text()}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("대시보드 열기", _on_open_dashboard, default=True),
        pystray.MenuItem("상태 API", _on_open_status),
        pystray.MenuItem(_engine_label, _on_toggle_engine),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("긴급 정지 (Kill Switch)", _on_kill_switch),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("시작 시 자동 실행", _on_toggle_autostart, checked=_autostart_checked),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("종료", _on_quit),
    )

    _tray_icon = pystray.Icon(
        name="stockvision",
        icon=icon_image,
        title="StockVision 로컬 서버",
        menu=menu,
    )

    def _run() -> None:
        try:
            _tray_icon.run()  # type: ignore[union-attr]
        except Exception as e:
            logger.error("트레이 실행 오류: %s", e)

    _tray_thread = threading.Thread(target=_run, daemon=True, name="tray-thread")
    _tray_thread.start()
    return _tray_thread


def update_tray_status(status: TrayStatus) -> None:
    """트레이 아이콘 색상을 상태에 따라 갱신한다."""
    global _current_status
    if _current_status == status:
        return
    _current_status = status
    if _tray_icon is not None:
        try:
            _tray_icon.icon = _create_icon_image(status)
            logger.debug("트레이 아이콘 색상 변경: %s", status)
        except Exception as e:
            logger.warning("트레이 아이콘 갱신 실패: %s", e)


def get_tray_status() -> TrayStatus:
    """현재 트레이 상태를 반환한다."""
    return _current_status


def stop_tray() -> None:
    """시스템 트레이 아이콘을 종료한다."""
    global _tray_icon
    if _tray_icon is not None:
        try:
            _tray_icon.stop()
        except Exception as e:
            logger.debug("트레이 종료 중 오류 (무시): %s", e)
        _tray_icon = None
