"""재무/배당 조회 API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from data_server.core.auth import verify_api_key
from data_server.core.database import get_db
from data_server.models.fundamental import CompanyDividend, CompanyFinancial
from data_server.models.market import StockMaster

router = APIRouter(tags=["financials"], dependencies=[Depends(verify_api_key)])


@router.get("/stocks/{symbol}/financials")
async def get_financials(
    symbol: str,
    year: int | None = Query(None),
    quarter: int | None = Query(None, ge=1, le=4),
    db: Session = Depends(get_db),
):
    stock = db.query(StockMaster).filter(StockMaster.symbol == symbol).first()
    if not stock or not stock.corp_code:
        return {"success": True, "data": None}

    q = db.query(CompanyFinancial).filter(
        CompanyFinancial.corp_code == stock.corp_code,
    )
    if year:
        period = f"{year}Q{quarter}" if quarter else str(year)
        q = q.filter(CompanyFinancial.period == period)

    results = q.order_by(CompanyFinancial.period.desc()).all()
    data = [
        {
            "period": f.period, "revenue": f.revenue,
            "operating_income": f.operating_income, "net_income": f.net_income,
            "eps": f.eps, "per": f.per, "pbr": f.pbr, "roe": f.roe,
        }
        for f in results
    ]
    return {"success": True, "data": data, "count": len(data)}


@router.get("/stocks/{symbol}/dividends")
async def get_dividends(
    symbol: str,
    year: int | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(CompanyDividend).filter(CompanyDividend.symbol == symbol)
    if year:
        q = q.filter(CompanyDividend.fiscal_year == str(year))
    results = q.order_by(CompanyDividend.fiscal_year.desc()).all()
    data = [
        {
            "fiscal_year": d.fiscal_year,
            "dividend_per_share": d.dividend_per_share,
            "dividend_yield": d.dividend_yield,
            "ex_date": str(d.ex_date) if d.ex_date else None,
            "pay_date": str(d.pay_date) if d.pay_date else None,
        }
        for d in results
    ]
    return {"success": True, "data": data, "count": len(data)}
