"""Windows 시작 시 자동 실행 관리.

레지스트리 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run에
StockVision 항목을 추가/제거한다.

Windows 전용: 다른 OS에서는 no-op으로 동작한다.
"""
from __future__ import annotations

import logging
import platform
import sys

logger = logging.getLogger(__name__)

_REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "StockVision"


def _get_exe_path() -> str:
    """현재 실행 파일 경로를 반환한다."""
    return sys.executable


def is_autostart_enabled() -> bool:
    """시작 시 자동 실행 등록 여부를 반환한다."""
    if platform.system() != "Windows":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable_autostart() -> bool:
    """시작 시 자동 실행을 등록한다. 성공하면 True."""
    if platform.system() != "Windows":
        logger.warning("Windows가 아닌 환경에서는 자동 시작을 지원하지 않습니다.")
        return False
    try:
        import winreg
        exe_path = _get_exe_path()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        logger.info("자동 시작 등록 완료: %s", exe_path)
        return True
    except OSError as e:
        logger.error("자동 시작 등록 실패: %s", e)
        return False


def disable_autostart() -> bool:
    """시작 시 자동 실행을 해제한다. 성공하면 True."""
    if platform.system() != "Windows":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _APP_NAME)
        logger.info("자동 시작 해제 완료")
        return True
    except FileNotFoundError:
        return True  # 이미 없음
    except OSError as e:
        logger.error("자동 시작 해제 실패: %s", e)
        return False
