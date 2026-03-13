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

from local_server.core.local_auth import is_secret_issued, mark_secret_issued, require_local_secret

from local_server.storage.credential import (
    clear_all_credentials,
    get_active_user,
    has_credential,
    load_cloud_tokens,
    set_active_user,
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
    # AS-2: 이미 secret이 발급된 상태면 인증 필요 (재등록 방지)
    if is_secret_issued(request):
        await require_local_secret(request)

    try:
        # JWT payload에서 email 추출 → 활성 사용자 설정
        import base64, json as _json
        try:
            payload_b64 = body.access_token.split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)  # padding
            payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
            email = payload.get("email") or payload.get("sub")
            if email:
                set_active_user(email)
        except Exception:
            pass  # JWT 디코딩 실패 시 default 유지

        save_cloud_tokens(body.access_token, body.refresh_token)
        # heartbeat에도 새 토큰 반영
        from local_server.cloud.heartbeat import get_cloud_client
        cc = get_cloud_client()
        if cc:
            cc.set_token(body.access_token)
        mark_secret_issued(request)
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


@router.post(
    "/restore",
    summary="저장된 토큰으로 세션 복원",
)
async def restore_session(request: Request) -> dict[str, Any]:
    """keyring에 저장된 토큰을 반환하여 프론트엔드 세션을 복원한다.

    access_token이 만료(60초 leeway)됐으면 refresh 후 새 토큰을 반환한다.
    """
    # AS-2: 이미 secret이 발급된 상태면 인증 필요 (재등록 방지)
    if is_secret_issued(request):
        await require_local_secret(request)

    from local_server.cloud.token_utils import _refresh_lock, is_jwt_expired

    access_token, refresh_token = load_cloud_tokens()
    if not refresh_token:
        raise HTTPException(status_code=404, detail="저장된 토큰 없음")

    # access_token 만료 확인
    if access_token and is_jwt_expired(access_token):
        access_token = None

    if not access_token:
        async with _refresh_lock:
            # Lock 내부에서 다시 확인 — 선행 요청이 이미 refresh했을 수 있음
            access_token, refresh_token = load_cloud_tokens()
            if not refresh_token:
                raise HTTPException(status_code=404, detail="저장된 토큰 없음")
            if not access_token or is_jwt_expired(access_token):
                try:
                    from local_server.cloud.client import CloudClient
                    from local_server.config import get_config
                    cloud_url = get_config().get("cloud.url")
                    temp = CloudClient(base_url=cloud_url)
                    tokens = await temp.refresh_access_token(refresh_token)
                    access_token = tokens["access_token"]
                    refresh_token = tokens["refresh_token"]
                    save_cloud_tokens(access_token, refresh_token)
                    # heartbeat에도 반영
                    from local_server.cloud.heartbeat import get_cloud_client
                    cc = get_cloud_client()
                    if cc:
                        cc.set_token(access_token)
                except Exception:
                    raise HTTPException(status_code=401, detail="토큰 갱신 실패. 재로그인 필요.")

    mark_secret_issued(request)
    email = get_active_user()
    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "email": email if email != "default" else None,
            "local_secret": request.app.state.local_secret,
        },
    }


@router.get(
    "/status",
    summary="인증 상태 확인",
)
async def auth_status(_: None = Depends(require_local_secret)) -> dict[str, Any]:
    """클라우드 토큰 저장 여부와 이메일을 반환한다. 토큰 자체는 노출하지 않는다."""
    access_token, refresh_token = load_cloud_tokens()
    email = get_active_user()
    return {
        "success": True,
        "data": {
            "has_cloud_token": bool(access_token),
            "has_refresh_token": bool(refresh_token),
            "email": email if email != "default" else None,
        },
        "count": 1,
    }
