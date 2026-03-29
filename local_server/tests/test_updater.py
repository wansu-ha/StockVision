"""updater 모듈 테스트."""
from __future__ import annotations

import asyncio
import hashlib
import json
import tempfile
from datetime import time as dtime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from local_server.updater.version_checker import UpdateInfo, _compare, check_from_heartbeat
from local_server.updater.installer import (
    is_in_update_window, backup_current, _cleanup_old_backups,
    write_pending_rollback, _INSTALL_BAT_TEMPLATE,
)
from local_server.updater.downloader import cleanup_temp, _verify_sha256
from local_server.updater.manager import UpdateState, UpdateManager


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

    def test_extended_fields(self) -> None:
        """S4 확장 필드 존재 확인."""
        state = UpdateState()
        d = state.to_dict()
        assert d["status"] == "idle"
        assert d["last_error"] is None
        assert d["last_checked_at"] is None
        assert d["mandatory"] is False
        assert "release_notes" not in d  # 별도 엔드포인트로 분리

    def test_status_transitions(self) -> None:
        """상태 전이 확인."""
        state = UpdateState()
        assert state.status == "idle"
        state.status = "checking"
        assert state.status == "checking"
        state.status = "downloading"
        assert state.status == "downloading"
        state.status = "ready"
        assert state.status == "ready"
        state.status = "installing"
        assert state.status == "installing"


# ── S3: SHA256 fail-closed ──


class TestSHA256FailClosed:
    """SHA256 검증이 fail-closed인지 확인."""

    @pytest.mark.asyncio
    async def test_sha256_fail_closed(self) -> None:
        """SHA256 파일 다운로드 실패 → False (fail-closed)."""
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"test installer data")
            file_path = Path(f.name)
        try:
            # 존재하지 않는 URL로 SHA256 검증
            result = await _verify_sha256(file_path, "http://invalid.local/bad.sha256")
            assert result is False
        finally:
            file_path.unlink(missing_ok=True)


# ── S1: 스케줄러 ──


class TestBackgroundTasks:
    """백그라운드 태스크 관리."""

    @pytest.mark.asyncio
    async def test_start_background_tasks_idempotent(self) -> None:
        """중복 호출 시 태스크 재생성 안 함."""
        mgr = UpdateManager.__new__(UpdateManager)
        mgr.state = UpdateState()
        mgr._install_dir = Path(".")
        mgr._check_task = None
        mgr._install_task = None
        mgr._download_in_progress = False
        mgr._install_guard = None
        mgr._event_callback = None

        await mgr.start_background_tasks()
        task1_check = mgr._check_task
        task1_install = mgr._install_task
        assert task1_check is not None
        assert task1_install is not None

        # 두 번째 호출 — 같은 태스크 유지
        await mgr.start_background_tasks()
        assert mgr._check_task is task1_check
        assert mgr._install_task is task1_install

        await mgr.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_cancels_tasks(self) -> None:
        """shutdown 호출 시 태스크 cancel."""
        mgr = UpdateManager.__new__(UpdateManager)
        mgr.state = UpdateState()
        mgr._install_dir = Path(".")
        mgr._check_task = None
        mgr._install_task = None
        mgr._download_in_progress = False
        mgr._install_guard = None
        mgr._event_callback = None

        await mgr.start_background_tasks()
        assert mgr._check_task is not None

        await mgr.shutdown()
        assert mgr._check_task is None
        assert mgr._install_task is None


# ── S6: 안전 조건 ──


class TestInstallGuard:
    """설치 안전 조건 검사."""

    def test_install_blocked_engine_running(self) -> None:
        """guard가 False → _can_install() False."""
        mgr = UpdateManager.__new__(UpdateManager)
        mgr.state = UpdateState()
        mgr._install_dir = Path(".")
        mgr._check_task = None
        mgr._install_task = None
        mgr._download_in_progress = False
        mgr._install_guard = lambda: False  # 엔진 실행 중
        mgr._event_callback = None

        assert mgr.is_safe_to_install() is False

        with patch("local_server.updater.manager.is_in_update_window", return_value=True):
            assert mgr._can_install() is False

    def test_install_allowed_when_safe(self) -> None:
        """guard가 True + 시간 허용 → _can_install() True."""
        mgr = UpdateManager.__new__(UpdateManager)
        mgr.state = UpdateState()
        mgr._install_dir = Path(".")
        mgr._check_task = None
        mgr._install_task = None
        mgr._download_in_progress = False
        mgr._install_guard = lambda: True
        mgr._event_callback = None

        with patch("local_server.updater.manager.is_in_update_window", return_value=True):
            assert mgr._can_install() is True

    def test_is_safe_without_guard(self) -> None:
        """guard 미설정 → 항상 True."""
        mgr = UpdateManager.__new__(UpdateManager)
        mgr.state = UpdateState()
        mgr._install_guard = None
        assert mgr.is_safe_to_install() is True


