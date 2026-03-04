"""
포트폴리오 집계 서비스

- VirtualAccount + VirtualPosition + VirtualTrade 기반
- 현재가: yfinance 실시간 조회 (5분 캐시)
"""
import logging
from datetime import datetime, timedelta

import yfinance as yf
from sqlalchemy.orm import Session

from app.models.virtual_trading import VirtualAccount, VirtualPosition, VirtualTrade

logger = logging.getLogger(__name__)

_price_cache: dict[str, tuple[float, datetime]] = {}
_PRICE_TTL = timedelta(minutes=5)


def _get_price(symbol: str) -> float | None:
    now = datetime.utcnow()
    cached = _price_cache.get(symbol)
    if cached and now - cached[1] < _PRICE_TTL:
        return cached[0]
    try:
        ticker = yf.Ticker(symbol)
        price  = ticker.fast_info.last_price
        if price:
            _price_cache[symbol] = (float(price), now)
            return float(price)
    except Exception as e:
        logger.warning(f"현재가 조회 실패 ({symbol}): {e}")
    return None


def get_portfolio(db: Session, account_id: int) -> dict:
    account = db.query(VirtualAccount).filter(VirtualAccount.id == account_id).first()
    if not account:
        return {}

    positions_raw = (
        db.query(VirtualPosition)
        .filter(VirtualPosition.account_id == account_id, VirtualPosition.quantity > 0)
        .all()
    )

    positions = []
    positions_value = 0.0
    for p in positions_raw:
        current = _get_price(p.symbol) or p.current_price or p.avg_price
        pnl     = (current - p.avg_price) * p.quantity
        pnl_pct = (current / p.avg_price - 1) * 100 if p.avg_price else 0
        val     = current * p.quantity
        positions_value += val
        positions.append({
            "symbol":        p.symbol,
            "quantity":      p.quantity,
            "avg_price":     round(p.avg_price, 2),
            "current_price": round(current, 2),
            "unrealized_pnl": round(pnl, 2),
            "pnl_pct":       round(pnl_pct, 2),
        })

    total_value = account.current_balance + positions_value
    total_pnl   = total_value - account.initial_balance

    # 포지션별 비중 계산
    for p in positions:
        p["weight_pct"] = round(p["current_price"] * p["quantity"] / total_value * 100, 1) if total_value else 0

    return {
        "account_id":       account_id,
        "account_name":     account.name,
        "total_value":      round(total_value, 2),
        "cash_balance":     round(account.current_balance, 2),
        "positions_value":  round(positions_value, 2),
        "total_pnl":        round(total_pnl, 2),
        "total_pnl_pct":    round(total_pnl / account.initial_balance * 100, 2) if account.initial_balance else 0,
        "positions":        positions,
    }


def get_equity_curve(db: Session, account_id: int, days: int = 30) -> list[dict]:
    """날짜별 포트폴리오 가치 (VirtualTrade 기반 재구성)"""
    since = datetime.utcnow() - timedelta(days=days)
    trades = (
        db.query(VirtualTrade)
        .filter(VirtualTrade.account_id == account_id, VirtualTrade.timestamp >= since)
        .order_by(VirtualTrade.timestamp)
        .all()
    )

    # 거래 없으면 현재 account 기준 단순 반환
    if not trades:
        account = db.query(VirtualAccount).filter(VirtualAccount.id == account_id).first()
        if not account:
            return []
        return [{"date": datetime.utcnow().date().isoformat(), "equity": account.current_balance}]

    # 일별 집계
    by_date: dict[str, float] = {}
    running = 0.0
    for t in trades:
        d = t.timestamp.date().isoformat()
        if t.trade_type == "BUY":
            running -= t.total_amount or 0
        else:
            running += (t.total_amount or 0) + (t.realized_pnl or 0)
        by_date[d] = running

    return [{"date": k, "equity": round(v, 2)} for k, v in sorted(by_date.items())]


def get_sector_allocation(db: Session, account_id: int) -> list[dict]:
    from app.models.stock import Stock
    account = db.query(VirtualAccount).filter(VirtualAccount.id == account_id).first()
    if not account:
        return []

    positions_raw = (
        db.query(VirtualPosition)
        .filter(VirtualPosition.account_id == account_id, VirtualPosition.quantity > 0)
        .all()
    )

    sectors: dict[str, float] = {}
    total = account.current_balance
    for p in positions_raw:
        price = _get_price(p.symbol) or p.avg_price
        val   = price * p.quantity
        total += val
        # sector 조회
        stock = db.query(Stock).filter(Stock.symbol == p.symbol).first()
        sector = stock.sector if stock else "기타"
        sectors[sector] = sectors.get(sector, 0) + val

    sectors["현금"] = account.current_balance
    return [
        {"sector": k, "value": round(v, 2), "weight_pct": round(v / total * 100, 1) if total else 0}
        for k, v in sectors.items()
    ]
