"""계약 테스트 — cloud_server 응답 shape 검증.

CT-1: 인증 응답 shape
CT-2: 규칙(Rule) 응답 shape
"""
from __future__ import annotations

from unittest.mock import patch

from cloud_server.tests.conftest import _auth_header, _make_user


# ── 헬퍼 ──────────────────────────────────────────────────────────────

def assert_shape(data: dict, required: set[str], forbidden: set[str] = frozenset()):
    """필수 키 존재 + 금지 키 부재"""
    missing = required - data.keys()
    assert not missing, f"필수 키 누락: {missing}"
    present = forbidden & data.keys()
    assert not present, f"금지 키 존재: {present}"


# ── CT-1: 인증 응답 shape ─────────────────────────────────────────────


class TestAuthContract:
    """CT-1: 인증 응답 shape 검증."""

    def test_ct1a_login_shape(self, client, db):
        """CT-1a: login 응답에 access_token(str), refresh_token(str), expires_in(int) 포함."""
        _make_user(db)
        resp = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "test1234",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert_shape(data, {"access_token", "refresh_token", "expires_in"})
        assert isinstance(data["access_token"], str)
        assert isinstance(data["refresh_token"], str)
        assert isinstance(data["expires_in"], int)

    def test_ct1b_refresh_shape(self, client, db):
        """CT-1b: refresh 응답이 login과 동일 shape (expires_in 포함)."""
        _make_user(db)
        login_resp = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "test1234",
        })
        rt = login_resp.json()["data"]["refresh_token"]

        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert_shape(data, {"access_token", "refresh_token", "expires_in"})
        assert isinstance(data["access_token"], str)
        assert isinstance(data["refresh_token"], str)
        assert isinstance(data["expires_in"], int)

    def test_ct1c_login_refresh_no_jwt_key(self, client, db):
        """CT-1c: login/refresh 응답에 'jwt' 키가 없어야 한다 (금지 키)."""
        # rate limiter 누적 방지 — 이전 테스트의 로그인 시도가 쌓여 429 발생 가능
        from cloud_server.core.rate_limit import login_limiter
        login_limiter._store.clear()

        _make_user(db, email="ct1c@example.com", password="test1234")
        login_resp = client.post("/api/v1/auth/login", json={
            "email": "ct1c@example.com",
            "password": "test1234",
        })
        assert login_resp.status_code == 200, f"login 실패: {login_resp.json()}"
        login_data = login_resp.json()["data"]
        assert_shape(login_data, set(), forbidden={"jwt"})

        rt = login_data["refresh_token"]
        refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        assert refresh_resp.status_code == 200, f"refresh 실패: {refresh_resp.json()}"
        refresh_data = refresh_resp.json()["data"]
        assert_shape(refresh_data, set(), forbidden={"jwt"})

    @patch("cloud_server.api.auth.send_verification_email")
    def test_ct1e_register_shape(self, _mock_email, client, db):
        """CT-1e: register 응답에 success(bool), message(str) 포함, data 래퍼 없음."""
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "test1234",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["success"], bool)
        assert isinstance(body["message"], str)
        # data 래퍼가 없어야 한다
        assert "data" not in body


# ── CT-2: 규칙(Rule) 응답 shape ───────────────────────────────────────


class TestRuleContract:
    """CT-2: 규칙 응답 shape 검증."""

    # 필수 필드 17개
    RULE_REQUIRED_FIELDS = {
        "id", "name", "symbol", "is_active", "priority", "version",
        "created_at", "updated_at", "script", "execution", "trigger_policy",
        "buy_conditions", "sell_conditions", "order_type", "qty",
        "max_position_count", "budget_ratio",
    }

    # 금지 필드 (v1 래퍼 키 — 최상위에 존재하면 안 됨)
    RULE_FORBIDDEN_FIELDS = {"conditions", "operator", "side"}

    def _create_rule(self, client, db):
        """테스트용 규칙 생성 후 (user, header, rule) 반환."""
        user = _make_user(db)
        header = _auth_header(user)
        resp = client.post("/api/v1/rules", json={
            "name": "테스트규칙",
            "symbol": "005930",
            "qty": 10,
        }, headers=header)
        assert resp.status_code == 201
        return user, header, resp.json()["data"]

    def test_ct2a_rule_required_fields(self, client, db):
        """CT-2a: Rule 객체에 필수 필드 17개 전체 존재."""
        _, _, rule = self._create_rule(client, db)
        assert_shape(rule, self.RULE_REQUIRED_FIELDS)

    def test_ct2b_list_shape(self, client, db):
        """CT-2b: 목록 응답 shape — success(bool), data(list), version(int), count(int)."""
        user, header, _ = self._create_rule(client, db)
        resp = client.get("/api/v1/rules", headers=header)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["success"], bool)
        assert isinstance(body["data"], list)
        assert isinstance(body["version"], int)
        assert isinstance(body["count"], int)

    def test_ct2c_patch_returns_405(self, client, db):
        """CT-2c: PATCH /api/v1/rules/{id} → 405 (PUT만 허용)."""
        _, header, rule = self._create_rule(client, db)
        resp = client.patch(f"/api/v1/rules/{rule['id']}", json={
            "name": "변경",
        }, headers=header)
        assert resp.status_code == 405

    def test_ct2d_rule_no_forbidden_fields(self, client, db):
        """CT-2d: Rule 응답에 금지 필드 부재 (conditions, operator, side)."""
        _, _, rule = self._create_rule(client, db)
        assert_shape(rule, set(), forbidden=self.RULE_FORBIDDEN_FIELDS)
