"""Windows 딥링크(커스텀 URI 프로토콜) 등록 및 검증.

HKCU\\Software\\Classes\\stockvision 레지스트리 키를 생성하여
stockvision://launch 형태의 URI를 현재 exe로 연결한다.

Windows 전용: 다른 OS에서는 no-op.
"""
from __future__ import annotations

import logging
import platform
import sys

logger = logging.getLogger(__name__)

_PROTOCOL = "stockvision"
_REG_KEY_PATH = rf"Software\Classes\{_PROTOCOL}"


def _get_exe_path() -> str:
    """현재 실행 파일 경로를 반환한다."""
    return sys.executable


def register_protocol() -> bool:
    """stockvision:// 프로토콜을 현재 exe 경로로 등록한다."""
    if platform.system() != "Windows":
        logger.debug("Windows가 아닌 환경 — 딥링크 등록 건너뜀")
        return False

    import winreg

    exe_path = _get_exe_path()
    try:
        # stockvision 키 생성
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"URL:{_PROTOCOL} Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")

        # shell\open\command 키 생성
        cmd_key_path = rf"{_REG_KEY_PATH}\shell\open\command"
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, cmd_key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f'"{exe_path}" "%1"')

        logger.info("딥링크 프로토콜 등록 완료: %s → %s", _PROTOCOL, exe_path)
        return True
    except OSError as e:
        logger.error("딥링크 프로토콜 등록 실패: %s", e)
        return False


def verify_protocol() -> bool:
    """등록된 프로토콜 경로가 현재 exe와 일치하는지 확인한다."""
    if platform.system() != "Windows":
        return True

    import winreg

    exe_path = _get_exe_path()
    cmd_key_path = rf"{_REG_KEY_PATH}\shell\open\command"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cmd_key_path, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, "")
            expected = f'"{exe_path}" "%1"'
            return value == expected
    except FileNotFoundError:
        return False
    except OSError:
        return False
