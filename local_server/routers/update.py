"""수동 업데이트 제어 API."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/update", tags=["update"])


@router.get("/status")
async def update_status():
    """현재 업데이트 상태 전체."""
    from local_server.updater.manager import get_update_manager
    return get_update_manager().state.to_dict()


@router.post("/check")
async def check_now():
    """즉시 버전 체크 + 자동 다운로드."""
    from local_server.updater.manager import get_update_manager
    from local_server.config import get_config

    mgr = get_update_manager()
    await mgr.check_update()

    if (mgr.state.info and mgr.state.info.available
            and not mgr.state.ready_to_install
            and not mgr._download_in_progress):
        cfg = get_config()
        if cfg.get("update.auto_enabled", True):
            asyncio.create_task(mgr.start_download())

    return mgr.state.to_dict()


@router.post("/install")
async def install_now(force: bool = False):
    """설치 시도 — 기본은 안전 조건 준수, force=true 시 강제."""
    from local_server.updater.manager import get_update_manager

    mgr = get_update_manager()
    if not mgr.state.ready_to_install:
        raise HTTPException(400, detail="설치 준비되지 않음")

    if not force:
        if not mgr.is_safe_to_install():
            raise HTTPException(
                409,
                detail="안전 조건 미충족 (엔진 실행 중 또는 미체결 주문 존재)",
            )

    mgr.try_install_force()
    return {"message": "설치 시작됨"}


@router.get("/release-notes")
async def release_notes():
    """최신 릴리즈 노트."""
    from local_server.updater.manager import get_update_manager
    mgr = get_update_manager()
    return {"notes": mgr.state.release_notes or ""}
