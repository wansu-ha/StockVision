"""
하트비트 수신 API

POST /api/v1/heartbeat   로컬 서버 상태 보고 (JWT 인증)
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import current_user
from cloud_server.core.database import get_db
from cloud_server.services.heartbeat_service import record_heartbeat

router = APIRouter(prefix="/api/v1", tags=["heartbeat"])


class HeartbeatBody(BaseModel):
    uuid: str
    version: str | None = None
    os: str | None = None
    kiwoom_connected: bool | None = None
    engine_running: bool | None = None
    active_rules_count: int | None = None
    timestamp: datetime


@router.post("/heartbeat")
def post_heartbeat(
    body: HeartbeatBody,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """로컬 서버 하트비트 수신 + rules_version/context_version 반환"""
    result = record_heartbeat(user["sub"], body.model_dump(), db)
    return {"success": True, "data": result}
