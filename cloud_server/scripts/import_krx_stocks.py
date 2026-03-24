"""KRX 종목 마스터 임포트.

KRX 공식 데이터에서 KOSPI + KOSDAQ 전체 종목을 조회하여
stock_master 테이블에 upsert한다.

사용법:
    python -m cloud_server.scripts.import_krx_stocks
"""
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _fetch_krx_stocks() -> list[dict]:
    """pykrx로 KOSPI + KOSDAQ 전체 종목 조회."""
    from pykrx import stock as pykrx_stock

    today = datetime.today().strftime("%Y%m%d")
    rows: list[dict] = []
    for market in ("KOSPI", "KOSDAQ"):
        tickers = pykrx_stock.get_market_ticker_list(today, market=market)
        for ticker in tickers:
            name = pykrx_stock.get_market_ticker_name(ticker)
            rows.append({"symbol": ticker, "name": name, "market": market})
    return rows


def run() -> None:
    from cloud_server.core.database import get_db_session
    from cloud_server.models.market import StockMaster

    rows = _fetch_krx_stocks()
    print(f"KRX 종목 조회 완료: {len(rows)}개")

    db = get_db_session()
    try:
        inserted = updated = 0
        for row in rows:
            existing = db.query(StockMaster).filter_by(symbol=row["symbol"]).first()
            if existing:
                existing.name = row["name"]
                existing.market = row["market"]
                existing.is_active = True
                updated += 1
            else:
                db.add(StockMaster(
                    symbol=row["symbol"],
                    name=row["name"],
                    market=row["market"],
                    is_active=True,
                ))
                inserted += 1
        db.commit()
        print(f"DB 저장 완료 — 신규: {inserted}개, 갱신: {updated}개")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
