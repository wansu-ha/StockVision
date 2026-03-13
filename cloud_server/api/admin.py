"""
어드민 API (role=admin 필수)

# 유저 관리
GET    /api/v1/admin/users           유저 목록
PATCH  /api/v1/admin/users/{id}      유저 상태 변경

# 통계
GET    /api/v1/admin/stats           시스템 통계

# 서비스 키 관리
GET    /api/v1/admin/service-keys    키 목록 (secret 마스킹)
POST   /api/v1/admin/service-keys    키 등록
DELETE /api/v1/admin/service-keys/{id} 키 삭제

# 전략 템플릿
GET    /api/v1/admin/templates       템플릿 목록
POST   /api/v1/admin/templates       템플릿 생성
PUT    /api/v1/admin/templates/{id}  템플릿 수정
DELETE /api/v1/admin/templates/{id}  템플릿 삭제

# 수집 상태
GET    /api/v1/admin/collector-status 수집 상태
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import require_admin
from cloud_server.core.database import get_db
from cloud_server.services import admin_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── 통계 ──────────────────────────────────────────────────────────────


@router.get("/stats")
def get_stats(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    """시스템 통계 (유저 수, 규칙 수, 활성 클라이언트)"""
    data = admin_service.get_stats(db)
    return {"success": True, "data": data}


# ── 유저 관리 ─────────────────────────────────────────────────────────


@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """유저 목록"""
    data = admin_service.list_users(db, page, limit)
    return {"success": True, **data}


class UserPatchBody(BaseModel):
    is_active: bool


@router.patch("/users/{user_id}")
def patch_user(
    user_id: str,
    body: UserPatchBody,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """유저 활성/비활성 전환"""
    admin_service.set_user_active(user_id, body.is_active, db)
    return {"success": True}


# ── 서비스 키 관리 ────────────────────────────────────────────────────


@router.get("/service-keys")
def list_service_keys(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    """서비스 키 목록 (api_secret 마스킹)"""
    data = admin_service.list_service_keys(db)
    return {"success": True, "data": data, "count": len(data)}


class ServiceKeyBody(BaseModel):
    api_key: str
    api_secret: str
    app_name: str | None = None


@router.post("/service-keys", status_code=201)
def create_service_key(
    body: ServiceKeyBody,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """서비스 키 등록 (api_secret 암호화 저장)"""
    data = admin_service.create_service_key(body.api_key, body.api_secret, body.app_name, db)
    return {"success": True, "data": data}


@router.delete("/service-keys/{key_id}")
def delete_service_key(
    key_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """서비스 키 삭제"""
    admin_service.delete_service_key(key_id, db)
    return {"success": True}


# ── 전략 템플릿 ────────────────────────────────────────────────────────


@router.get("/templates")
def list_templates(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    """전략 템플릿 목록"""
    data = admin_service.list_templates(db)
    return {"success": True, "data": data, "count": len(data)}


class TemplateBody(BaseModel):
    name: str
    description: str | None = None
    buy_conditions: dict | None = None
    sell_conditions: dict | None = None
    default_params: dict | None = None
    category: str | None = None
    is_public: bool = False


@router.post("/templates", status_code=201)
def create_template(
    body: TemplateBody,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """전략 템플릿 생성"""
    data = admin_service.create_template(body.model_dump(), admin["sub"], db)
    return {"success": True, "data": data}


@router.put("/templates/{template_id}")
def update_template(
    template_id: int,
    body: TemplateBody,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """전략 템플릿 수정"""
    data = admin_service.update_template(template_id, body.model_dump(exclude_unset=True), db)
    return {"success": True, "data": data}


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """전략 템플릿 삭제"""
    admin_service.delete_template(template_id, db)
    return {"success": True}


# ── 수집 상태 ─────────────────────────────────────────────────────────


@router.get("/collector-status")
def get_collector_status(_admin=Depends(require_admin), db: Session = Depends(get_db)):
    """데이터 수집기 상태 조회"""
    data = admin_service.get_collector_status_info(db)
    return {"success": True, "data": data}


# ── 어드민 전용 시세 조회 API ─────────────────────────────────────────


@router.get("/quotes/{symbol}/daily")
def get_daily_quotes(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    일봉 데이터 조회 (어드민 전용, 제5조③ 시세 중계 금지 준수).
    수집된 시세는 내부 분석용 — 일반 유저 접근 불가.
    """
    from datetime import date
    from cloud_server.models.market import DailyBar

    query = db.query(DailyBar).filter(DailyBar.symbol == symbol)
    if start:
        query = query.filter(DailyBar.date >= date.fromisoformat(start))
    if end:
        query = query.filter(DailyBar.date <= date.fromisoformat(end))

    bars = query.order_by(DailyBar.date).all()
    return {
        "success": True,
        "data": [
            {
                "date": b.date.isoformat(),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "change_pct": b.change_pct,
            }
            for b in bars
        ],
        "count": len(bars),
    }


@router.get("/quotes/{symbol}/latest")
def get_latest_quote(
    symbol: str,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """최신 시세 조회 (어드민 전용)"""
    from cloud_server.models.market import MinuteBar

    bar = db.query(MinuteBar).filter(
        MinuteBar.symbol == symbol
    ).order_by(MinuteBar.timestamp.desc()).first()

    if not bar:
        return {"success": True, "data": None}

    return {
        "success": True,
        "data": {
            "symbol": symbol,
            "price": bar.close,
            "timestamp": bar.timestamp.isoformat(),
        },
    }
