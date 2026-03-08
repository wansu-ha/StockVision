"""REST 라우터 및 WebSocket 테스트.

FastAPI TestClient를 사용하여 엔드포인트를 테스트한다.
keyring은 mock으로 대체한다.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """임시 설정 파일을 사용하는 Config 픽스처."""
    config_file = tmp_path / "config.json"
    monkeypatch.setenv("SV_CONFIG_PATH", str(config_file))

    # 전역 싱글턴 리셋
    import local_server.config as cfg_module
    cfg_module._config_instance = None

    import local_server.storage.rules_cache as rc_module
    rc_module._rules_cache_instance = None

    import local_server.storage.log_db as ld_module
    ld_module._log_db_instance = None

    yield tmp_path

    # 테스트 후 싱글턴 리셋
    cfg_module._config_instance = None
    rc_module._rules_cache_instance = None
    ld_module._log_db_instance = None


@pytest.fixture
def client(tmp_config: Path):
    """TestClient 픽스처. keyring은 mock으로 대체."""
    with patch("keyring.get_password", return_value=None), \
         patch("keyring.set_password"), \
         patch("keyring.delete_password"):

        # log_db, rules_cache가 tmp 경로 사용하도록 패치
        from local_server.storage.log_db import LogDB
        import local_server.storage.log_db as ld_module
        ld_module._log_db_instance = LogDB(db_path=tmp_config / "logs.db")

        from local_server.storage.rules_cache import RulesCache
        import local_server.storage.rules_cache as rc_module
        rc_module._rules_cache_instance = RulesCache(rules_path=tmp_config / "rules.json")

        from local_server.main import create_app
        app = create_app()

        with TestClient(app, raise_server_exceptions=True) as c:
            # shared secret 헤더를 client에 부착
            c._local_secret = app.state.local_secret
            yield c


@pytest.fixture
def sh(client: TestClient) -> dict[str, str]:
    """보호 엔드포인트용 X-Local-Secret 헤더."""
    return {"X-Local-Secret": client._local_secret}


# ──────────────────────────────────────────────────────
# 헬스체크
# ──────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ──────────────────────────────────────────────────────
# 상태 라우터
# ──────────────────────────────────────────────────────

class TestStatusRouter:
    def test_get_status(self, client: TestClient) -> None:
        resp = client.get("/api/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "server" in body["data"]
        assert "broker" in body["data"]
        assert "strategy_engine" in body["data"]


# ──────────────────────────────────────────────────────
# 인증 라우터
# ──────────────────────────────────────────────────────

class TestAuthRouter:
    def test_issue_token(self, client: TestClient) -> None:
        with patch("keyring.set_password"), patch("keyring.get_password", return_value=None):
            resp = client.post(
                "/api/auth/token",
                json={"access_token": "test_access_jwt", "refresh_token": "test_refresh_jwt"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

    def test_auth_status(self, client: TestClient) -> None:
        resp = client.get("/api/auth/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "has_cloud_token" in body["data"]

    def test_logout(self, client: TestClient, sh: dict) -> None:
        with patch("keyring.delete_password"):
            resp = client.post("/api/auth/logout", headers=sh)
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ──────────────────────────────────────────────────────
# 설정 라우터
# ──────────────────────────────────────────────────────

class TestConfigRouter:
    def test_get_config(self, client: TestClient, sh: dict) -> None:
        resp = client.get("/api/config", headers=sh)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "server" in body["data"]

    def test_patch_config(self, client: TestClient, sh: dict) -> None:
        resp = client.patch(
            "/api/config",
            json={"updates": {"log_level": "DEBUG"}},
            headers=sh,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["log_level"] == "DEBUG"

    def test_config_returns_kis_section(self, client: TestClient, sh: dict) -> None:
        """설정 조회 시 kis 섹션이 포함된다."""
        resp = client.get("/api/config", headers=sh)
        body = resp.json()
        assert body["success"] is True
        # kis 섹션 존재 확인 (account_no 등)
        assert "kis" in body["data"]


# ──────────────────────────────────────────────────────
# 매매 라우터
# ──────────────────────────────────────────────────────

class TestTradingRouter:
    def test_start_strategy_without_credentials_returns_400(
        self, client: TestClient, sh: dict
    ) -> None:
        """자격증명 없이 전략 시작 시 400을 반환한다."""
        with patch("keyring.get_password", return_value=None):
            resp = client.post("/api/strategy/start", headers=sh)
        assert resp.status_code == 400

    def test_start_strategy_creates_engine(self, client: TestClient, sh: dict) -> None:
        """자격증명 있으면 전략 시작이 브로커 연결을 시도한다."""
        # mock broker connect 실패 → 400 (브로커 연결 실패)
        with patch("keyring.get_password", return_value="exists"), \
             patch("local_server.routers.trading.create_broker_from_config",
                   side_effect=ValueError("모의: 브로커 미설정")):
            resp = client.post("/api/strategy/start", headers=sh)
        assert resp.status_code == 400
        assert "브로커 연결 실패" in resp.json()["detail"]

    def test_place_market_order_without_engine(self, client: TestClient, sh: dict) -> None:
        """엔진 미실행 시 주문 요청은 에러를 반환한다."""
        resp = client.post(
            "/api/trading/order",
            json={"symbol": "005930", "side": "BUY", "qty": 10, "type": "MARKET"},
            headers=sh,
        )
        # 엔진 미실행 상태이므로 400 또는 409
        assert resp.status_code in (400, 409)

    def test_limit_order_without_price_returns_422(self, client: TestClient, sh: dict) -> None:
        """지정가 주문 시 limit_price 없으면 422를 반환한다."""
        with patch("keyring.get_password", return_value="exists"):
            resp = client.post(
                "/api/trading/order",
                json={"symbol": "005930", "side": "BUY", "qty": 10, "type": "LIMIT"},
                headers=sh,
            )
        assert resp.status_code == 422


# ──────────────────────────────────────────────────────
# 규칙 라우터
# ──────────────────────────────────────────────────────

class TestRulesRouter:
    def test_get_rules_empty(self, client: TestClient, sh: dict) -> None:
        """초기 규칙 목록은 비어있다."""
        resp = client.get("/api/rules", headers=sh)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"] == []
        assert body["count"] == 0

    def test_sync_rules_with_direct_payload(self, client: TestClient, sh: dict) -> None:
        """직접 규칙을 제공하여 동기화한다."""
        rules = [{"id": 1, "name": "RSI매수"}]
        resp = client.post("/api/rules/sync", json={"rules": rules}, headers=sh)
        assert resp.status_code == 200
        assert resp.json()["data"]["synced_count"] == 1

        # 동기화 후 조회
        get_resp = client.get("/api/rules", headers=sh)
        assert get_resp.json()["count"] == 1

    def test_sync_without_cloud_url_returns_400(self, client: TestClient, sh: dict) -> None:
        """cloud.url이 없을 때 클라우드 sync 요청은 400을 반환한다."""
        resp = client.post("/api/rules/sync", json={}, headers=sh)
        assert resp.status_code == 400


# ──────────────────────────────────────────────────────
# 로그 라우터
# ──────────────────────────────────────────────────────

class TestLogsRouter:
    def test_get_logs_empty(self, client: TestClient, sh: dict) -> None:
        """초기 로그는 비어있다."""
        resp = client.get("/api/logs", headers=sh)
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["total"] == 0

    def test_get_logs_invalid_type(self, client: TestClient, sh: dict) -> None:
        """유효하지 않은 log_type은 success=False를 반환한다."""
        resp = client.get("/api/logs?log_type=INVALID", headers=sh)
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_get_logs_after_write(self, client: TestClient, sh: dict) -> None:
        """로그 기록 후 조회하면 해당 로그가 포함된다."""
        from local_server.storage.log_db import get_log_db, LOG_TYPE_SYSTEM
        get_log_db().write(LOG_TYPE_SYSTEM, "테스트 로그")

        resp = client.get("/api/logs?log_type=SYSTEM", headers=sh)
        body = resp.json()
        assert body["data"]["total"] >= 1


# ──────────────────────────────────────────────────────
# ConnectionManager 테스트
# ──────────────────────────────────────────────────────

class TestConnectionManager:
    def test_initial_count(self) -> None:
        """초기 연결 수는 0이다."""
        from local_server.routers.ws import ConnectionManager
        mgr = ConnectionManager()
        assert mgr.connection_count() == 0
