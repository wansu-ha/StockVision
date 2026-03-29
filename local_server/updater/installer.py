"""설치 시퀀스 — 백업 + .bat 생성 (verifier 포함) + 프로세스 종료."""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, time as dtime
from pathlib import Path

from local_server.__version__ import __version__ as _VERSION

logger = logging.getLogger(__name__)

# 확장된 bat 템플릿 — health check + 버전 검증 + 롤백
_INSTALL_BAT_TEMPLATE = r"""@echo off
REM === StockVision 업데이트 + 검증 스크립트 ===

REM 1. 서버 종료 대기
timeout /t 3 /nobreak >nul

REM 2. pending_rollback.json 상태를 verifying으로 갱신
echo {{"status":"verifying","from_version":"{from_version}","to_version":"{target_version}","backup_dir":"{backup_dir}"}} > "{install_dir}\pending_rollback.json"

REM 3. 인스톨러 실행 (종료까지 대기)
start /wait "" "{installer_path}" /SILENT /SUPPRESSMSGBOXES

REM 4. Inno [Run] 실패 대비 — 프로세스 없으면 직접 시작
timeout /t 5 /nobreak >nul
tasklist /FI "IMAGENAME eq stockvision-local.exe" | findstr "stockvision-local.exe" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    start "" "{install_dir}\stockvision-local.exe"
    timeout /t 5 /nobreak >nul
)

REM 5. health check — 목표 버전으로 떴는지 확인 (최대 60초)
set ATTEMPTS=0
:health_loop
if %ATTEMPTS% GEQ 20 goto rollback
timeout /t 3 /nobreak >nul
set /a ATTEMPTS+=1
curl -s http://127.0.0.1:{port}/health > "%TEMP%\sv_health.tmp" 2>nul
if %ERRORLEVEL% NEQ 0 goto health_loop
findstr /C:"{target_version}" "%TEMP%\sv_health.tmp" >nul 2>&1
if %ERRORLEVEL%==0 goto version_ok
goto health_loop

:version_ok
REM 6. 안정성 확인 — 15초 후 한 번 더 체크
timeout /t 15 /nobreak >nul
curl -s -o nul -w "%%{{http_code}}" http://127.0.0.1:{port}/health | findstr "200" >nul
if %ERRORLEVEL% NEQ 0 goto rollback

REM 7. 성공 — pending_rollback 삭제
del "{install_dir}\pending_rollback.json" 2>nul
del "%TEMP%\sv_health.tmp" 2>nul
del "%~f0"
exit /b 0

:rollback
REM 8. 실패 — 새 서버 프로세스 종료 시도
taskkill /IM stockvision-local.exe /F >nul 2>&1
timeout /t 3 /nobreak >nul

REM 9. 백업에서 복원
echo %DATE% %TIME% 업데이트 실패, 롤백 시작 >> "{install_dir}\logs\update.log"
xcopy /E /Y /Q "{backup_dir}\*" "{install_dir}\" >nul 2>&1

REM 10. pending_rollback 상태를 rolled_back으로 갱신
echo {{"status":"rolled_back","from_version":"{from_version}","to_version":"{target_version}","backup_dir":"{backup_dir}"}} > "{install_dir}\pending_rollback.json"

REM 11. 이전 버전 서버 시작
start "" "{install_dir}\stockvision-local.exe"

del "%TEMP%\sv_health.tmp" 2>nul
del "%~f0"
exit /b 1
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


def write_pending_rollback(
    install_dir: Path,
    from_version: str,
    to_version: str,
    backup_dir: str,
) -> Path:
    """설치 전 pending_rollback.json 마커 생성."""
    marker = install_dir / "pending_rollback.json"
    marker.write_text(json.dumps({
        "status": "installing",
        "from_version": from_version,
        "to_version": to_version,
        "timestamp": datetime.now().isoformat(),
        "backup_dir": backup_dir,
    }))
    logger.info("pending_rollback 마커 생성: %s", marker)
    return marker


def execute_update(
    installer_path: Path,
    install_dir: Path | None = None,
    target_version: str = "",
    from_version: str = "",
    backup_dir: str = "",
    port: int = 4020,
) -> None:
    """설치 .bat을 생성하고 현재 프로세스를 종료한다.

    확장된 bat는 health check + 버전 검증 + 롤백을 포함한다.
    """
    if install_dir is None:
        install_dir = get_install_dir()

    bat_content = _INSTALL_BAT_TEMPLATE.format(
        installer_path=str(installer_path),
        install_dir=str(install_dir),
        target_version=target_version,
        from_version=from_version,
        backup_dir=backup_dir,
        port=port,
    )
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
