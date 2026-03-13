"""계약 테스트 — local_server 응답 shape 검증.

CT-3: 상태 모델 shape
CT-4: 로컬 인증
CT-6c: 폐기 API
"""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


# ── 헬퍼 ──────────────────────────────────────────────────────────────

def assert_shape(data: dict, required: set[str], forbidden: set[str] = frozenset()):
    """필수 키 존재 + 금지 키 부재"""
    missing = required - data.keys()
    assert not missing, f"필수 키 누락: {missing}"
    present = forbidden & data.keys()
    assert not present, f"금지 키 존재: {present}"


# ── CT-3: 상태 모델 shape ─────────────────────────────────────────────


class TestStatusContract:
    """CT-3: 상태 모델 응답 shape 검증."""

    def test_ct3a_status_shape(self, client: TestClient):
        """CT-3a: GET /api/status — broker.connected(bool), broker.has_credentials(bool), strategy_engine.running(bool)."""
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()["data"]

        broker = data["broker"]
        assert_shape(broker, {"connected", "has_credentials"})
        assert isinstance(broker["connected"], bool)
        assert isinstance(broker["has_credentials"], bool)

        engine = data["strategy_engine"]
        assert_shape(engine, {"running"})
        assert isinstance(engine["running"], bool)

    def test_ct3b_health_shape(self, client: TestClient):
        """CT-3b: GET /health — status(str), version(str)."""
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert_shape(body, {"status", "version"})
        assert isinstance(body["status"], str)
        assert isinstance(body["version"], str)


# ── CT-4: 로컬 인증 ──────────────────────────────────────────────────


class TestLocalAuthContract:
    """CT-4: 로컬 인증 계약 검증."""

    def test_ct4a_token_response_shape(self, client: TestClient):
        """CT-4a: POST /api/auth/token 응답에 local_secret(str) + message(str) 포함."""
        with patch("keyring.set_password"), patch("keyring.get_password", return_value=None):
            resp = client.post("/api/auth/token", json={
                "access_token": "test_jwt",
                "refresh_token": "test_rt",
            })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert_shape(data, {"local_secret", "message"})
        assert isinstance(data["local_secret"], str)
        assert isinstance(data["message"], str)

    def test_ct4b_protected_endpoints_require_secret(self, client: TestClient):
        """CT-4b: 보호 엔드포인트 — X-Local-Secret 없이 → 401/403."""
        # 대표 3개 보호 엔드포인트
        protected = [
            ("POST", "/api/auth/logout"),
            ("GET", "/api/config"),
            ("GET", "/api/rules"),
        ]
        for method, path in protected:
            resp = getattr(client, method.lower())(path)
            assert resp.status_code in (401, 403), (
                f"{method} {path}: 예상 401/403, 실제 {resp.status_code}"
            )

    def test_ct4c_exempt_endpoints_no_secret(self, client: TestClient):
        """CT-4c: 면제 엔드포인트 — secret 없이 200."""
        exempt = [
            ("GET", "/health"),
            ("GET", "/api/status"),
            ("GET", "/api/auth/status"),
        ]
        for method, path in exempt:
            resp = getattr(client, method.lower())(path)
            assert resp.status_code == 200, (
                f"{method} {path}: 예상 200, 실제 {resp.status_code}"
            )

    def test_ct4c_token_endpoint_exempt(self, client: TestClient):
        """CT-4c: POST /api/auth/token — secret 없이 200."""
        with patch("keyring.set_password"), patch("keyring.get_password", return_value=None):
            resp = client.post("/api/auth/token", json={
                "access_token": "a",
                "refresh_token": "b",
            })
        assert resp.status_code == 200

    def test_ct4d_ws_no_secret_close_4003(self, client: TestClient):
        """CT-4d: WS /ws — sec 없이 연결 → close code 4003."""
        try:
            with client.websocket_connect("/ws"):
                pass
            assert False, "WebSocketDisconnect가 발생해야 한다"
        except WebSocketDisconnect as e:
            assert e.code == 4003

    def test_ct4e_ws_valid_secret_connects(self, client: TestClient):
        """CT-4e: WS /ws — 올바른 sec → 연결 성공 + welcome 메시지."""
        secret = client._local_secret
        with client.websocket_connect(f"/ws?sec={secret}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "system"
            assert "message" in msg["data"]


# ── CT-6c: 폐기 API ──────────────────────────────────────────────────


class TestDeprecatedApiContract:
    """CT-6c: 폐기된 API 404 검증."""

    def test_ct6c_variables_returns_404(self, client: TestClient, sh: dict):
        """CT-6c: GET /api/variables → 404."""
        resp = client.get("/api/variables", headers=sh)
        assert resp.status_code == 404
