"""Windows 수면 방지 유틸리티.

SetThreadExecutionState Win32 API를 사용하여
프로세스가 실행 중인 동안 시스템 수면을 방지한다.

자동매매 중 PC가 수면 상태로 전환되면 주문 실행이 중단되므로,
전략 엔진 실행 중에는 반드시 수면 방지를 활성화해야 한다.

Windows 전용: 다른 OS에서는 no-op로 동작한다.
"""
from __future__ import annotations

import logging
import platform
import sys

logger = logging.getLogger(__name__)

# SetThreadExecutionState 플래그 (Windows API 상수)
ES_CONTINUOUS: int = 0x80000000
ES_SYSTEM_REQUIRED: int = 0x00000001
ES_DISPLAY_REQUIRED: int = 0x00000002


def _is_windows() -> bool:
    """현재 플랫폼이 Windows인지 확인한다."""
    return platform.system() == "Windows" or sys.platform == "win32"


def enable_sleep_prevention(include_display: bool = False) -> bool:
    """시스템 수면 방지를 활성화한다.

    Args:
        include_display: True이면 화면 꺼짐도 방지한다 (기본: False, 수면만 방지)

    Returns:
        성공하면 True, 실패(비Windows 또는 API 오류)하면 False
    """
    if not _is_windows():
        logger.info("Windows가 아닌 환경 — 수면 방지 기능 비활성화 (no-op)")
        return False

    try:
        import ctypes
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        if include_display:
            flags |= ES_DISPLAY_REQUIRED

        result = ctypes.windll.kernel32.SetThreadExecutionState(flags)
        if result == 0:
            logger.error("SetThreadExecutionState 실패 (반환값 0)")
            return False

        logger.info(
            "수면 방지 활성화 (display_required=%s, flags=0x%08X)",
            include_display,
            flags,
        )
        return True

    except AttributeError:
        logger.error("ctypes.windll 접근 실패 — Windows 환경인지 확인하세요")
        return False
    except Exception as e:
        logger.error("수면 방지 활성화 실패: %s", e)
        return False


def disable_sleep_prevention() -> bool:
    """시스템 수면 방지를 해제한다.

    ES_CONTINUOUS 플래그만 설정하여 이전 상태를 복원한다.

    Returns:
        성공하면 True, 실패하면 False
    """
    if not _is_windows():
        return False

    try:
        import ctypes
        result = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        if result == 0:
            logger.error("수면 방지 해제 실패 (SetThreadExecutionState 반환값 0)")
            return False

        logger.info("수면 방지 해제 완료")
        return True

    except Exception as e:
        logger.error("수면 방지 해제 실패: %s", e)
        return False
