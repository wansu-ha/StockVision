"""설치 시퀀스 — 백업 + .bat 생성 + 프로세스 종료."""
from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import tempfile
from datetime import time as dtime
from pathlib import Path

from local_server.__version__ import __version__ as _VERSION

logger = logging.getLogger(__name__)

_INSTALL_BAT_TEMPLATE = """@echo off
timeout /t 3 /nobreak >nul
start "" "{installer_path}" /SILENT /SUPPRESSMSGBOXES
del "%~f0"
"""


def get_install_dir() -> Path:
    """현재 exe의 설치 디렉토리를 반환한다."""
    if getattr(sys, "frozen", False):
        # PyInstaller onedir
        return Path(sys.executable).parent
    # 개발 환경
    return Path(__file__).resolve().parent.parent.parent


def backup_current(install_dir: Path, max_backups: int = 2) -> Path | None:
    """현재 버전을 backup/ 디렉토리에 복사한다.

    Returns:
        백업 경로 또는 실패 시 None.
    """
    backup_dir = install_dir / "backup" / f"v{_VERSION}"
    try:
        if backup_dir.exists():
            shutil.rmtree(backup_dir)

        # exe 디렉토리 전체 복사 (backup/ 제외)
        def _ignore(src: str, names: list[str]) -> set[str]:
            if Path(src) == install_dir:
                return {"backup", "temp", "logs"}
            return set()

        shutil.copytree(install_dir, backup_dir, ignore=_ignore)
        logger.info("백업 완료: %s", backup_dir)

        # 오래된 백업 정리
        _cleanup_old_backups(install_dir / "backup", max_backups)

        return backup_dir
    except Exception:
        logger.exception("백업 실패")
        return None


def _cleanup_old_backups(backup_root: Path, max_keep: int) -> None:
    """오래된 백업을 삭제한다 (최근 N개만 유지)."""
    if not backup_root.exists():
        return
    dirs = sorted(backup_root.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True)
    for d in dirs[max_keep:]:
        try:
            shutil.rmtree(d)
            logger.info("오래된 백업 삭제: %s", d.name)
        except Exception:
            logger.warning("백업 삭제 실패: %s", d.name)


def is_in_update_window(no_update_start: str, no_update_end: str, now: dtime | None = None) -> bool:
    """현재 시간이 업데이트 허용 구간인지 확인한다.

    no_update_start~no_update_end 사이에는 업데이트 불가.
    예: "08:00"~"17:00" → 17:00~08:00에만 업데이트 가능.

    Args:
        now: 테스트용 시간 주입. None이면 현재 시간.
    """
    from datetime import datetime

    if now is None:
        now = datetime.now().time()
    try:
        start = dtime.fromisoformat(no_update_start)
        end = dtime.fromisoformat(no_update_end)
    except ValueError:
        logger.warning("업데이트 시간 파싱 실패: %s ~ %s", no_update_start, no_update_end)
        return False

    # no_update 구간 안이면 False
    if start <= end:
        # 같은 날: start <= now < end → 차단
        if start <= now < end:
            return False
        return True
    else:
        # 자정 걸침: start <= now OR now < end → 차단
        if now >= start or now < end:
            return False
        return True


def execute_update(installer_path: Path) -> None:
    """설치 .bat을 생성하고 현재 프로세스를 종료한다.

    .bat이 3초 대기 후 인스톨러를 실행하고 자신을 삭제한다.
    """
    bat_content = _INSTALL_BAT_TEMPLATE.format(installer_path=str(installer_path))
    bat_path = Path(tempfile.gettempdir()) / "stockvision_update.bat"

    bat_path.write_text(bat_content, encoding="utf-8")
    logger.info("설치 스크립트 생성: %s", bat_path)

    # detached process로 .bat 실행
    subprocess.Popen(
        ["cmd", "/c", str(bat_path)],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        close_fds=True,
    )
    logger.info("설치 시작 — 서버 종료")
    sys.exit(0)
