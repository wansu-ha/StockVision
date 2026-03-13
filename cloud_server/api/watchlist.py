"""
관심종목 CRUD API

GET    /api/v1/watchlist          → 내 관심종목 목록
POST   /api/v1/watchlist          → 관심종목 등록
DELETE /api/v1/watchlist/:symbol  → 관심종목 해제
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import current_user
from cloud_server.core.database import get_db
from cloud_server.services.watchlist_service import (
    add_to_watchlist,
    get_watchlist,
    remove_from_watchlist,
)

router = APIRouter(prefix="/api/v1/watchlist", tags=["watchlist"])


class WatchlistAddBody(BaseModel):
    symbol: str


@router.get("")
def list_watchlist(
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """내 관심종목 목록"""
    items = get_watchlist(db, user["sub"])
    return {"success": True, "data": items, "count": len(items)}


@router.post("")
def add_watchlist(
    body: WatchlistAddBody,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """관심종목 등록"""
    item = add_to_watchlist(db, user["sub"], body.symbol)
    return {"success": True, "data": item}


@router.delete("/{symbol}")
def remove_watchlist(
    symbol: str,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """관심종목 해제"""
    deleted = remove_from_watchlist(db, user["sub"], symbol)
    if not deleted:
        raise HTTPException(status_code=404, detail="관심종목에 없는 종목입니다.")
    return {"success": True}
