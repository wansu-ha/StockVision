"""디바이스 관리 API.

디바이스 목록, 등록, 해제.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import current_user
from cloud_server.core.database import get_db
from cloud_server.models.device import Device

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

MAX_DEVICES = 5


class DeviceRegisterBody(BaseModel):
    device_id: str
    name: str | None = None
    platform: str | None = None  # 'web' | 'android' | 'ios'


@router.get("")
def list_devices(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """등록된 디바이스 목록."""
    devices = (
        db.query(Device)
        .filter(Device.user_id == user["sub"], Device.is_active == True)  # noqa: E712
        .order_by(Device.registered_at.desc())
        .all()
    )
    return {
        "success": True,
        "data": [
            {
                "id": d.id,
                "name": d.name,
                "platform": d.platform,
                "registered_at": d.registered_at.isoformat() if d.registered_at else None,
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
            }
            for d in devices
        ],
        "count": len(devices),
    }


@router.post("/register")
def register_device(
    body: DeviceRegisterBody,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """디바이스 메타데이터 등록 (키는 로컬에서 관리)."""
    active_count = (
        db.query(Device)
        .filter(Device.user_id == user["sub"], Device.is_active == True)  # noqa: E712
        .count()
    )
    if active_count >= MAX_DEVICES:
        raise HTTPException(status_code=400, detail=f"최대 {MAX_DEVICES}대까지 등록 가능합니다.")

    # 중복 체크
    existing = db.query(Device).filter(Device.id == body.device_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="이미 등록된 디바이스입니다.")

    device = Device(
        id=body.device_id,
        user_id=user["sub"],
        name=body.name,
        platform=body.platform,
    )
    db.add(device)
    db.commit()

    return {"success": True, "data": {"device_id": device.id}}


@router.delete("/{device_id}")
def deactivate_device(
    device_id: str,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """디바이스 해제 (is_active=False)."""
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.user_id == user["sub"],
    ).first()

    if not device:
        raise HTTPException(status_code=404, detail="디바이스를 찾을 수 없습니다.")

    device.is_active = False
    db.commit()

    return {"success": True, "message": "디바이스가 해제되었습니다."}
