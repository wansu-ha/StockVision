"""
하트비트 비즈니스 로직

로컬 서버의 상태 보고를 받고 버전 정보(rules, context, watchlist, stock_master) 반환.
"""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud_server.core.config import settings
from cloud_server.models.heartbeat import Heartbeat
from cloud_server.models.rule import TradingRule
from cloud_server.services.stock_service import get_stock_master_version
from cloud_server.services.watchlist_service import get_watchlist_version


def record_heartbeat(user_id: str, payload: dict, db: Session) -> dict:
    """
    하트비트 저장 후 버전 정보 반환.

    payload 형식:
    {
      "uuid": str,
      "version": str,
      "os": str,
      "broker_connected": bool,
      "engine_running": bool,
      "active_rules_count": int,
      "timestamp": datetime
    }
    """
    hb = Heartbeat(
        uuid=payload["uuid"],
        user_id=user_id,
        version=payload.get("version"),
        os=payload.get("os"),
        broker_connected=payload.get("broker_connected"),
        engine_running=payload.get("engine_running"),
        active_rules_count=payload.get("active_rules_count"),
        timestamp=payload["timestamp"],
    )
    db.add(hb)
    db.commit()

    # 사용자 규칙 최신 version 계산
    rules_version = db.query(func.max(TradingRule.version)).filter(
        TradingRule.user_id == user_id
    ).scalar() or 0

    # context_version: 현재는 고정값 (v2에서 확장)
    context_version = 1

    return {
        "rules_version": rules_version,
        "context_version": context_version,
        "watchlist_version": get_watchlist_version(db, user_id),
        "stock_master_version": get_stock_master_version(db),
        "latest_version": settings.LOCAL_SERVER_LATEST_VERSION,
        "min_version": settings.LOCAL_SERVER_MIN_SUPPORTED,
        "download_url": settings.LOCAL_SERVER_DOWNLOAD_URL,
        "timestamp": datetime.utcnow().isoformat(),
    }
