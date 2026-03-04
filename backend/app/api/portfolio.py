from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.core.database import get_db
from app.services.portfolio import get_portfolio, get_equity_curve, get_sector_allocation

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"])


@router.get("/{account_id}")
def portfolio(account_id: int, db: Session = Depends(get_db), _user=Depends(current_user)):
    data = get_portfolio(db, account_id)
    if not data:
        raise HTTPException(status_code=404, detail="계좌 없음")
    return {"success": True, "data": data}


@router.get("/{account_id}/equity-curve")
def equity_curve(
    account_id: int,
    period:     str     = Query("30d"),
    db:         Session = Depends(get_db),
    _user=Depends(current_user),
):
    days_map = {"7d": 7, "30d": 30, "90d": 90, "180d": 180}
    days = days_map.get(period, 30)
    data = get_equity_curve(db, account_id, days)
    return {"success": True, "data": data}


@router.get("/{account_id}/sector-allocation")
def sector_allocation(
    account_id: int,
    db:         Session = Depends(get_db),
    _user=Depends(current_user),
):
    data = get_sector_allocation(db, account_id)
    return {"success": True, "data": data}
