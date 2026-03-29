"""버전 체크 — GitHub Releases + 하트비트 응답."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from packaging.version import Version

from local_server.__version__ import __version__ as _VERSION

logger = logging.getLogger(__name__)

GITHUB_RELEASES_URL = "https://api.github.com/repos/wansu-ha/StockVision/releases/latest"
INSTALLER_ASSET_NAME = "StockVision-Bridge-Setup.exe"
SHA256_ASSET_NAME = "StockVision-Bridge-Setup.exe.sha256"


@dataclass
class UpdateInfo:
    """업데이트 정보."""
    available: bool
    latest: str
    current: str
    major_mismatch: bool
    download_url: str = ""
    sha256_url: str = ""
    release_notes: str = ""


def check_from_heartbeat(resp: dict[str, Any]) -> UpdateInfo | None:
    """하트비트 응답에서 버전 정보를 추출한다.

    Returns:
        UpdateInfo 또는 latest_version이 없으면 None.
    """
    latest = resp.get("latest_version")
    if not latest:
        return None

    download_url = resp.get("download_url", "")
    return _compare(_VERSION, latest, download_url, "")


async def check_from_github() -> UpdateInfo | None:
    """GitHub Releases API에서 최신 버전을 확인한다.

    Returns:
        UpdateInfo 또는 릴리즈가 없으면 None.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(GITHUB_RELEASES_URL)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.warning("GitHub Releases API 조회 실패")
        return None

    tag = data.get("tag_name", "")
    latest = tag.lstrip("v")
    if not latest:
        return None

    # asset에서 인스톨러 + sha256 URL 찾기
    download_url = ""
    sha256_url = ""
    for asset in data.get("assets", []):
        name = asset.get("name", "")
        if name == INSTALLER_ASSET_NAME:
            download_url = asset.get("browser_download_url", "")
        elif name == SHA256_ASSET_NAME:
            sha256_url = asset.get("browser_download_url", "")

    release_notes = data.get("body", "") or ""
    return _compare(_VERSION, latest, download_url, sha256_url, release_notes)


def _compare(
    current: str, latest: str, download_url: str, sha256_url: str,
    release_notes: str = "",
) -> UpdateInfo:
    """현재 버전과 최신 버전을 비교한다."""
    try:
        cur_v = Version(current)
        lat_v = Version(latest)
    except Exception:
        return UpdateInfo(
            available=False, latest=latest, current=current,
            major_mismatch=False,
        )

    available = lat_v > cur_v
    major_mismatch = cur_v.major != lat_v.major

    return UpdateInfo(
        available=available,
        latest=latest,
        current=current,
        major_mismatch=major_mismatch,
        download_url=download_url,
        sha256_url=sha256_url,
        release_notes=release_notes,
    )
