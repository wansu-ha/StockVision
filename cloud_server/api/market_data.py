"""시장 데이터 API — 가격, 현재가, 재무, 배당.

GET /api/v1/stocks/{symbol}/bars        일봉/주봉/월봉 OHLCV
GET /api/v1/stocks/{symbol}/quote       현재가 (지연)
GET /api/v1/stocks/{symbol}/financials  재무 데이터
GET /api/v1/stocks/{symbol}/dividends   배당 이력
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import current_user
from cloud_server.core.database import get_db
from cloud_server.data.factory import get_aggregator
from cloud_server.models.market import StockMaster

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stocks", tags=["market-data"])


@router.get("/{symbol}/bars")
async def get_bars(
    symbol: str,
    start: date = Query(default=None),
    end: date = Query(default=None),
    resolution: str = Query("1d", pattern="^(1d|1w|1mo)$"),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """일봉/주봉/월봉 OHLCV 조회. DB 캐시 → on-demand 수집 폴백.

    resolution:
      1d  — 일봉 (기본값)
      1w  — 주봉 (일봉 집계)
      1mo — 월봉 (일봉 집계)
    """
    if start is None:
        start = date.today() - timedelta(days=365)
    if end is None:
        end = date.today()

    # DB 캐시 확인 — 기간 대비 충분한 데이터가 있을 때만 캐시 사용
    from cloud_server.models.market import DailyBar
    cached = db.query(DailyBar).filter(
        DailyBar.symbol == symbol,
        DailyBar.date >= start,
        DailyBar.date <= end,
    ).order_by(DailyBar.date).all()

    total_days = (end - start).days
    expected_min = max(total_days * 0.5, 3)  # 영업일 비율 + 최소 3건

    if cached and len(cached) >= expected_min:
        data = [
            {
                "date": str(b.date),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in cached
        ]
        if resolution != "1d":
            data = _aggregate_daily_bars(data, resolution)
        return {"success": True, "data": data, "count": len(data), "resolution": resolution}

    # on-demand 수집
    agg = get_aggregator()
    bars = await agg.get_daily_bars(symbol, start, end)
    if not bars:
        return {"success": True, "data": [], "count": 0, "resolution": resolution}

    # DB 저장
    from cloud_server.services.market_repository import MarketRepository
    repo = MarketRepository(db)
    for bar in bars:
        repo.save_daily_bar(symbol, bar.date, {
            "open": int(bar.open) if bar.open else None,
            "high": int(bar.high) if bar.high else None,
            "low": int(bar.low) if bar.low else None,
            "close": int(bar.close) if bar.close else None,
            "volume": bar.volume,
        })

    data = sorted(
        [
            {
                "date": str(b.date),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in bars
        ],
        key=lambda x: x["date"],
    )
    if resolution != "1d":
        data = _aggregate_daily_bars(data, resolution)
    return {"success": True, "data": data, "count": len(data), "resolution": resolution}


def _aggregate_daily_bars(bars: list[dict], resolution: str) -> list[dict]:
    """일봉 → 주봉(1w) 또는 월봉(1mo) 집계."""
    if not bars:
        return []

    from itertools import groupby
    from datetime import date as date_type

    def week_key(b):
        d = date_type.fromisoformat(b["date"]) if isinstance(b["date"], str) else b["date"]
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"

    def month_key(b):
        d = date_type.fromisoformat(b["date"]) if isinstance(b["date"], str) else b["date"]
        return f"{d.year}-{d.month:02d}"

    key_fn = week_key if resolution == "1w" else month_key

    result = []
    for _, group in groupby(bars, key=key_fn):
        group_list = list(group)
        result.append({
            "date": group_list[0]["date"],
            "open": group_list[0]["open"],
            "high": max(b["high"] for b in group_list if b.get("high") is not None),
            "low": min(b["low"] for b in group_list if b.get("low") is not None),
            "close": group_list[-1]["close"],
            "volume": sum(b.get("volume") or 0 for b in group_list),
        })
    return result


@router.get("/{symbol}/quote")
async def get_quote(
    symbol: str,
    user: dict = Depends(current_user),
):
    """현재가 조회 (지연 시세). 실시간 중계 아님."""
    agg = get_aggregator()
    quote = await agg.get_quote(symbol)
    if not quote:
        raise HTTPException(status_code=404, detail="시세를 조회할 수 없습니다.")
    return {
        "success": True,
        "data": {
            "symbol": quote.symbol,
            "price": quote.price,
            "change": quote.change,
            "change_pct": quote.change_pct,
            "volume": quote.volume,
            "timestamp": quote.timestamp,
        },
    }


@router.get("/{symbol}/financials")
async def get_financials(
    symbol: str,
    year: int = Query(...),
    quarter: int | None = Query(None, ge=1, le=4),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """재무 데이터 조회."""
    # symbol → corp_code 변환
    stock = db.query(StockMaster).filter(StockMaster.symbol == symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    if not stock.corp_code:
        raise HTTPException(status_code=404, detail="해당 종목의 기업 고유번호(corp_code)가 없습니다.")

    # DB 캐시 확인
    from cloud_server.models.fundamental import CompanyFinancial
    period = f"{year}Q{quarter}" if quarter else str(year)
    cached = db.query(CompanyFinancial).filter(
        CompanyFinancial.corp_code == stock.corp_code,
        CompanyFinancial.period == period,
    ).first()

    if cached:
        return {"success": True, "data": _financial_to_dict(cached)}

    # on-demand 수집
    agg = get_aggregator()
    result = await agg.get_financials(stock.corp_code, year, quarter)
    if not result:
        return {"success": True, "data": None}

    result.symbol = symbol

    # DB 저장
    fin = CompanyFinancial(
        corp_code=stock.corp_code,
        period=period,
        revenue=result.revenue,
        operating_income=result.operating_income,
        net_income=result.net_income,
        total_assets=result.total_assets,
        total_equity=result.total_equity,
        total_debt=result.total_debt,
        eps=result.eps,
        per=result.per,
        pbr=result.pbr,
        roe=result.roe,
        debt_ratio=result.debt_ratio,
        provider="dart",
    )
    db.add(fin)
    db.commit()

    return {"success": True, "data": _financial_to_dict(fin)}


@router.get("/{symbol}/dividends")
async def get_dividends(
    symbol: str,
    year: int | None = Query(None),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """배당 이력 조회."""
    # DB 캐시 확인
    from cloud_server.models.fundamental import CompanyDividend
    query = db.query(CompanyDividend).filter(CompanyDividend.symbol == symbol)
    if year:
        query = query.filter(CompanyDividend.fiscal_year == str(year))
    cached = query.order_by(CompanyDividend.fiscal_year.desc()).all()

    if cached:
        data = [_dividend_to_dict(d) for d in cached]
        return {"success": True, "data": data, "count": len(data)}

    # on-demand 수집
    agg = get_aggregator()
    results = await agg.get_dividends(symbol, year)
    if not results:
        return {"success": True, "data": [], "count": 0}

    # DB 저장
    for div in results:
        d = CompanyDividend(
            symbol=symbol,
            fiscal_year=div.fiscal_year,
            dividend_per_share=div.dividend_per_share,
            dividend_yield=div.dividend_yield,
            ex_date=div.ex_date,
            pay_date=div.pay_date,
            payout_ratio=div.payout_ratio,
            provider="yfinance",
        )
        db.merge(d)
    db.commit()

    data = [
        {
            "fiscal_year": d.fiscal_year,
            "dividend_per_share": d.dividend_per_share,
            "dividend_yield": d.dividend_yield,
            "ex_date": str(d.ex_date) if d.ex_date else None,
            "pay_date": str(d.pay_date) if d.pay_date else None,
            "payout_ratio": d.payout_ratio,
        }
        for d in results
    ]
    return {"success": True, "data": data, "count": len(data)}


def _financial_to_dict(f) -> dict:
    return {
        "corp_code": f.corp_code,
        "period": f.period,
        "revenue": f.revenue,
        "operating_income": f.operating_income,
        "net_income": f.net_income,
        "total_assets": f.total_assets,
        "total_equity": f.total_equity,
        "total_debt": f.total_debt,
        "eps": f.eps,
        "per": f.per,
        "pbr": f.pbr,
        "roe": f.roe,
        "debt_ratio": f.debt_ratio,
    }


def _dividend_to_dict(d) -> dict:
    return {
        "fiscal_year": d.fiscal_year,
        "dividend_per_share": d.dividend_per_share,
        "dividend_yield": d.dividend_yield,
        "ex_date": str(d.ex_date) if d.ex_date else None,
        "pay_date": str(d.pay_date) if d.pay_date else None,
        "payout_ratio": d.payout_ratio,
    }
