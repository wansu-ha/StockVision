"""종목 마스터 조회 API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from data_server.core.auth import verify_api_key
from data_server.core.database import get_db
from data_server.services.market_repository import MarketRepository

router = APIRouter(tags=["stocks"], dependencies=[Depends(verify_api_key)])


@router.get("/stocks")
async def list_stocks(
    market: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    repo = MarketRepository(db)
    stocks = repo.get_all_stocks(market=market, search=search)
    data = [
        {
            "symbol": s.symbol, "name": s.name,
            "market": s.market, "sector": s.sector,
            "is_active": s.is_active,
        }
        for s in stocks
    ]
    return {"success": True, "data": data, "count": len(data)}


@router.get("/stocks/{symbol}")
async def get_stock(symbol: str, db: Session = Depends(get_db)):
    repo = MarketRepository(db)
    stock = repo.get_stock(symbol)
    if not stock:
        return {"success": False, "message": "종목을 찾을 수 없습니다."}
    return {
        "success": True,
        "data": {
            "symbol": stock.symbol, "name": stock.name,
            "market": stock.market, "sector": stock.sector,
            "corp_code": stock.corp_code, "is_active": stock.is_active,
        },
    }
