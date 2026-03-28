"""UpdateManager — 업데이트 전체 흐름을 관리한다."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from local_server.updater.version_checker import UpdateInfo, check_from_github, check_from_heartbeat
from local_server.updater.downloader import cleanup_temp, download_installer
from local_server.updater.installer import (
    backup_current,
    execute_update,
    get_install_dir,
    is_in_update_window,
)

logger = logging.getLogger(__name__)


@dataclass
class UpdateState:
    """현재 업데이트 상태."""
    info: UpdateInfo | None = None
    download_progress: float = 0.0
    ready_to_install: bool = False
    installer_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """health API 응답용 dict."""
        if not self.info:
            return {
                "available": False,
                "latest": "",
                "major_mismatch": False,
                "download_progress": 0.0,
                "ready_to_install": False,
            }
        return {
            "available": self.info.available,
            "latest": self.info.latest,
            "major_mismatch": self.info.major_mismatch,
            "download_progress": self.download_progress,
            "ready_to_install": self.ready_to_install,
        }


class UpdateManager:
    """업데이트 수명주기 관리."""

    def __init__(self) -> None:
        self.state = UpdateState()
        self._install_dir = get_install_dir()
        self._check_task: asyncio.Task | None = None
        self._install_task: asyncio.Task | None = None

    async def startup(self) -> None:
        """서버 시작 시 호출. 임시 파일 정리 + 최초 버전 체크."""
        cleanup_temp(self._install_dir)
        await self.check_update()

    async def check_update(self) -> UpdateInfo | None:
        """GitHub에서 최신 버전을 확인한다."""
        info = await check_from_github()
        if info:
            self.state.info = info
            if info.available:
                logger.info("업데이트 가능: %s → %s", info.current, info.latest)
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

        if self.state.ready_to_install:
            return False  # 이미 다운로드 완료

        def _on_progress(p: float) -> None:
            self.state.download_progress = round(p, 2)

        path = await download_installer(
            info.download_url, info.sha256_url,
            self._install_dir, _on_progress,
        )

        if path:
            self.state.installer_path = path
            self.state.ready_to_install = True
            self.state.download_progress = 1.0
            logger.info("다운로드 완료: %s", path)
            return True

        self.state.download_progress = 0.0
        return False

    def try_install(self, no_update_start: str, no_update_end: str) -> bool:
        """허용 시간이면 설치를 실행한다.

        Returns:
            설치 시작 여부 (True면 프로세스 종료됨).
        """
        if not self.state.ready_to_install or not self.state.installer_path:
            return False

        if not is_in_update_window(no_update_start, no_update_end):
            logger.debug("업데이트 차단 시간 — 설치 대기")
            return False

        backup_current(self._install_dir)
        execute_update(self.state.installer_path)
        return True  # 실제로는 sys.exit으로 도달 안 함


# 싱글톤
_manager: UpdateManager | None = None


def get_update_manager() -> UpdateManager:
    """전역 UpdateManager 인스턴스."""
    global _manager
    if _manager is None:
        _manager = UpdateManager()
    return _manager
