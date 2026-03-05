"""시스템 트레이 아이콘 모듈.

pystray를 사용하여 Windows 시스템 트레이에 아이콘을 표시한다.
FastAPI 앱과 별도 스레드에서 실행된다.

트레이 메뉴:
  - 상태 확인: 기본 브라우저로 /api/status 열기
  - 종료: uvicorn 서버 종료
"""
from __future__ import annotations

import logging
import os
import threading
import webbrowser
from typing import Any

logger = logging.getLogger(__name__)

# pystray, Pillow는 GUI 환경에서만 사용 가능
try:
    import pystray
    from PIL import Image, ImageDraw

    _PYSTRAY_AVAILABLE = True
except ImportError:
    _PYSTRAY_AVAILABLE = False
    logger.warning("pystray 또는 Pillow 없음 — 시스템 트레이 비활성화")


def _create_icon_image(size: int = 64) -> "Image.Image":
    """트레이 아이콘 이미지를 생성한다.

    외부 이미지 파일이 없을 때 프로그래매틱으로 생성하는 폴백.
    """
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 원형 배경 (파란색)
    draw.ellipse((2, 2, size - 2, size - 2), fill=(37, 99, 235, 255))
    # 'S' 글자 영역 (흰색 사각형으로 단순 표현)
    margin = size // 4
    draw.rectangle(
        (margin, margin, size - margin, size - margin),
        fill=(255, 255, 255, 200),
    )
    return img


# 전역 트레이 아이콘 인스턴스
_tray_icon: "pystray.Icon | None" = None
_tray_thread: threading.Thread | None = None


def _on_open_status(icon: Any, item: Any) -> None:
    """트레이 메뉴 '상태 확인' 클릭 핸들러."""
    from local_server.config import get_config
    cfg = get_config()
    port = cfg.get("server.port")
    url = f"http://127.0.0.1:{port}/api/status"
    webbrowser.open(url)
    logger.info("브라우저로 상태 페이지 열기: %s", url)


def _on_quit(icon: Any, item: Any) -> None:
    """트레이 메뉴 '종료' 클릭 핸들러."""
    logger.info("트레이 종료 메뉴 선택")
    icon.stop()
    # uvicorn을 종료하기 위해 프로세스에 SIGTERM/KeyboardInterrupt 전달
    os.kill(os.getpid(), 2)  # signal.SIGINT (=2)


def start_tray() -> threading.Thread | None:
    """시스템 트레이 아이콘을 별도 스레드에서 시작한다.

    Returns:
        트레이 스레드 (pystray 미설치 시 None)
    """
    global _tray_icon, _tray_thread

    if not _PYSTRAY_AVAILABLE:
        logger.warning("시스템 트레이를 사용할 수 없습니다 (pystray 미설치)")
        return None

    icon_image = _create_icon_image()

    menu = pystray.Menu(
        pystray.MenuItem("StockVision 로컬 서버", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("상태 확인", _on_open_status),
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


def stop_tray() -> None:
    """시스템 트레이 아이콘을 종료한다."""
    global _tray_icon
    if _tray_icon is not None:
        try:
            _tray_icon.stop()
        except Exception as e:
            logger.debug("트레이 종료 중 오류 (무시): %s", e)
        _tray_icon = None
