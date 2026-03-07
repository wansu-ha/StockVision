"""Windows 토스트 알림 유틸리티.

체결, 오류, Kill Switch 등 주요 이벤트를 Windows 토스트 알림으로 표시한다.
브라우저가 열려있지 않아도 사용자에게 알림을 전달할 수 있다.

Windows 전용: 다른 OS에서는 no-op으로 동작한다.
"""
from __future__ import annotations

import logging
import platform
import threading

logger = logging.getLogger(__name__)


def _is_windows() -> bool:
    return platform.system() == "Windows"


def show_toast(title: str, message: str, duration: int = 5) -> None:
    """Windows 토스트 알림을 표시한다.

    Args:
        title: 알림 제목
        message: 알림 본문
        duration: 표시 시간 (초)
    """
    if not _is_windows():
        logger.debug("Windows가 아닌 환경 — 토스트 알림 건너뜀")
        return

    # 별도 스레드에서 실행 (COM 초기화 필요, 메인 스레드 차단 방지)
    thread = threading.Thread(
        target=_show_toast_thread,
        args=(title, message, duration),
        daemon=True,
    )
    thread.start()


def _show_toast_thread(title: str, message: str, duration: int) -> None:
    """토스트 알림 실행 (별도 스레드)."""
    try:
        # winotify 우선 시도 (가벼움, COM 불필요)
        from winotify import Notification
        toast = Notification(
            app_id="StockVision",
            title=title,
            msg=message,
            duration="short" if duration <= 5 else "long",
        )
        toast.show()
        return
    except ImportError:
        pass

    try:
        # win10toast 폴백
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=duration, threaded=False)
        return
    except ImportError:
        pass

    # 둘 다 없으면 로그만
    logger.debug("토스트 라이브러리 없음 (winotify 또는 win10toast 설치 필요): %s — %s", title, message)
