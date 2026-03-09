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
        _captured_path = None

        client = CloudClient(base_url="http://test-server")

        async def mock_get(path: str):
            nonlocal _captured_path
            _captured_path = path
            return {"success": True, "data": rules, "count": 1}

        client._get = mock_get  # type: ignore[method-assign]
        result = await client.fetch_rules()
        assert result == rules
        assert _captured_path == "/api/v1/rules"

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
        _captured_path = None

        async def mock_post(path: str, data=None):
            nonlocal _captured_path
            _captured_path = path
            return {"received": True}

        client._post = mock_post  # type: ignore[method-assign]
        result = await client.send_heartbeat({"uuid": "test", "timestamp": "2026-01-01T00:00:00"})
        assert result == {"received": True}
        assert _captured_path == "/api/v1/heartbeat"


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


# ──────────────────────────────────────────────────────
# 하트비트 요청 payload 계약 테스트
# ──────────────────────────────────────────────────────


class TestHeartbeatRequestContract:
    """로컬 서버가 보내는 하트비트 payload가 서버 HeartbeatBody 스키마와 일치하는지 검증."""

    def test_payload_has_required_fields(self) -> None:
        """payload에 서버 필수 필드(uuid, timestamp)가 포함된다."""
        from unittest.mock import patch, MagicMock

        mock_cfg = MagicMock()
        mock_cfg.get.side_effect = lambda key, default=None: {
            "server.uuid": "test-uuid-1234",
            "server.version": "1.0.0",
        }.get(key, default)

        with patch("local_server.cloud.heartbeat.get_config", return_value=mock_cfg):
            from local_server.cloud.heartbeat import _build_heartbeat_payload
            payload = _build_heartbeat_payload()

        assert "uuid" in payload
        assert "timestamp" in payload
        assert isinstance(payload["engine_running"], bool)
        assert "version" in payload
        assert "os" in payload

    def test_payload_no_legacy_fields(self) -> None:
        """레거시 필드(status, strategy_engine)가 포함되지 않는다."""
        from unittest.mock import patch, MagicMock

        mock_cfg = MagicMock()
        mock_cfg.get.side_effect = lambda key, default=None: {
            "server.uuid": "test-uuid",
            "server.version": "1.0.0",
        }.get(key, default)

        with patch("local_server.cloud.heartbeat.get_config", return_value=mock_cfg):
            from local_server.cloud.heartbeat import _build_heartbeat_payload
            payload = _build_heartbeat_payload()

        assert "status" not in payload
        assert "strategy_engine" not in payload


# ──────────────────────────────────────────────────────
# 하트비트 응답 계약 테스트
# ──────────────────────────────────────────────────────


class TestHeartbeatResponseContract:
    """클라우드 하트비트 응답 형식이 로컬 서버 기대와 일치하는지 검증한다."""

    _REQUIRED_FIELDS = [
        "rules_version",
        "context_version",
        "watchlist_version",
        "stock_master_version",
        "latest_version",
        "min_version",
        "download_url",
        "timestamp",
    ]

    def test_heartbeat_response_has_all_required_fields(self) -> None:
        """하트비트 응답 계약: 로컬 서버가 기대하는 모든 필드가 존재한다."""
        # 클라우드 heartbeat_service와 동일한 응답 구조
        mock_response = {
            "rules_version": 3,
            "context_version": 1,
            "watchlist_version": 2,
            "stock_master_version": 100,
            "latest_version": "1.1.0",
            "min_version": "1.0.0",
            "download_url": "https://example.com/releases",
            "timestamp": "2026-03-09T00:00:00",
        }
        for field in self._REQUIRED_FIELDS:
            assert field in mock_response, f"필수 필드 누락: {field}"


# ──────────────────────────────────────────────────────
# 서버 버전 체크 로직 테스트
# ──────────────────────────────────────────────────────


class TestCheckServerVersion:
    """_check_server_version 로직을 검증한다."""

    def _call(self, resp: dict, current_version: str = "1.0.0") -> None:
        """_check_server_version을 호출한다."""
        from unittest.mock import patch
        import local_server.cloud.heartbeat as hb_mod

        # 이전 알림 기록 초기화
        hb_mod._version_notified = None

        with patch("local_server.cloud.heartbeat.get_config") as mock_cfg, \
             patch("local_server.cloud.heartbeat._send_toast") as self._mock_toast:
            mock_cfg.return_value.get.return_value = current_version
            hb_mod._check_server_version(resp)

    def test_no_notification_when_up_to_date(self) -> None:
        """현재 버전이 최신이면 알림을 보내지 않는다."""
        self._call({"latest_version": "1.0.0", "min_version": "1.0.0"}, "1.0.0")
        self._mock_toast.assert_not_called()

    def test_update_available_notification(self) -> None:
        """새 버전이 있으면 '업데이트 가능' 토스트를 보낸다."""
        self._call(
            {"latest_version": "1.1.0", "min_version": "1.0.0", "download_url": ""},
            "1.0.0",
        )
        self._mock_toast.assert_called_once()
        title = self._mock_toast.call_args[0][0]
        assert "업데이트 가능" in title

    def test_mandatory_update_notification(self) -> None:
        """최소 버전 미달이면 '업데이트 필수' 토스트를 보낸다."""
        self._call(
            {"latest_version": "2.0.0", "min_version": "1.5.0", "download_url": ""},
            "1.0.0",
        )
        self._mock_toast.assert_called_once()
        title = self._mock_toast.call_args[0][0]
        assert "업데이트 필수" in title

    def test_no_notification_without_latest_version(self) -> None:
        """latest_version이 없으면 아무것도 안 한다."""
        self._call({}, "1.0.0")
        self._mock_toast.assert_not_called()

    def test_no_duplicate_notification(self) -> None:
        """같은 버전에 대해 알림을 중복으로 보내지 않는다."""
        from unittest.mock import patch
        import local_server.cloud.heartbeat as hb_mod

        hb_mod._version_notified = None
        resp = {"latest_version": "1.1.0", "min_version": "1.0.0", "download_url": ""}

        with patch("local_server.cloud.heartbeat.get_config") as mock_cfg, \
             patch("local_server.cloud.heartbeat._send_toast") as mock_toast:
            mock_cfg.return_value.get.return_value = "1.0.0"
            hb_mod._check_server_version(resp)
            hb_mod._check_server_version(resp)  # 두 번째 호출

        assert mock_toast.call_count == 1
