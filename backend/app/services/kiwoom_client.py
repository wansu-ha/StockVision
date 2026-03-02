"""
키움증권 REST API 클라이언트

환경 변수(KIWOOM_APP_KEY, KIWOOM_APP_SECRET)가 없으면 graceful 비활성화.
키 설정 시 실시간 시세 조회 가능.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# 키움증권 REST API 기본 URL
KIWOOM_BASE_URL = "https://openapi.kiwoom.com:8443"
KIWOOM_MOCK_URL = "https://mockapi.kiwoom.com:8443"  # 모의투자


class KiwoomClient:
    """키움증권 REST API 비동기 클라이언트"""

    def __init__(self):
        self.app_key = os.getenv("KIWOOM_APP_KEY", "")
        self.app_secret = os.getenv("KIWOOM_APP_SECRET", "")
        self.account_no = os.getenv("KIWOOM_ACCOUNT_NO", "")
        self.use_mock = os.getenv("KIWOOM_USE_MOCK", "true").lower() == "true"

        self.base_url = KIWOOM_MOCK_URL if self.use_mock else KIWOOM_BASE_URL
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self._client = None
        self._enabled = bool(self.app_key and self.app_secret)

        if not self._enabled:
            logger.info("키움증권 API 키 미설정 — 비활성화 상태로 운영")
        else:
            logger.info(f"키움증권 API 초기화 (모의투자: {self.use_mock})")

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def _get_client(self):
        """httpx 비동기 클라이언트 반환 (lazy init)"""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=10.0,
            )
        return self._client

    async def _ensure_token(self) -> bool:
        """토큰 발급/갱신. 성공 시 True, 실패 시 False."""
        if not self._enabled:
            return False

        # 토큰이 유효하면 재사용
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return True

        try:
            client = await self._get_client()
            resp = await client.post(
                "/oauth2/token",
                json={
                    "grant_type": "client_credentials",
                    "appkey": self.app_key,
                    "secretkey": self.app_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self.access_token = data.get("token")
            # 토큰 만료 시간 (기본 24시간)
            expires_in = data.get("expires_in", 86400)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            logger.info("키움증권 토큰 발급 성공")
            return True
        except Exception as e:
            logger.error(f"키움증권 토큰 발급 실패: {e}")
            return False

    def _auth_headers(self) -> dict:
        """인증 헤더 생성"""
        return {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

    async def get_current_price(self, symbol: str) -> Optional[dict]:
        """현재가 조회

        Returns:
            {"price": float, "change": float, "change_rate": float, "volume": int} or None
        """
        if not await self._ensure_token():
            return None

        try:
            client = await self._get_client()
            resp = await client.get(
                "/uapi/domestic-stock/v1/quotations/inquire-price",
                headers={
                    **self._auth_headers(),
                    "tr_id": "FHKST01010100",
                },
                params={"fid_input_iscd": symbol, "fid_cond_mrkt_div_code": "J"},
            )
            resp.raise_for_status()
            data = resp.json()
            output = data.get("output", {})
            return {
                "price": float(output.get("stck_prpr", 0)),
                "change": float(output.get("prdy_vrss", 0)),
                "change_rate": float(output.get("prdy_ctrt", 0)),
                "volume": int(output.get("acml_vol", 0)),
            }
        except Exception as e:
            logger.error(f"현재가 조회 실패 ({symbol}): {e}")
            return None

    async def get_stock_list(self, market: str = "KOSPI") -> Optional[list]:
        """종목 목록 조회

        Args:
            market: "KOSPI" or "KOSDAQ"
        """
        if not await self._ensure_token():
            return None

        try:
            client = await self._get_client()
            market_code = "0001" if market == "KOSPI" else "1001"
            resp = await client.get(
                "/uapi/domestic-stock/v1/quotations/inquire-member",
                headers={
                    **self._auth_headers(),
                    "tr_id": "FHKST03010200",
                },
                params={"fid_input_iscd": market_code, "fid_cond_mrkt_div_code": "J"},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("output", [])
        except Exception as e:
            logger.error(f"종목 목록 조회 실패 ({market}): {e}")
            return None

    async def close(self):
        """클라이언트 종료"""
        if self._client:
            await self._client.aclose()
            self._client = None


# 싱글톤 인스턴스
_kiwoom_client: Optional[KiwoomClient] = None


def get_kiwoom_client() -> KiwoomClient:
    """키움증권 클라이언트 싱글톤 반환"""
    global _kiwoom_client
    if _kiwoom_client is None:
        _kiwoom_client = KiwoomClient()
    return _kiwoom_client
