"""
AI 컨텍스트 API

GET /api/v1/context             최신 컨텍스트 스냅샷
GET /api/v1/context/variables   사용 가능한 변수 목록
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import current_user
from cloud_server.core.database import get_db
from cloud_server.services.context_service import ContextService, AVAILABLE_VARIABLES

router = APIRouter(prefix="/api/v1/context", tags=["context"])


@router.get("")
def get_context(
    _user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """최신 시장 컨텍스트 (RSI, EMA, 변동성 등)"""
    service = ContextService(db)
    data = service.get_current_context()
    return {"success": True, "data": data}


@router.get("/variables")
def get_variables(_user=Depends(current_user)):
    """규칙 조건에서 사용 가능한 변수 목록"""
    return {"success": True, "data": AVAILABLE_VARIABLES, "count": len(AVAILABLE_VARIABLES)}
