"""
버전 체크 API (공개, 인증 불필요)

GET /api/v1/version   로컬 서버 버전 정보
"""
from fastapi import APIRouter

from cloud_server.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["version"])


@router.get("/version")
def get_version():
    """로컬 서버 최신 버전 정보"""
    return {
        "success": True,
        "data": {
            "latest": settings.LOCAL_SERVER_LATEST_VERSION,
            "min_supported": settings.LOCAL_SERVER_MIN_SUPPORTED,
            "download_url": settings.LOCAL_SERVER_DOWNLOAD_URL,
            "changelog": "",
        },
    }
