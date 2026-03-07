"""local_server.broker.kiwoom.auth: 키움증권 OAuth 인증 모듈

키움 REST API 토큰 발급/갱신을 관리한다.
KIS와 주요 차이:
- Body: secretkey (KIS: appsecret)
- 응답: token (KIS: access_token), expires_dt 날짜 문자열 (KIS: expires_in 초)
- 모든 API 헤더: api-id 사용 (KIS: tr_id)
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# 키움 REST API 기본 URL
KIWOOM_BASE_URL_REAL = "https://api.kiwoom.com"
KIWOOM_BASE_URL_MOCK = "https://mockapi.kiwoom.com"

# 토큰 만료 여유 시간
TOKEN_REFRESH_MARGIN_SECONDS = 300  # 5분


@dataclass
class TokenInfo:
    """액세스 토큰 정보"""
    access_token: str
    token_type: str
    expires_at: datetime


class KiwoomAuth:
    """키움증권 OAuth 2.0 인증 관리자.

    App Key / Secret Key로 액세스 토큰을 발급받고,
    만료 전 자동 갱신한다.
    """

    def __init__(self, app_key: str, secret_key: str, is_mock: bool = False) -> None:
        self._app_key = app_key
        self._secret_key = secret_key
        self._is_mock = is_mock
        self._base_url = KIWOOM_BASE_URL_MOCK if is_mock else KIWOOM_BASE_URL_REAL
        self._token_info: Optional[TokenInfo] = None
        self._lock = asyncio.Lock()

    @property
    def base_url(self) -> str:
        """현재 사용 중인 기본 URL을 반환한다."""
        return self._base_url

    async def get_access_token(self) -> str:
        """유효한 액세스 토큰을 반환한다. 만료 임박 시 자동 갱신."""
        async with self._lock:
            if self._needs_refresh():
                await self._fetch_token()
        return self._token_info.access_token  # type: ignore[union-attr]

    def _needs_refresh(self) -> bool:
        if self._token_info is None:
            return True
        margin = timedelta(seconds=TOKEN_REFRESH_MARGIN_SECONDS)
        return datetime.now() >= self._token_info.expires_at - margin

    async def _fetch_token(self) -> None:
        """키움 서버에서 토큰을 발급받는다."""
        url = f"{self._base_url}/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self._app_key,
            "secretkey": self._secret_key,
        }

        logger.info("키움 액세스 토큰 발급 요청 (%s)", "모의" if self._is_mock else "실전")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json;charset=UTF-8"},
            )
            resp.raise_for_status()

        data = resp.json()
        if data.get("return_code") != 0:
            raise ConnectionError(
                f"키움 토큰 발급 실패: {data.get('return_msg', 'unknown error')}"
            )

        # expires_dt: "20241107083713" → datetime
        expires_dt_str = data.get("expires_dt", "")
        if expires_dt_str:
            expires_at = datetime.strptime(expires_dt_str, "%Y%m%d%H%M%S")
        else:
            expires_at = datetime.now() + timedelta(hours=24)

        self._token_info = TokenInfo(
            access_token=data["token"],
            token_type=data.get("token_type", "bearer"),
            expires_at=expires_at,
        )
        logger.info(
            "키움 액세스 토큰 발급 완료 (만료: %s)",
            self._token_info.expires_at.isoformat(),
        )

    def invalidate(self) -> None:
        """캐시된 토큰을 무효화한다."""
        self._token_info = None
        logger.info("캐시된 토큰 무효화")

    async def build_headers(self, api_id: str) -> dict[str, str]:
        """API 요청용 인증 헤더를 구성한다.

        Args:
            api_id: 키움 API 식별자 (예: "ka10007", "kt10000")

        Returns:
            dict: authorization, api-id 포함 헤더
        """
        token = await self.get_access_token()
        return {
            "authorization": f"Bearer {token}",
            "api-id": api_id,
            "Content-Type": "application/json;charset=UTF-8",
        }
