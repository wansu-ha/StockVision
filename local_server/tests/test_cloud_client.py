"""클라우드 클라이언트 테스트.

httpx의 MockTransport를 사용하여 실제 네트워크 없이 테스트한다.
"""
from __future__ import annotations

import json
import pytest
import httpx

from local_server.cloud.client import CloudClient, CloudClientError


def _make_response(data: object, status_code: int = 200) -> httpx.Response:
    """테스트용 httpx.Response를 생성한다."""
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )


class MockTransport(httpx.AsyncBaseTransport):
    """단일 응답을 반환하는 mock 전송 레이어."""

    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return self._response


class TestCloudClientFetchRules:
    @pytest.mark.asyncio
    async def test_fetch_rules_with_data_wrapper(self) -> None:
        """{ data: [...] } 형식의 응답에서 규칙을 파싱한다."""
        rules = [{"id": 1, "name": "RSI매수"}]
        transport = MockTransport(_make_response({"success": True, "data": rules, "count": 1}))

        client = CloudClient(base_url="http://test-server")

        async with httpx.AsyncClient(transport=transport) as http_client:
            # _get을 직접 대체하는 방식으로 테스트
            original_get = client._get

            async def mock_get(path: str):
                return {"success": True, "data": rules, "count": 1}

            client._get = mock_get  # type: ignore[method-assign]
            result = await client.fetch_rules()
            assert result == rules
            client._get = original_get

    @pytest.mark.asyncio
    async def test_fetch_rules_with_plain_list(self) -> None:
        """[ ... ] 형식 응답도 파싱한다."""
        rules = [{"id": 2}]
        client = CloudClient(base_url="http://test-server")

        async def mock_get(path: str):
            return rules

        client._get = mock_get  # type: ignore[method-assign]
        result = await client.fetch_rules()
        assert result == rules

    @pytest.mark.asyncio
    async def test_fetch_rules_unexpected_format_raises(self) -> None:
        """예상치 못한 응답 형식이면 CloudClientError를 발생시킨다."""
        client = CloudClient(base_url="http://test-server")

        async def mock_get(path: str):
            return "unexpected string"

        client._get = mock_get  # type: ignore[method-assign]
        with pytest.raises(CloudClientError):
            await client.fetch_rules()


class TestCloudClientHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_ok(self) -> None:
        """서버가 { status: ok }를 반환하면 True."""
        client = CloudClient(base_url="http://test-server")

        async def mock_get(path: str):
            return {"status": "ok"}

        client._get = mock_get  # type: ignore[method-assign]
        result = await client.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_fails_on_error(self) -> None:
        """요청 실패 시 False를 반환한다."""
        client = CloudClient(base_url="http://test-server")

        async def mock_get(path: str):
            raise CloudClientError("연결 실패")

        client._get = mock_get  # type: ignore[method-assign]
        result = await client.health_check()
        assert result is False


class TestCloudClientSendHeartbeat:
    @pytest.mark.asyncio
    async def test_send_heartbeat(self) -> None:
        """하트비트 전송 후 서버 응답을 딕셔너리로 반환한다."""
        client = CloudClient(base_url="http://test-server")

        async def mock_post(path: str, data=None):
            return {"received": True}

        client._post = mock_post  # type: ignore[method-assign]
        result = await client.send_heartbeat({"status": "online"})
        assert result == {"received": True}


class TestCloudClientURLConstruction:
    def test_base_url_trailing_slash_stripped(self) -> None:
        """base_url의 끝 슬래시가 제거된다."""
        client = CloudClient(base_url="http://test-server/")
        assert client._base_url == "http://test-server"

    def test_make_url_concatenation(self) -> None:
        """_make_url이 경로를 올바르게 연결한다."""
        client = CloudClient(base_url="http://test-server")
        assert client._make_url("/api/rules") == "http://test-server/api/rules"
        assert client._make_url("api/rules") == "http://test-server/api/rules"

    def test_authorization_header_set(self) -> None:
        """api_token이 있으면 Authorization 헤더가 설정된다."""
        client = CloudClient(base_url="http://test-server", api_token="mytoken")
        assert client._headers.get("Authorization") == "Bearer mytoken"

    def test_no_authorization_header_when_no_token(self) -> None:
        """api_token이 없으면 Authorization 헤더가 없다."""
        client = CloudClient(base_url="http://test-server")
        assert "Authorization" not in client._headers