# ── S6: try_install 시그니처 ──


class TestTryInstall:
    """try_install 통일 시그니처."""

    def test_try_install_not_ready(self) -> None:
        """ready_to_install False → 설치 안 됨."""
        mgr = UpdateManager.__new__(UpdateManager)
        mgr.state = UpdateState()
        mgr._install_dir = Path(".")
        mgr._install_guard = None
        mgr._event_callback = None
        assert mgr.try_install() is False

    def test_try_install_force_not_ready(self) -> None:
        """ready_to_install False → force도 설치 안 됨."""
        mgr = UpdateManager.__new__(UpdateManager)
        mgr.state = UpdateState()
        mgr._install_dir = Path(".")
        mgr._install_guard = None
        mgr._event_callback = None
        assert mgr.try_install_force() is False


# ── S7: 롤백 마커 ──


class TestRollbackMarker:
    """pending_rollback.json 마커."""

    def test_rollback_marker_written(self, tmp_path: Path) -> None:
        """설치 전 마커 생성."""
        marker = write_pending_rollback(
            tmp_path,
            from_version="0.2.0",
            to_version="0.3.0",
            backup_dir=str(tmp_path / "backup" / "v0.2.0"),
        )
        assert marker.exists()
        data = json.loads(marker.read_text())
        assert data["status"] == "installing"
        assert data["from_version"] == "0.2.0"
        assert data["to_version"] == "0.3.0"

    def test_rollback_marker_cleaned(self, tmp_path: Path) -> None:
        """마커 삭제."""
        marker = write_pending_rollback(tmp_path, "0.2.0", "0.3.0", "")
        assert marker.exists()
        marker.unlink()
        assert not marker.exists()

    def test_rolled_back_state_on_startup(self, tmp_path: Path) -> None:
        """rolled_back 마커 → 상태 반영."""
        marker = tmp_path / "pending_rollback.json"
        marker.write_text(json.dumps({
            "status": "rolled_back",
            "from_version": "0.2.0",
            "to_version": "0.3.0",
        }))
        data = json.loads(marker.read_text())
        assert data["status"] == "rolled_back"

        # main.py 로직 시뮬레이션
        state = UpdateState()
        state.status = data["status"]
        state.last_error = f"v{data['to_version']} 업데이트 실패, v{data['from_version']}으로 복원됨"
        marker.unlink()

        assert state.status == "rolled_back"
        assert "0.3.0" in state.last_error
        assert not marker.exists()

    def test_verifier_bat_template_has_target_version(self) -> None:
        """bat 템플릿에 target_version 플레이스홀더 포함."""
        assert "{target_version}" in _INSTALL_BAT_TEMPLATE
        assert "{backup_dir}" in _INSTALL_BAT_TEMPLATE
        assert "{port}" in _INSTALL_BAT_TEMPLATE
        assert "{install_dir}" in _INSTALL_BAT_TEMPLATE


# ── S2: 하트비트 ──


class TestHeartbeatIntegration:
    """하트비트 → on_heartbeat 호출."""

    def test_heartbeat_triggers_on_heartbeat(self) -> None:
        """on_heartbeat 호출 시 state 갱신."""
        mgr = UpdateManager.__new__(UpdateManager)
        mgr.state = UpdateState()
        mgr._install_dir = Path(".")
        mgr._check_task = None
        mgr._install_task = None
        mgr._download_in_progress = False
        mgr._install_guard = None
        mgr._event_callback = None

        # 초기 info 세팅 (GitHub URL 보유)
        mgr.state.info = UpdateInfo(
            available=False, latest="0.2.0", current="0.2.0",
            major_mismatch=False, download_url="http://dl", sha256_url="http://sha",
        )

        with patch("local_server.updater.version_checker._VERSION", "0.2.0"):
            mgr.on_heartbeat({"latest_version": "0.3.0", "download_url": ""})

        assert mgr.state.info.available is True
        assert mgr.state.info.latest == "0.3.0"
        # GitHub URL이 없으면 기존 URL 유지
        assert mgr.state.info.download_url == "http://dl"


# ── S1: 다운로드 중복 방지 ──


class TestDownloadGuard:
    """다운로드 중복 방지."""

    @pytest.mark.asyncio
    async def test_duplicate_download_blocked(self) -> None:
        """_download_in_progress True → start_download False."""
        mgr = UpdateManager.__new__(UpdateManager)
        mgr.state = UpdateState(
            info=UpdateInfo(
                available=True, latest="0.3.0", current="0.2.0",
                major_mismatch=False, download_url="http://dl", sha256_url="",
            ),
        )
        mgr._install_dir = Path(".")
        mgr._download_in_progress = True
        mgr._event_callback = None

        result = await mgr.start_download()
        assert result is False
