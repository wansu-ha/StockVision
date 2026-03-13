"""설정 라우터.

GET  /api/config          — 현재 설정 조회 (민감 정보 마스킹)
PATCH /api/config         — 설정 변경 후 저장
POST /api/config/broker-keys — 증권사 API Key 등록 + 모의/실전 자동 감지
"""
from __future__ import annotations

import logging
from typing import Any, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from local_server.core.local_auth import require_local_secret
from pydantic import BaseModel, Field

from local_server.storage.config_store import read_config, update_config
from local_server.storage.credential import (
    save_credential,
    KEY_APP_KEY,
    KEY_APP_SECRET,
    KEY_KIWOOM_APP_KEY,
    KEY_KIWOOM_SECRET_KEY,
    save_account_no,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ConfigUpdateRequest(BaseModel):
    """설정 업데이트 요청 바디 (부분 업데이트 지원)."""

    updates: dict[str, Any]


class BrokerKeysRequest(BaseModel):
    """증권사 API Key 등록 요청 바디."""

    broker_type: Literal["kiwoom", "kis"] = Field(..., description="증권사 타입")
    app_key: str = Field(..., description="앱 키")
    app_secret: str = Field(..., description="앱 시크릿")
    account_no: str | None = Field(None, description="KIS 계좌번호 (KIS 전용)")


async def _detect_mock_kiwoom(app_key: str, secret_key: str) -> bool:
    """키움 키로 모의/실전 자동 감지. 모의 먼저 시도."""
    for is_mock, base in [(True, "https://mockapi.kiwoom.com"), (False, "https://api.kiwoom.com")]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.post(f"{base}/oauth2/token", json={
                    "grant_type": "client_credentials", "appkey": app_key, "secretkey": secret_key,
                })
                if r.status_code == 200 and r.json().get("return_code") == 0:
                    return is_mock
        except Exception:
            continue
    raise ValueError("모의/실전 서버 모두 인증 실패. 키를 확인하세요.")


@router.get(
    "",
    summary="현재 설정 조회",
)
async def get_configuration(_: None = Depends(require_local_secret)) -> dict[str, Any]:
    """현재 서버 설정을 반환한다. 민감 정보(API Key 등)는 마스킹된다."""
    config_data = read_config()
    return {"success": True, "data": config_data, "count": 1}


@router.patch(
    "",
    summary="설정 변경",
)
async def patch_configuration(body: ConfigUpdateRequest, _: None = Depends(require_local_secret)) -> dict[str, Any]:
    """설정을 부분 업데이트하고 저장한다."""
    updated = update_config(body.updates)
    logger.info("설정 변경: %s", list(body.updates.keys()))
    return {"success": True, "data": updated, "count": 1}


@router.post(
    "/broker-keys",
    summary="증권사 API Key 등록 + 모의/실전 감지",
)
async def register_broker_keys(body: BrokerKeysRequest, _: None = Depends(require_local_secret)) -> dict[str, Any]:
    """API Key를 keyring에 저장하고, 모의/실전을 자동 감지하여 config에 반영한다."""
    try:
        is_mock: bool

        if body.broker_type == "kiwoom":
            is_mock = await _detect_mock_kiwoom(body.app_key, body.app_secret)
            save_credential(KEY_KIWOOM_APP_KEY, body.app_key)
            save_credential(KEY_KIWOOM_SECRET_KEY, body.app_secret)
        else:
            # KIS — TODO: 감지 로직 추가 시
            save_credential(KEY_APP_KEY, body.app_key)
            save_credential(KEY_APP_SECRET, body.app_secret)
            if body.account_no:
                save_account_no(body.account_no)
            is_mock = True  # KIS 감지 미구현 → 기본 모의

        update_config({"broker": {"type": body.broker_type, "is_mock": is_mock}})
        label = "모의투자" if is_mock else "실전투자"
        logger.info("%s API Key 등록 완료 (%s)", body.broker_type, label)

        return {
            "success": True,
            "data": {
                "message": f"API Key가 등록되었습니다. ({label})",
                "broker_type": body.broker_type,
                "is_mock": is_mock,
            },
            "count": 1,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.error("API Key 등록 실패: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API Key 저장 실패: {e}",
        ) from e
