import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.core.database import get_db
from app.core.encryption import encrypt_blob, decrypt_blob
from app.models.auth import ConfigBlob

router = APIRouter(prefix="/api/v1", tags=["config"])


@router.get("/config")
def get_config(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """사용자 설정 조회 (서버사이드 복호화)"""
    cb = db.query(ConfigBlob).filter(ConfigBlob.user_id == user["sub"]).first()

    if not cb or not cb.blob:
        return {"success": True, "data": {}, "count": 0}

    try:
        data = json.loads(decrypt_blob(cb.blob).decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="설정 복호화에 실패했습니다.")

    return {"success": True, "data": data, "count": 1}


@router.put("/config")
def put_config(body: dict, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """사용자 설정 저장 (서버사이드 암호화)"""
    encrypted = encrypt_blob(json.dumps(body).encode("utf-8"))

    cb = db.query(ConfigBlob).filter(ConfigBlob.user_id == user["sub"]).first()
    if cb:
        cb.blob = encrypted
    else:
        db.add(ConfigBlob(user_id=user["sub"], blob=encrypted))

    db.commit()
    return {"success": True}
