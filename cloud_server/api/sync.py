"""
로컬 서버 동기화 API

로컬 서버가 JWT로 직접 호출하는 엔드포인트.
(대부분은 기존 /api/v1/rules, /api/v1/context 엔드포인트를 재사용)

GET /api/v1/templates   전략 템플릿 목록 (로컬 서버 캐시용)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import current_user
from cloud_server.core.database import get_db
from cloud_server.services.admin_service import list_templates

router = APIRouter(prefix="/api/v1", tags=["sync"])


@router.get("/templates")
def get_templates(
    _user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """
    전략 템플릿 목록 (로컬 서버 fetch 용).
    공개 템플릿만 반환.
    """
    from cloud_server.models.template import StrategyTemplate

    templates = db.query(StrategyTemplate).filter(
        StrategyTemplate.is_public == True  # noqa: E712
    ).order_by(StrategyTemplate.created_at.desc()).all()

    data = [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "buy_conditions": t.buy_conditions,
            "sell_conditions": t.sell_conditions,
            "default_params": t.default_params,
            "category": t.category,
        }
        for t in templates
    ]

    return {"success": True, "data": data, "count": len(data)}
