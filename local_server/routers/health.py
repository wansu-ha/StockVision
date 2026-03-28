from fastapi import APIRouter

from local_server.__version__ import __version__ as _VERSION

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    from local_server.updater.manager import get_update_manager

    mgr = get_update_manager()
    return {
        "status": "ok",
        "version": _VERSION,
        "update_status": mgr.state.to_dict(),
    }
