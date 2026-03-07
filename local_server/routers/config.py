"""설정 라우터.

GET  /api/config          — 현재 설정 조회 (민감 정보 마스킹)
PATCH /api/config         — 설정 변경 후 저장
POST /api/config/broker-keys — 증권사 API Key + 계좌번호를 keyring에 저장
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from local_server.storage.config_store import read_config, update_config
from local_server.storage.credential import (
    has_credential,
    KEY_APP_KEY,
    save_api_keys,
    save_account_no,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ConfigUpdateRequest(BaseModel):
    """설정 업데이트 요청 바디 (부분 업데이트 지원)."""

    updates: dict[str, Any]


class KisConfigRequest(BaseModel):
    """KIS API Key 등록 요청 바디."""

    app_key: str = Field(..., description="KIS 앱 키")
    app_secret: str = Field(..., description="KIS 앱 시크릿")
    account_no: str = Field(..., description="KIS 계좌번호 (예: 12345678901)")


@router.get(
    "",
    summary="현재 설정 조회",
)
async def get_configuration() -> dict[str, Any]:
    """현재 서버 설정을 반환한다. 민감 정보(API Key 등)는 마스킹된다."""
    config_data = read_config()
    return {"success": True, "data": config_data, "count": 1}


@router.patch(
    "",
    summary="설정 변경",
)
async def patch_configuration(body: ConfigUpdateRequest) -> dict[str, Any]:
    """설정을 부분 업데이트하고 저장한다.

    중첩 딕셔너리를 그대로 전달하면 해당 키만 업데이트된다.
    예: { "updates": { "cloud": { "url": "https://..." } } }
    """
    updated = update_config(body.updates)
    logger.info("설정 변경: %s", list(body.updates.keys()))
    return {"success": True, "data": updated, "count": 1}


@router.post(
    "/broker-keys",
    summary="증권사 API Key 및 계좌번호 등록",
)
async def register_broker_keys(body: KisConfigRequest) -> dict[str, Any]:
    """KIS 앱 키, 앱 시크릿, 계좌번호를 keyring에 저장한다.

    이 정보는 BrokerAdapter.connect() 호출 및 주문 발행에 사용된다.
    저장 성공 여부만 반환하며, 실제 KIS 인증(토큰 발급)은 별도로 수행된다.
    """
    try:
        save_api_keys(body.app_key, body.app_secret)
        save_account_no(body.account_no)
        logger.info("KIS API Key 및 계좌번호 등록 완료")
        return {
            "success": True,
            "data": {
                "message": "KIS API Key가 등록되었습니다.",
                "has_key": has_credential(KEY_APP_KEY),
            },
            "count": 1,
        }
    except Exception as e:
        logger.error("KIS API Key 저장 실패: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API Key 저장 실패: {e}",
        ) from e
