"""동적 수집 상태 조회 API."""
from fastapi import APIRouter, Depends

from data_server.core.auth import verify_api_key
from data_server.services.dynamic_collector import get_task_status

router = APIRouter(tags=["collection"], dependencies=[Depends(verify_api_key)])


@router.get("/collection/{task_id}")
async def get_collection_status(task_id: str):
    """수집 태스크 상태 조회."""
    status = get_task_status(task_id)
    if not status:
        return {"success": False, "message": "태스크를 찾을 수 없습니다."}
    return {"success": True, **status}
