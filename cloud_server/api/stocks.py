"""
종목 메타데이터 검색 API

GET /api/v1/stocks/search?q=삼성   → StockMaster 검색 (상위 20건)
GET /api/v1/stocks/:symbol         → 종목 상세 메타데이터
GET /api/v1/stocks/master          → 전체 종목 마스터 (로컬 서버 캐시용)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import current_user
from cloud_server.core.database import get_db
from cloud_server.services.stock_service import get_stock, search_stocks

router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])


@router.get("/search")
def search(
    q: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """종목 검색 — 이름 또는 코드로 검색 (메타데이터만, 시세 미포함)"""
    results = search_stocks(db, q, limit)
    return {"success": True, "data": results, "count": len(results)}


@router.get("/master")
def master_list(
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """전체 종목 마스터 목록 (로컬 서버 sync용)"""
    from cloud_server.models.market import StockMaster

    rows = db.query(StockMaster).filter(
        StockMaster.is_active == True  # noqa: E712
    ).order_by(StockMaster.symbol).all()

    data = [
        {"symbol": r.symbol, "name": r.name, "market": r.market}
        for r in rows
    ]
    return {"success": True, "data": data, "count": len(data)}


@router.get("/{symbol}")
def detail(
    symbol: str,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """종목 상세 메타데이터"""
    result = get_stock(db, symbol)
    if not result:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    return {"success": True, "data": result}
