"""인증 라우터.

POST /api/auth/token  — 클라우드 로그인 후 JWT를 로컬 서버에 전달
POST /api/auth/logout — 저장된 자격증명 전체 삭제
GET  /api/auth/status — 인증 상태 확인
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from local_server.core.local_auth import require_local_secret

from local_server.storage.credential import (
    clear_all_credentials,
    has_credential,
    KEY_CLOUD_ACCESS_TOKEN,
    save_cloud_tokens,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class CloudTokenRequest(BaseModel):
    """클라우드 JWT 전달 요청 바디.

    프론트엔드가 클라우드 서버에서 로그인한 뒤
    발급받은 토큰 쌍을 로컬 서버에 전달한다.
    """

    access_token: str = Field(..., description="클라우드 액세스 JWT")
    refresh_token: str = Field(..., description="클라우드 리프레시 JWT")


@router.post(
    "/token",
    summary="클라우드 JWT를 로컬 서버에 등록",
)
async def register_cloud_token(body: CloudTokenRequest, request: Request) -> dict[str, Any]:
    """클라우드 JWT 토큰 쌍을 받아 keyring에 저장한다.

    이후 클라우드 API 서버 통신 시 이 토큰을 Authorization 헤더에 사용한다.
    응답에 local_secret을 포함하여 프론트엔드가 이후 요청에 사용할 수 있게 한다.
    """
    try:
        save_cloud_tokens(body.access_token, body.refresh_token)
        logger.info("클라우드 토큰 등록 완료")
        return {
            "success": True,
            "data": {
                "message": "클라우드 토큰이 등록되었습니다.",
                "local_secret": request.app.state.local_secret,
            },
            "count": 1,
        }
    except Exception as e:
        logger.error("클라우드 토큰 저장 실패: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"토큰 저장 실패: {e}",
        ) from e


@router.post(
    "/logout",
    summary="저장된 자격증명 삭제 (로그아웃)",
)
async def logout(_: None = Depends(require_local_secret)) -> dict[str, Any]:
    """keyring에 저장된 모든 자격증명을 삭제한다."""
    clear_all_credentials()
    logger.info("로그아웃: 자격증명 전체 삭제")
    return {"success": True, "data": {"message": "로그아웃 완료"}, "count": 0}


@router.get(
    "/status",
    summary="인증 상태 확인",
)
async def auth_status() -> dict[str, Any]:
    """클라우드 토큰 및 키움 API Key 저장 여부를 반환한다."""
    has_cloud_token = has_credential(KEY_CLOUD_ACCESS_TOKEN)

    return {
        "success": True,
        "data": {
            "has_cloud_token": has_cloud_token,
        },
        "count": 1,
    }
