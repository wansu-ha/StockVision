"""디바이스 페어링 엔드포인트.

POST /api/devices/pair/init      → E2E 키 생성 + QR 데이터 반환
POST /api/devices/pair/complete  → 페어링 완료 + 클라우드 등록
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/devices", tags=["디바이스"])


class PairCompleteBody(BaseModel):
    device_id: str
    name: str | None = None
    platform: str | None = None


@router.post("/pair/init")
def pair_init():
    """E2E 키 생성 + QR 데이터 반환."""
    from local_server.cloud.e2e_crypto import E2ECrypto
    crypto = E2ECrypto()
    device_id, key_b64 = crypto.generate_key()

    # QR 데이터: JSON 형식으로 device_id + key 포함
    import json
    qr_data = json.dumps({"device_id": device_id, "key": key_b64}, ensure_ascii=False)

    return {
        "success": True,
        "data": {
            "device_id": device_id,
            "key": key_b64,
            "qr_data": qr_data,
        },
    }


@router.post("/pair/complete")
async def pair_complete(body: PairCompleteBody):
    """페어링 완료 → 클라우드에 디바이스 등록."""
    from local_server.cloud.client import CloudClient, CloudClientError
    from local_server.cloud.heartbeat import get_cloud_client

    client = get_cloud_client()
    if not client:
        raise HTTPException(status_code=503, detail="클라우드 연결이 설정되지 않았습니다.")

    try:
        resp = await client._post("/api/v1/devices/register", {
            "device_id": body.device_id,
            "name": body.name,
            "platform": body.platform,
        })
        return {"success": True, "data": resp}
    except CloudClientError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
