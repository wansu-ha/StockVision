"""local_server.broker.kiwoom.auth: 키움증권 OAuth 인증 모듈"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# 키움 REST API 기본 URL
KIWOOM_BASE_URL = "https://openapi.koreainvestment.com:9443"

# 토큰 만료 여유 시간 (실제 만료 N초 전에 갱신)
TOKEN_REFRESH_MARGIN_SECONDS = 300  # 5분


@dataclass
class TokenInfo:
    """액세스 토큰 정보"""
    access_token: str       # Bearer 토큰
    token_type: str         # 토큰 타입 (Bearer)
    expires_at: datetime    # 만료 시각


class KiwoomAuth:
    """키움증권 OAuth 2.0 인증 관리자.

    App Key / App Secret으로 액세스 토큰을 발급받고,
    만료 전 자동 갱신한다.
    """

    def __init__(self, app_key: str, app_secret: str) -> None:
        """초기화.

        Args:
            app_key: 키움 Open API+ App Key
            app_secret: 키움 Open API+ App Secret
        """
        self._app_key = app_key
        self._app_secret = app_secret
        self._token_info: Optional[TokenInfo] = None
        self._lock = asyncio.Lock()  # 동시 갱신 방지

    async def get_access_token(self) -> str:
        """유효한 액세스 토큰을 반환한다.

        토큰이 없거나 곧 만료될 경우 자동으로 갱신한다.

        Returns:
            str: Bearer 액세스 토큰

        Raises:
            httpx.HTTPStatusError: API 오류 시
        """
        async with self._lock:
            if self._needs_refresh():
                await self._fetch_token()
        return self._token_info.access_token  # type: ignore[union-attr]

    def _needs_refresh(self) -> bool:
        """토큰 갱신이 필요한지 확인한다."""
        if self._token_info is None:
            return True
        margin = timedelta(seconds=TOKEN_REFRESH_MARGIN_SECONDS)
        return datetime.now() >= self._token_info.expires_at - margin

    async def _fetch_token(self) -> None:
        """키움 서버에서 토큰을 새로 발급받는다."""
        url = f"{KIWOOM_BASE_URL}/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self._app_key,
            "appsecret": self._app_secret,
        }

        logger.info("키움 액세스 토큰 발급 요청")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()

        data = resp.json()
        expires_in: int = int(data.get("expires_in", 86400))  # 기본 24시간
        self._token_info = TokenInfo(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_at=datetime.now() + timedelta(seconds=expires_in),
        )
        logger.info(
            "키움 액세스 토큰 발급 완료 (만료: %s)",
            self._token_info.expires_at.isoformat(),
        )

    def invalidate(self) -> None:
        """캐시된 토큰을 무효화한다. (인증 오류 발생 시 호출)"""
        self._token_info = None
        logger.info("캐시된 토큰 무효화")

    async def build_headers(self) -> dict[str, str]:
        """일반 API 요청에 필요한 인증 헤더를 구성한다.

        시세 조회, 주문 등 토큰 발급 이후의 모든 요청에 사용한다.
        appsecret은 포함하지 않는다 — 토큰 발급 전용 헤더는 build_auth_headers()를 사용.

        Returns:
            dict: Authorization(Bearer), appkey 포함 헤더
        """
        token = await self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "appkey": self._app_key,
            "Content-Type": "application/json; charset=utf-8",
        }

    def build_auth_headers(self) -> dict[str, str]:
        """토큰 발급 요청 전용 헤더를 구성한다.

        POST /oauth2/token 요청에만 사용한다.
        appsecret이 포함되므로 다른 엔드포인트에 사용하지 말 것.

        Returns:
            dict: appkey, appsecret 포함 헤더 (Authorization 미포함)
        """
        return {
            "appkey": self._app_key,
            "appsecret": self._app_secret,
            "Content-Type": "application/json; charset=utf-8",
        }
