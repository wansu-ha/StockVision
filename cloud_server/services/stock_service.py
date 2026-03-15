"""
종목 메타데이터 비즈니스 로직

- StockMaster 검색 (이름/코드)
- 공공데이터포털 KRX 상장종목 수집 (일 1회)

공공데이터포털 API 응답 필드:
  srtnCd  — 단축코드 (A005930 형태, 앞 'A' 제거하여 6자리로 저장)
  itmsNm  — 종목명
  mrktCtg — 시장 구분 (KOSPI / KOSDAQ / KONEX)
  crno    — 법인등록번호
  corpNm  — 법인명
"""
import logging
import os
from datetime import date, timedelta

import httpx
from sqlalchemy import or_
from sqlalchemy.orm import Session

from cloud_server.models.market import StockMaster

logger = logging.getLogger(__name__)

_DATA_PORTAL_URL = (
    "https://apis.data.go.kr/1160100/service/GetKrxListedInfoService/getItemInfo"
)


def search_stocks(db: Session, query: str, limit: int = 20) -> list[dict]:
    """종목 검색 — name 또는 symbol 부분 매칭 (상위 N건)"""
    pattern = f"%{query}%"
    rows = (
        db.query(StockMaster)
        .filter(
            StockMaster.is_active == True,  # noqa: E712
            or_(
                StockMaster.symbol.ilike(pattern),
                StockMaster.name.ilike(pattern),
            ),
        )
        .order_by(StockMaster.symbol)
        .limit(limit)
        .all()
    )
    return [_to_dict(r) for r in rows]


def get_stock(db: Session, symbol: str) -> dict | None:
    """종목 상세 메타데이터 조회"""
    row = db.query(StockMaster).filter(StockMaster.symbol == symbol).first()
    return _to_dict(row) if row else None


def get_stock_master_version(db: Session) -> str | None:
    """StockMaster 최신 updated_at을 버전으로 사용"""
    from sqlalchemy import func

    ts = db.query(func.max(StockMaster.updated_at)).scalar()
    return ts.isoformat() if ts else None


async def fetch_krx_listed(db: Session) -> int:
    """공공데이터포털에서 KRX 상장종목 정보를 수집하여 StockMaster에 upsert한다.

    - beginBasDt로 최근 7일 데이터만 요청 (날짜 필터 없으면 전체 이력 160만건+)
    - srtnCd 앞의 'A' 접두어를 제거하여 6자리 종목코드로 저장

    Returns:
        처리된 종목 수
    """
    api_key = os.environ.get("KRX_LISTING_API_KEY", "")
    if not api_key:
        logger.warning("KRX_LISTING_API_KEY 미설정 — 종목 마스터 수집 건너뜀")
        return 0

    # 최근 7일 이내 데이터만 요청 (주말/공휴일 대비 여유)
    begin_date = (date.today() - timedelta(days=7)).strftime("%Y%m%d")

    count = 0
    page = 1
    page_size = 1000
    seen_symbols: set[str] = set()

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            params = {
                "serviceKey": api_key,
                "resultType": "json",
                "numOfRows": page_size,
                "pageNo": page,
                "beginBasDt": begin_date,
            }
            resp = await client.get(_DATA_PORTAL_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            body = data.get("response", {}).get("body", {})
            items = body.get("items", {}).get("item", [])
            if not items:
                break

            for item in items:
                raw_code = (item.get("srtnCd") or "").strip()
                name = (item.get("itmsNm") or "").strip()
                market = (item.get("mrktCtg") or "").strip()

                if not raw_code or not name:
                    continue

                # 'A005930' → '005930' (앞의 알파벳 접두어 제거)
                symbol = raw_code.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                if not symbol:
                    continue

                # 같은 종목이 여러 날짜로 중복 반환될 수 있으므로 dedup
                if symbol in seen_symbols:
                    continue
                seen_symbols.add(symbol)

                _upsert_master(db, symbol, name, market)
                count += 1

            total = int(body.get("totalCount", 0))
            if page * page_size >= total:
                break
            page += 1

    db.commit()
    logger.info("KRX 종목 마스터 수집 완료: %d건", count)
    return count


def _upsert_master(db: Session, symbol: str, name: str, market: str) -> None:
    """StockMaster upsert (flush만, commit은 호출부에서)"""
    existing = db.query(StockMaster).filter(StockMaster.symbol == symbol).first()
    if existing:
        existing.name = name
        existing.market = market
        existing.is_active = True
    else:
        db.add(StockMaster(symbol=symbol, name=name, market=market, is_active=True))


def _to_dict(row: StockMaster) -> dict:
    return {
        "symbol": row.symbol,
        "name": row.name,
        "market": row.market,
        "sector": row.sector,
        "is_active": row.is_active,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
