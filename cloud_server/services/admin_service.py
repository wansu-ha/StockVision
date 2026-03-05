"""
어드민 비즈니스 로직

시스템 통계, 유저 관리, 서비스 키 관리, 수집 상태 조회.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from cloud_server.collector.scheduler import get_collector_status
from cloud_server.core.encryption import encrypt_value
from cloud_server.models.heartbeat import Heartbeat
from cloud_server.models.market import MinuteBar
from cloud_server.models.rule import TradingRule
from cloud_server.models.template import KiwoomServiceKey, StrategyTemplate
from cloud_server.models.user import User


def get_stats(db: Session) -> dict:
    """시스템 통계"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()  # noqa: E712
    rules_count = db.query(TradingRule).count()

    # 최근 30분 내 하트비트 (활성 클라이언트)
    cutoff = datetime.utcnow() - timedelta(minutes=30)
    active_clients = db.query(Heartbeat).filter(
        Heartbeat.created_at >= cutoff
    ).count()

    return {
        "user_count": total_users,
        "active_users": active_users,
        "rules_count": rules_count,
        "active_clients": active_clients,
        "timestamp": datetime.utcnow().isoformat(),
    }


def get_collector_status_info(db: Session) -> dict:
    """데이터 수집기 상태"""
    status = get_collector_status()

    last_bar = db.query(MinuteBar).order_by(
        MinuteBar.created_at.desc()
    ).first()

    return {
        "status": status["status"],
        "last_quote_time": status.get("last_quote_time") or (
            last_bar.created_at.isoformat() if last_bar else None
        ),
        "error_count": status.get("error_count", 0),
        "last_error": status.get("last_error"),
        "total_quotes": status.get("total_quotes", db.query(MinuteBar).count()),
        "timestamp": datetime.utcnow().isoformat(),
    }


def list_users(db: Session, page: int = 1, limit: int = 20) -> dict:
    """유저 목록 조회"""
    offset = (page - 1) * limit
    users = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    total = db.query(User).count()
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "nickname": u.nickname,
                "role": u.role,
                "email_verified": u.email_verified,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "limit": limit,
    }


def set_user_active(user_id: str, is_active: bool, db: Session) -> None:
    """유저 활성/비활성 전환"""
    from fastapi import HTTPException
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다.")
    user.is_active = is_active
    db.commit()


# ── 서비스 키 관리 ────────────────────────────────────────────────────


def list_service_keys(db: Session) -> list[dict]:
    """서비스 키 목록 (secret 마스킹)"""
    keys = db.query(KiwoomServiceKey).order_by(KiwoomServiceKey.created_at.desc()).all()
    return [
        {
            "id": k.id,
            "api_key": k.api_key,
            "api_secret": "***",  # 마스킹
            "app_name": k.app_name,
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat(),
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        }
        for k in keys
    ]


def create_service_key(api_key: str, api_secret: str, app_name: str | None, db: Session) -> dict:
    """서비스 키 등록 (api_secret 암호화)"""
    encrypted_secret = encrypt_value(api_secret)
    key = KiwoomServiceKey(
        api_key=api_key,
        api_secret=encrypted_secret,
        app_name=app_name,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return {"id": key.id, "api_key": key.api_key, "app_name": key.app_name}


def delete_service_key(key_id: int, db: Session) -> None:
    """서비스 키 삭제"""
    from fastapi import HTTPException
    key = db.query(KiwoomServiceKey).filter(KiwoomServiceKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="키를 찾을 수 없습니다.")
    db.delete(key)
    db.commit()


# ── 전략 템플릿 ────────────────────────────────────────────────────────


def _template_to_dict(t: StrategyTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "buy_conditions": t.buy_conditions,
        "sell_conditions": t.sell_conditions,
        "default_params": t.default_params,
        "category": t.category,
        "is_public": t.is_public,
        "created_by": t.created_by,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def list_templates(db: Session) -> list[dict]:
    templates = db.query(StrategyTemplate).order_by(StrategyTemplate.created_at.desc()).all()
    return [_template_to_dict(t) for t in templates]


def create_template(data: dict, created_by: str, db: Session) -> dict:
    t = StrategyTemplate(
        name=data["name"],
        description=data.get("description"),
        buy_conditions=data.get("buy_conditions"),
        sell_conditions=data.get("sell_conditions"),
        default_params=data.get("default_params"),
        category=data.get("category"),
        is_public=data.get("is_public", False),
        created_by=created_by,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _template_to_dict(t)


def update_template(template_id: int, data: dict, db: Session) -> dict:
    from fastapi import HTTPException
    t = db.query(StrategyTemplate).filter(StrategyTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")
    for field, value in data.items():
        if hasattr(t, field):
            setattr(t, field, value)
    db.commit()
    db.refresh(t)
    return _template_to_dict(t)


def delete_template(template_id: int, db: Session) -> None:
    from fastapi import HTTPException
    t = db.query(StrategyTemplate).filter(StrategyTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")
    db.delete(t)
    db.commit()
