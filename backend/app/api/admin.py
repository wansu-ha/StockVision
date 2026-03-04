from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models.auth import User, OnboardingState
from app.models.templates import StrategyTemplate

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── 통계 ──────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    cutoff_30d = datetime.utcnow() - timedelta(days=30)
    active_30d = db.query(User).filter(User.created_at >= cutoff_30d).count()
    cutoff_7d = datetime.utcnow() - timedelta(days=7)
    new_7d = db.query(User).filter(User.created_at >= cutoff_7d).count()

    onboarding_done = db.query(OnboardingState).filter(
        OnboardingState.completed_at.isnot(None)
    ).count()

    total_templates = db.query(StrategyTemplate).count()
    active_templates = db.query(StrategyTemplate).filter(StrategyTemplate.is_active == True).count()  # noqa: E712

    return {
        "success": True,
        "data": {
            "users": {
                "total": total_users,
                "active_30d": active_30d,
                "new_7d": new_7d,
                "onboarding_done": onboarding_done,
            },
            "templates": {
                "total": total_templates,
                "active": active_templates,
            },
        },
    }


# ── 사용자 목록 ────────────────────────────────────────────────────────

@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * limit
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    total = db.query(User).count()
    return {
        "success": True,
        "data": [
            {
                "id": u.id,
                "email": u.email,
                "nickname": u.nickname,
                "role": u.role,
                "email_verified": u.email_verified,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


# ── 관리자 전략 템플릿 CRUD ────────────────────────────────────────────

class TemplateBody(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None
    difficulty: str | None = None
    rule_json: dict | None = None
    backtest_summary: dict | None = None
    tags: list[str] = []
    is_active: bool = True


@router.get("/templates")
def list_all_templates(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(StrategyTemplate).all()
    return {
        "success": True,
        "data": [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "difficulty": t.difficulty,
                "is_active": t.is_active,
                "backtest_summary": t.backtest_summary,
                "tags": t.tags or [],
            }
            for t in rows
        ],
    }


@router.post("/templates", status_code=201)
def create_template(body: TemplateBody, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    t = StrategyTemplate(**body.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"success": True, "data": {"id": t.id}}


@router.put("/templates/{template_id}")
def update_template(
    template_id: int,
    body: TemplateBody,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    t = db.query(StrategyTemplate).filter(StrategyTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(t, field, value)
    db.commit()
    return {"success": True}


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    t = db.query(StrategyTemplate).filter(StrategyTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")
    t.is_active = False  # soft delete
    db.commit()
    return {"success": True}
