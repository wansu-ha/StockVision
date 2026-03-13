"""
관심종목 비즈니스 로직

- 목록 조회, 등록, 해제
- watchlist_version 계산
"""
import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud_server.models.market import Watchlist

logger = logging.getLogger(__name__)


def get_watchlist(db: Session, user_id: str) -> list[dict]:
    """사용자의 관심종목 목록 반환"""
    rows = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id)
        .order_by(Watchlist.added_at.desc())
        .all()
    )
    return [_to_dict(r) for r in rows]


def add_to_watchlist(db: Session, user_id: str, symbol: str) -> dict:
    """관심종목 등록. 이미 있으면 기존 항목 반환."""
    existing = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id, Watchlist.symbol == symbol)
        .first()
    )
    if existing:
        return _to_dict(existing)

    item = Watchlist(user_id=user_id, symbol=symbol)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_dict(item)


def remove_from_watchlist(db: Session, user_id: str, symbol: str) -> bool:
    """관심종목 해제. 삭제 성공하면 True."""
    deleted = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id, Watchlist.symbol == symbol)
        .delete()
    )
    db.commit()
    return deleted > 0


def get_watchlist_version(db: Session, user_id: str) -> int:
    """사용자의 관심종목 수를 버전으로 사용 (변경 감지용)"""
    return db.query(func.count(Watchlist.id)).filter(
        Watchlist.user_id == user_id
    ).scalar() or 0


def _to_dict(row: Watchlist) -> dict:
    return {
        "id": row.id,
        "symbol": row.symbol,
        "added_at": row.added_at.isoformat() if row.added_at else None,
    }
