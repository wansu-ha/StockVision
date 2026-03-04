from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.templates import StrategyTemplate

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _serialize(t: StrategyTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "category": t.category,
        "difficulty": t.difficulty,
        "rule_json": t.rule_json,
        "backtest_summary": t.backtest_summary,
        "tags": t.tags or [],
    }


@router.get("")
def list_templates(db: Session = Depends(get_db)):
    rows = db.query(StrategyTemplate).filter(StrategyTemplate.is_active == True).all()  # noqa: E712
    return {"success": True, "data": [_serialize(t) for t in rows], "count": len(rows)}


@router.get("/{template_id}")
def get_template(template_id: int, db: Session = Depends(get_db)):
    t = db.query(StrategyTemplate).filter(
        StrategyTemplate.id == template_id,
        StrategyTemplate.is_active == True,  # noqa: E712
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")
    return {"success": True, "data": _serialize(t)}
