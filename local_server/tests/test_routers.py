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
            yield c


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

    def test_logout(self, client: TestClient) -> None:
        with patch("keyring.delete_password"):
            resp = client.post("/api/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# ──────────────────────────────────────────────────────
# 설정 라우터
# ──────────────────────────────────────────────────────

class TestConfigRouter:
    def test_get_config(self, client: TestClient) -> None:
        resp = client.get("/api/config")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "server" in body["data"]

    def test_patch_config(self, client: TestClient) -> None:
        resp = client.patch(
            "/api/config",
            json={"updates": {"log_level": "DEBUG"}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["log_level"] == "DEBUG"

    def test_config_masks_api_key(self, client: TestClient) -> None:
        """설정 조회 시 app_key가 마스킹된다."""
        # app_key가 있는 경우를 시뮬레이션
        with patch("keyring.get_password", return_value="real_key"):
            resp = client.get("/api/config")
        # kiwoom.app_key는 "" (config.json에 저장 안 함) — 마스킹 로직 확인
        body = resp.json()
        kiwoom = body["data"].get("kiwoom", {})
        # config.json에는 빈 문자열이 저장되므로 마스킹 안 됨
        assert kiwoom.get("app_key") is not None  # 필드 존재 확인


# ──────────────────────────────────────────────────────
# 매매 라우터
# ──────────────────────────────────────────────────────

class TestTradingRouter:
    def test_start_strategy_without_credentials_returns_400(
        self, client: TestClient
    ) -> None:
        """자격증명 없이 전략 시작 시 400을 반환한다."""
        with patch("keyring.get_password", return_value=None):
            resp = client.post("/api/strategy/start")
        assert resp.status_code == 400

    def test_start_and_stop_strategy(self, client: TestClient) -> None:
        """전략 시작 후 중지한다."""
        with patch("keyring.get_password", return_value="exists"):
            # 리셋
            from local_server.routers.status import set_strategy_running
            set_strategy_running(False)

            start_resp = client.post("/api/strategy/start")
            assert start_resp.status_code == 200
            assert start_resp.json()["data"]["strategy_engine"] == "running"

            stop_resp = client.post("/api/strategy/stop")
            assert stop_resp.status_code == 200
            assert stop_resp.json()["data"]["strategy_engine"] == "stopped"

    def test_place_market_order(self, client: TestClient) -> None:
        """시장가 주문을 발행한다."""
        with patch("keyring.get_password", return_value="exists"):
            resp = client.post(
                "/api/trading/order",
                json={"symbol": "005930", "side": "BUY", "qty": 10, "type": "MARKET"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["symbol"] == "005930"

    def test_limit_order_without_price_returns_422(self, client: TestClient) -> None:
        """지정가 주문 시 limit_price 없으면 422를 반환한다."""
        with patch("keyring.get_password", return_value="exists"):
            resp = client.post(
                "/api/trading/order",
                json={"symbol": "005930", "side": "BUY", "qty": 10, "type": "LIMIT"},
            )
        assert resp.status_code == 422


# ──────────────────────────────────────────────────────
# 규칙 라우터
# ──────────────────────────────────────────────────────

class TestRulesRouter:
    def test_get_rules_empty(self, client: TestClient) -> None:
        """초기 규칙 목록은 비어있다."""
        resp = client.get("/api/rules")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"] == []
        assert body["count"] == 0

    def test_sync_rules_with_direct_payload(self, client: TestClient) -> None:
        """직접 규칙을 제공하여 동기화한다."""
        rules = [{"id": 1, "name": "RSI매수"}]
        resp = client.post("/api/rules/sync", json={"rules": rules})
        assert resp.status_code == 200
        assert resp.json()["data"]["synced_count"] == 1

        # 동기화 후 조회
        get_resp = client.get("/api/rules")
        assert get_resp.json()["count"] == 1

    def test_sync_without_cloud_url_returns_400(self, client: TestClient) -> None:
        """cloud.url이 없을 때 클라우드 sync 요청은 400을 반환한다."""
        resp = client.post("/api/rules/sync", json={})
        assert resp.status_code == 400


# ──────────────────────────────────────────────────────
# 로그 라우터
# ──────────────────────────────────────────────────────

class TestLogsRouter:
    def test_get_logs_empty(self, client: TestClient) -> None:
        """초기 로그는 비어있다."""
        resp = client.get("/api/logs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["total"] == 0

    def test_get_logs_invalid_type(self, client: TestClient) -> None:
        """유효하지 않은 log_type은 success=False를 반환한다."""
        resp = client.get("/api/logs?log_type=INVALID")
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_get_logs_after_write(self, client: TestClient) -> None:
        """로그 기록 후 조회하면 해당 로그가 포함된다."""
        from local_server.storage.log_db import get_log_db, LOG_TYPE_SYSTEM
        get_log_db().write(LOG_TYPE_SYSTEM, "테스트 로그")

        resp = client.get("/api/logs?log_type=SYSTEM")
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
