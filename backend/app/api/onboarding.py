from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.core.database import get_db
from app.models.auth import OnboardingState

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


def _get_or_create(db: Session, user_id: str) -> OnboardingState:
    state = db.query(OnboardingState).filter(OnboardingState.user_id == user_id).first()
    if not state:
        state = OnboardingState(user_id=user_id)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


@router.get("/status")
def get_status(user=Depends(current_user), db: Session = Depends(get_db)):
    state = _get_or_create(db, user["sub"])
    return {
        "success": True,
        "data": {
            "step_completed": state.step_completed,
            "risk_accepted": state.risk_accepted,
            "is_complete": state.completed_at is not None,
        },
    }


@router.post("/step/{n}")
def complete_step(n: int, user=Depends(current_user), db: Session = Depends(get_db)):
    if n < 1 or n > 6:
        raise HTTPException(status_code=400, detail="유효하지 않은 단계입니다 (1~6).")
    state = _get_or_create(db, user["sub"])
    if n > state.step_completed:
        state.step_completed = n
    if n == 6 and state.completed_at is None:
        state.completed_at = datetime.utcnow()
    db.commit()
    return {"success": True, "data": {"step_completed": state.step_completed}}


@router.post("/accept-risk")
def accept_risk(user=Depends(current_user), db: Session = Depends(get_db)):
    state = _get_or_create(db, user["sub"])
    state.risk_accepted = True
    state.risk_accepted_at = datetime.utcnow()
    if state.step_completed < 2:
        state.step_completed = 2
    db.commit()
    return {"success": True}
