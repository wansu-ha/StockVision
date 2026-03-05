"""클라우드 서버 HTTP 클라이언트.

httpx를 사용하여 클라우드 서버와 아웃바운드 통신을 담당한다.
로컬 서버는 인터넷에서 인바운드 연결을 받지 않고,
클라우드 서버로의 아웃바운드 요청만 수행한다.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# 기본 타임아웃 (초)
DEFAULT_TIMEOUT = 10.0


class CloudClientError(Exception):
    """클라우드 서버 통신 실패 시 발생하는 예외."""


class CloudClient:
    """클라우드 서버 HTTP 클라이언트."""

    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
        api_token: str | None = None,
    ) -> None:
        """
        Args:
            base_url: 클라우드 서버 기본 URL (예: https://api.stockvision.com)
            timeout: 요청 타임아웃 (초)
            api_token: 클라우드 서버 인증 토큰 (있으면 Authorization 헤더 추가)
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_token:
            self._headers["Authorization"] = f"Bearer {api_token}"

    def _make_url(self, path: str) -> str:
        """베이스 URL과 경로를 합쳐 완전한 URL을 반환한다."""
        return f"{self._base_url}/{path.lstrip('/')}"

    async def _get(self, path: str) -> Any:
        """GET 요청을 수행하고 JSON 응답을 반환한다."""
        url = self._make_url(path)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(url, headers=self._headers)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as e:
                raise CloudClientError(f"요청 타임아웃 ({url}): {e}") from e
            except httpx.HTTPStatusError as e:
                raise CloudClientError(
                    f"HTTP 오류 {e.response.status_code} ({url}): {e.response.text}"
                ) from e
            except httpx.RequestError as e:
                raise CloudClientError(f"요청 실패 ({url}): {e}") from e

    async def _post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        """POST 요청을 수행하고 JSON 응답을 반환한다."""
        url = self._make_url(path)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(url, json=data or {}, headers=self._headers)
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException as e:
                raise CloudClientError(f"요청 타임아웃 ({url}): {e}") from e
            except httpx.HTTPStatusError as e:
                raise CloudClientError(
                    f"HTTP 오류 {e.response.status_code} ({url}): {e.response.text}"
                ) from e
            except httpx.RequestError as e:
                raise CloudClientError(f"요청 실패 ({url}): {e}") from e

    async def fetch_rules(self) -> list[dict[str, Any]]:
        """클라우드 서버에서 매매 규칙을 가져온다.

        Returns:
            규칙 목록 (딕셔너리 리스트)
        """
        logger.debug("클라우드에서 규칙 fetch: %s/api/rules", self._base_url)
        result = await self._get("/api/rules")

        # 응답 형식 { success, data, count } 기준으로 파싱
        if isinstance(result, dict) and "data" in result:
            data = result["data"]
            if isinstance(data, list):
                return data
        elif isinstance(result, list):
            return result

        raise CloudClientError(f"예상치 못한 규칙 응답 형식: {type(result)}")

    async def send_heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        """클라우드 서버에 하트비트를 전송한다.

        Args:
            payload: 전송할 상태 정보

        Returns:
            서버 응답
        """
        logger.debug("하트비트 전송: %s", self._base_url)
        result = await self._post("/api/local/heartbeat", payload)
        return result if isinstance(result, dict) else {"raw": result}

    async def health_check(self) -> bool:
        """클라우드 서버의 헬스체크를 수행한다.

        Returns:
            서버가 응답하면 True, 실패하면 False
        """
        try:
            result = await self._get("/health")
            return isinstance(result, dict) and result.get("status") == "ok"
        except CloudClientError:
            return False
