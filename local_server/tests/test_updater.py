"""updater 모듈 테스트."""
from __future__ import annotations

import hashlib
import tempfile
from datetime import time as dtime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from local_server.updater.version_checker import UpdateInfo, _compare, check_from_heartbeat
from local_server.updater.installer import is_in_update_window, backup_current, _cleanup_old_backups
from local_server.updater.downloader import cleanup_temp
from local_server.updater.manager import UpdateState


# ── version_checker ──


class TestCompare:
    """버전 비교 로직."""

    def test_same_version(self) -> None:
        info = _compare("0.2.0", "0.2.0", "", "")
        assert not info.available
        assert not info.major_mismatch

    def test_minor_update(self) -> None:
        info = _compare("0.2.0", "0.3.0", "http://dl", "http://sha")
        assert info.available
        assert not info.major_mismatch
        assert info.download_url == "http://dl"
        assert info.sha256_url == "http://sha"

    def test_major_mismatch(self) -> None:
        info = _compare("0.2.0", "1.0.0", "", "")
        assert info.available
        assert info.major_mismatch

    def test_current_newer(self) -> None:
        info = _compare("1.0.0", "0.9.0", "", "")
        assert not info.available

    def test_invalid_version(self) -> None:
        info = _compare("invalid", "1.0.0", "", "")
        assert not info.available


class TestCheckFromHeartbeat:
    """하트비트 응답 파싱."""

    def test_with_latest_version(self) -> None:
        with patch("local_server.updater.version_checker._VERSION", "0.2.0"):
            info = check_from_heartbeat({"latest_version": "0.3.0", "download_url": ""})
        assert info is not None
        assert info.available

    def test_without_latest_version(self) -> None:
        info = check_from_heartbeat({})
        assert info is None

    def test_same_version(self) -> None:
        with patch("local_server.updater.version_checker._VERSION", "0.2.0"):
            info = check_from_heartbeat({"latest_version": "0.2.0"})
        assert info is not None
        assert not info.available


# ── installer ──


class TestUpdateWindow:
    """업데이트 허용 시간 판단."""

    def test_inside_no_update_window(self) -> None:
        """no_update 구간 안 → 업데이트 불가."""
        assert not is_in_update_window("08:00", "17:00", now=dtime(10, 0))

    def test_outside_no_update_window(self) -> None:
        """no_update 구간 밖 → 업데이트 가능."""
        assert is_in_update_window("08:00", "17:00", now=dtime(18, 0))

    def test_midnight(self) -> None:
        """자정 → 업데이트 가능."""
        assert is_in_update_window("08:00", "17:00", now=dtime(0, 30))

    def test_boundary_start(self) -> None:
        """정확히 start → 차단."""
        assert not is_in_update_window("08:00", "17:00", now=dtime(8, 0))

    def test_boundary_end(self) -> None:
        """정확히 end → 허용."""
        assert is_in_update_window("08:00", "17:00", now=dtime(17, 0))

    def test_invalid_time(self) -> None:
        """잘못된 시간 형식 → False."""
        assert not is_in_update_window("invalid", "17:00")


class TestBackup:
    """백업 로직."""

    def test_backup_creates_directory(self, tmp_path: Path) -> None:
        # 가짜 설치 디렉토리
        install = tmp_path / "install"
        install.mkdir()
        (install / "app.exe").write_text("fake")
        (install / "data.json").write_text("{}")

        with patch("local_server.updater.installer._VERSION", "0.2.0"):
            result = backup_current(install)

        assert result is not None
        assert (result / "app.exe").exists()
        assert (result / "data.json").exists()

    def test_cleanup_keeps_max(self, tmp_path: Path) -> None:
        backup_root = tmp_path / "backup"
        backup_root.mkdir()
        for i in range(5):
            d = backup_root / f"v0.{i}.0"
            d.mkdir()
            (d / "dummy").write_text(str(i))

        _cleanup_old_backups(backup_root, max_keep=2)
        remaining = list(backup_root.iterdir())
        assert len(remaining) == 2


# ── downloader ──


class TestCleanupTemp:
    """임시 파일 정리."""

    def test_removes_files(self, tmp_path: Path) -> None:
        temp = tmp_path / "temp"
        temp.mkdir()
        (temp / "installer.exe").write_text("incomplete")
        (temp / "partial.tmp").write_text("data")

        cleanup_temp(tmp_path)
        assert len(list(temp.iterdir())) == 0

    def test_no_temp_dir(self, tmp_path: Path) -> None:
        """temp/ 없으면 에러 안 남."""
        cleanup_temp(tmp_path)


# ── manager state ──


class TestUpdateState:
    """UpdateState.to_dict."""

    def test_empty_state(self) -> None:
        state = UpdateState()
        d = state.to_dict()
        assert not d["available"]
        assert d["latest"] == ""

    def test_with_info(self) -> None:
        info = UpdateInfo(
            available=True, latest="0.3.0", current="0.2.0",
            major_mismatch=False, download_url="http://x", sha256_url="",
        )
        state = UpdateState(info=info, download_progress=0.5)
        d = state.to_dict()
        assert d["available"]
        assert d["latest"] == "0.3.0"
        assert d["download_progress"] == 0.5
        assert not d["ready_to_install"]
