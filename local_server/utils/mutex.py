"""Windows Named Mutex를 이용한 다중 인스턴스 방지.

CreateMutexW로 시스템 전역 뮤텍스를 획득한다.
이미 같은 이름의 뮤텍스가 존재하면 False를 반환하여 중복 실행을 막는다.

Windows 전용: 다른 OS에서는 항상 True (no-op).
"""
from __future__ import annotations

import logging
import platform

logger = logging.getLogger(__name__)

# 뮤텍스 핸들을 모듈 레벨에 유지 — 프로세스 종료 시 OS가 자동 해제
_mutex_handle = None


def acquire_mutex(name: str = "StockVision") -> bool:
    """Named Mutex 획득을 시도한다.

    Returns:
        True: 획득 성공 (첫 번째 인스턴스)
        False: 이미 실행 중 (두 번째 인스턴스)
    """
    global _mutex_handle

    if platform.system() != "Windows":
        return True

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ERROR_ALREADY_EXISTS = 183

    # CreateMutexW(lpMutexAttributes, bInitialOwner, lpName)
    handle = kernel32.CreateMutexW(
        wintypes.LPVOID(0),  # 기본 보안 속성
        wintypes.BOOL(True),  # 소유권 요청
        f"Global\\{name}",
    )

    if handle == 0:
        logger.error("뮤텍스 생성 실패: %s", ctypes.get_last_error())
        return False

    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        logger.info("이미 실행 중인 인스턴스가 있습니다.")
        return False

    _mutex_handle = handle
    logger.debug("뮤텍스 획득 성공: %s", name)
    return True
