"""UpdateManager — 업데이트 전체 흐름을 관리한다."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from local_server.__version__ import __version__ as _VERSION
from local_server.updater.version_checker import UpdateInfo, check_from_github, check_from_heartbeat
from local_server.updater.downloader import cleanup_temp, download_installer
from local_server.updater.installer import (
    backup_current,
    execute_update,
    get_install_dir,
    is_in_update_window,
    write_pending_rollback,
)

logger = logging.getLogger(__name__)


@dataclass
class UpdateState:
    """현재 업데이트 상태."""
    info: UpdateInfo | None = None
    download_progress: float = 0.0
    ready_to_install: bool = False
    installer_path: Path | None = None
    # S4 확장
    status: str = "idle"  # idle | checking | downloading | ready | installing | verifying | rolled_back | error
    last_error: str | None = None
    release_notes: str | None = None
    last_checked_at: str | None = None
    mandatory: bool = False

    def to_dict(self) -> dict[str, Any]:
        """health / update API 응답용 dict."""
        return {
            "status": self.status,
            "available": self.info.available if self.info else False,
            "latest": self.info.latest if self.info else "",
            "current": self.info.current if self.info else "",
            "major_mismatch": self.info.major_mismatch if self.info else False,
            "download_progress": self.download_progress,
            "ready_to_install": self.ready_to_install,
            "last_error": self.last_error,
            "last_checked_at": self.last_checked_at,
            "mandatory": self.mandatory,
            # release_notes는 의도적 제외 — 본문이 길어 별도 엔드포인트로 분리
        }


class UpdateManager:
    """업데이트 수명주기 관리."""

    def __init__(self) -> None:
        self.state = UpdateState()
        self._install_dir = get_install_dir()
        self._check_task: asyncio.Task | None = None
        self._install_task: asyncio.Task | None = None
        self._download_in_progress = False
        self._install_guard: Callable[[], bool] | None = None
        self._event_callback: Callable[[str, str], None] | None = None

    async def startup(self) -> None:
        """서버 시작 시 호출. 임시 파일 정리 + 최초 버전 체크."""
        cleanup_temp(self._install_dir)
        await self.check_update()

    async def check_update(self) -> UpdateInfo | None:
        """GitHub에서 최신 버전을 확인한다."""
        self.state.status = "checking"
        info = await check_from_github()
        self.state.last_checked_at = datetime.now().isoformat()
        if info:
            self.state.info = info
            self.state.release_notes = info.release_notes or self.state.release_notes
            self.state.mandatory = info.major_mismatch
            if info.major_mismatch:
                self._emit("update_mandatory", "서버 버전이 호환되지 않습니다. 업데이트가 필요합니다")
            if info.available:
                logger.info("업데이트 가능: %s → %s", info.current, info.latest)
                self._emit("update_available", f"새 버전 v{info.latest} 사용 가능")
            else:
                self.state.status = "idle"
        else:
            self.state.status = "idle"
        return info

    def on_heartbeat(self, resp: dict[str, Any]) -> None:
        """하트비트 응답에서 버전 정보를 갱신한다."""
        info = check_from_heartbeat(resp)
        if info and info.available:
            # GitHub URL이 없으면 하트비트의 download_url은 비어있을 수 있음
            if not info.download_url and self.state.info:
                info.download_url = self.state.info.download_url
                info.sha256_url = self.state.info.sha256_url
            self.state.info = info

    async def start_download(self) -> bool:
        """인스톨러를 백그라운드로 다운로드한다.

        Returns:
            다운로드 시작 여부.
        """
        info = self.state.info
        if not info or not info.available or not info.download_url:
            return False

        if self._download_in_progress or self.state.ready_to_install:
            return False

        self._download_in_progress = True
        self.state.status = "downloading"
        self.state.last_error = None

        def _on_progress(p: float) -> None:
            self.state.download_progress = round(p, 2)

        try:
            path = await download_installer(
                info.download_url, info.sha256_url,
                self._install_dir, _on_progress,
            )

            if path:
                self.state.installer_path = path
                self.state.ready_to_install = True
                self.state.download_progress = 1.0
                self.state.status = "ready"
                logger.info("다운로드 완료: %s", path)
                self._emit("download_complete", "업데이트 준비됨. 허용 시간에 자동 설치됩니다")
                return True

            self.state.download_progress = 0.0
            self.state.status = "error"
            self.state.last_error = "다운로드 실패 (SHA256 검증 또는 네트워크 오류)"
            return False
        finally:
            self._download_in_progress = False

    def set_event_callback(self, cb: Callable[[str, str], None]) -> None:
        """업데이트 이벤트 알림 콜백 주입. main.py에서 호출."""
        self._event_callback = cb

    def _emit(self, event: str, message: str) -> None:
        """이벤트 콜백이 설정된 경우 호출한다."""
        if self._event_callback:
            try:
                self._event_callback(event, message)
            except Exception as e:
                logger.warning("이벤트 콜백 오류 (무시): %s", e)

    def set_install_guard(self, guard: Callable[[], bool]) -> None:
        """설치 안전 조건 콜백 주입. main.py에서 호출."""
        self._install_guard = guard

    def is_safe_to_install(self) -> bool:
        """안전 조건만 확인 (시간 무관). 수동 API에서 사용."""
        if self._install_guard and not self._install_guard():
            return False
        return True

    def _can_install(self) -> bool:
        """시간 + 안전 조건 모두 확인. 자동 루프에서 사용."""
        from local_server.config import get_config
        cfg = get_config()
        if not is_in_update_window(
            cfg.get("update.no_update_start", "08:00"),
            cfg.get("update.no_update_end", "17:00"),
        ):
            return False
        return self.is_safe_to_install()

    def try_install(self) -> bool:
        """안전 조건 + 시간 확인 후 설치.

        Returns:
            설치 시작 여부 (True면 프로세스 종료됨).
        """
        if not self.state.ready_to_install or not self.state.installer_path:
            return False
        if not self._can_install():
            logger.debug("업데이트 설치 조건 미충족 — 대기")
            return False
        return self._execute_install()

    def try_install_force(self) -> bool:
        """시간/안전 조건 무시 — 수동 API용."""
        if not self.state.ready_to_install or not self.state.installer_path:
            return False
        return self._execute_install()

    def _execute_install(self) -> bool:
        """공통 설치 실행 로직."""
        self.state.status = "installing"
        self._emit("install_start", "업데이트 설치 중... 서버가 재시작됩니다")
        info = self.state.info
        backup_dir = backup_current(self._install_dir)
        backup_dir_str = str(backup_dir) if backup_dir else ""

        # pending_rollback 마커 생성
        write_pending_rollback(
            self._install_dir,
            from_version=info.current if info else _VERSION,
            to_version=info.latest if info else "",
            backup_dir=backup_dir_str,
        )

        from local_server.config import get_config
        cfg = get_config()
        port = cfg.get("server.port", 4020)

        execute_update(
            self.state.installer_path,
            install_dir=self._install_dir,
            target_version=info.latest if info else "",
            from_version=info.current if info else _VERSION,
            backup_dir=backup_dir_str,
            port=port,
        )
        return True  # 실제로는 sys.exit으로 도달 안 함

    # ── 백그라운드 루프 ──

    async def _check_loop(self) -> None:
        """1시간마다 새 버전 확인 + 자동 다운로드."""
        while True:
            await asyncio.sleep(3600)
            # 하트비트가 이미 최신 정보를 넣었으면 GitHub 재확인 불필요
            if not self.state.info or not self.state.info.available:
                await self.check_update()
            if (self.state.info and self.state.info.available
                    and not self.state.ready_to_install
                    and not self._download_in_progress):
                from local_server.config import get_config
                cfg = get_config()
                if cfg.get("update.auto_enabled", True):
                    await self.start_download()

    async def _install_loop(self) -> None:
        """ready_to_install이면 주기적으로 설치 시도.

        첫 1회는 즉시 평가 (부팅 시 이미 ready 상태 대응).
        """
        first = True
        while True:
            if first:
                first = False
            else:
                await asyncio.sleep(600)  # 10분
            if not self.state.ready_to_install:
                continue
            self.try_install()

    async def start_background_tasks(self) -> None:
        """체크 루프 + 설치 루프 시작. 중복 호출 무시."""
        if self._check_task is None or self._check_task.done():
            self._check_task = asyncio.create_task(self._check_loop())
        if self._install_task is None or self._install_task.done():
            self._install_task = asyncio.create_task(self._install_loop())
        logger.info("업데이트 백그라운드 태스크 시작")

    async def shutdown(self) -> None:
        """백그라운드 태스크 정리."""
        for task in (self._check_task, self._install_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._check_task = None
        self._install_task = None
        logger.info("업데이트 백그라운드 태스크 종료")


# 싱글톤
_manager: UpdateManager | None = None


def get_update_manager() -> UpdateManager:
    """전역 UpdateManager 인스턴스."""
    global _manager
    if _manager is None:
        _manager = UpdateManager()
    return _manager
