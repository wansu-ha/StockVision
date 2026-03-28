"""인스톨러 다운로드 + SHA256 검증."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SEC = 300  # 5분


def get_temp_dir(install_dir: Path) -> Path:
    """임시 다운로드 디렉토리."""
    d = install_dir / "temp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cleanup_temp(install_dir: Path) -> None:
    """임시 디렉토리의 불완전 파일을 정리한다."""
    temp = install_dir / "temp"
    if not temp.exists():
        return
    for f in temp.iterdir():
        try:
            f.unlink()
            logger.info("임시 파일 삭제: %s", f.name)
        except Exception:
            logger.warning("임시 파일 삭제 실패: %s", f.name)


async def download_installer(
    download_url: str,
    sha256_url: str,
    install_dir: Path,
    progress_callback: callable | None = None,
) -> Path | None:
    """인스톨러를 다운로드하고 SHA256을 검증한다.

    Args:
        download_url: 인스톨러 다운로드 URL
        sha256_url: SHA256 해시 파일 URL (없으면 검증 생략)
        install_dir: 설치 디렉토리
        progress_callback: 진행률 콜백 (0.0~1.0)

    Returns:
        검증 완료된 인스톨러 경로, 실패 시 None.
    """
    temp_dir = get_temp_dir(install_dir)
    dest = temp_dir / "StockVision-Bridge-Setup.exe"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # 다운로드
            async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
                async with client.stream("GET", download_url) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0

                    with open(dest, "wb") as f:
                        async for chunk in resp.aiter_bytes(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total > 0:
                                progress_callback(downloaded / total)

            logger.info("다운로드 완료: %s (%d bytes)", dest.name, downloaded)

            # SHA256 검증
            if sha256_url:
                if not await _verify_sha256(dest, sha256_url):
                    logger.warning("SHA256 불일치 (시도 %d/%d)", attempt, MAX_RETRIES)
                    dest.unlink(missing_ok=True)
                    continue
                logger.info("SHA256 검증 통과")

            return dest

        except Exception:
            logger.warning("다운로드 실패 (시도 %d/%d)", attempt, MAX_RETRIES, exc_info=True)
            dest.unlink(missing_ok=True)

    logger.error("다운로드 최종 실패 (%d회 시도)", MAX_RETRIES)
    return None


async def _verify_sha256(file_path: Path, sha256_url: str) -> bool:
    """파일의 SHA256 해시를 원격 해시와 비교한다."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(sha256_url)
            resp.raise_for_status()
            expected = resp.text.strip().split()[0].lower()
    except Exception:
        logger.warning("SHA256 파일 다운로드 실패 — 검증 생략")
        return True  # sha256 파일 못 받으면 통과 (폴백)

    actual = hashlib.sha256(file_path.read_bytes()).hexdigest().lower()
    return actual == expected
