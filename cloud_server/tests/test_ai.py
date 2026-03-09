"""
AI 분석 모듈 테스트

Claude API는 mock (실제 호출 금지).
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from cloud_server.tests.conftest import _auth_header, _make_user


# ── 스텁 fallback (키 미설정) ──────────────────────────────────


def test_stub_fallback_no_key(client, db):
    """ANTHROPIC_API_KEY 미설정 → source: stub, score: 0.0"""
    user = _make_user(db)
    headers = _auth_header(user)

    with patch("cloud_server.services.ai_service.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = ""
        mock_settings.CLAUDE_MODEL = "test-model"
        mock_settings.AI_DAILY_LIMIT = 100
        mock_settings.AI_CACHE_TTL = 3600
        resp = client.get("/api/v1/ai/analysis/005930?type=sentiment", headers=headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["source"] == "stub"
    assert data["result"]["score"] == 0.0
    assert data["result"]["label"] == "neutral"
    assert data["token_usage"] is None


# ── 스텁 fallback (유효하지 않은 키) ─────────────────────────


def test_stub_fallback_invalid_key(client, db):
    """Claude API AuthenticationError → source: stub 반환"""
    user = _make_user(db)
    headers = _auth_header(user)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"score": 0.5, "label": "positive", "text": "test"}')]
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)

    with patch("cloud_server.services.ai_service.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = "invalid-key"
        mock_settings.CLAUDE_MODEL = "test-model"
        mock_settings.AI_DAILY_LIMIT = 100
        mock_settings.AI_CACHE_TTL = 3600

        # anthropic import 시 AuthenticationError 발생 시뮬레이션
        with patch("cloud_server.services.ai_service.AIService._call_claude", return_value=None):
            resp = client.get("/api/v1/ai/analysis/005930?type=summary", headers=headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["source"] == "stub"


# ── 캐시 동작 ────────────────────────────────────────────────


def test_cache_hit(client, db):
    """동일 symbol+type 재호출 → cached: true"""
    user = _make_user(db)
    headers = _auth_header(user)

    claude_result = {
        "text": '{"score": 0.3, "label": "slightly_positive", "text": "테스트"}',
        "input_tokens": 200,
        "output_tokens": 80,
    }

    with patch("cloud_server.services.ai_service.settings") as mock_settings, \
         patch("cloud_server.services.ai_service.AIService._call_claude", return_value=claude_result), \
         patch("cloud_server.services.ai_service._daily_count", 0):
        mock_settings.ANTHROPIC_API_KEY = "valid-key"
        mock_settings.CLAUDE_MODEL = "test-model"
        mock_settings.AI_DAILY_LIMIT = 100
        mock_settings.AI_CACHE_TTL = 3600

        # 첫 호출
        resp1 = client.get("/api/v1/ai/analysis/005930?type=sentiment", headers=headers)
        assert resp1.status_code == 200
        assert resp1.json()["data"]["cached"] is False

        # 두 번째 호출 → 캐시 히트
        resp2 = client.get("/api/v1/ai/analysis/005930?type=sentiment", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["data"]["cached"] is True


# ── 일일 한도 ────────────────────────────────────────────────


def test_daily_limit_exceeded(client, db):
    """AI_DAILY_LIMIT 초과 → source: stub"""
    user = _make_user(db)
    headers = _auth_header(user)

    import cloud_server.services.ai_service as ai_mod

    with patch("cloud_server.services.ai_service.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = "valid-key"
        mock_settings.CLAUDE_MODEL = "test-model"
        mock_settings.AI_DAILY_LIMIT = 2
        mock_settings.AI_CACHE_TTL = 3600

        # 카운터를 한도까지 설정
        ai_mod._daily_count = 2
        ai_mod._daily_reset_date = __import__("datetime").date.today()

        resp = client.get("/api/v1/ai/analysis/005930?type=technical", headers=headers)

    assert resp.status_code == 200
    assert resp.json()["data"]["source"] == "stub"

    # 리셋
    ai_mod._daily_count = 0


# ── type별 분기 ───────────────────────────────────────────────


@pytest.mark.parametrize("analysis_type", ["sentiment", "summary", "risk", "technical"])
def test_type_routing(client, db, analysis_type):
    """각 type별 정상 호출 확인"""
    user = _make_user(db)
    headers = _auth_header(user)

    claude_result = {
        "text": json.dumps({"score": 0.1, "label": "neutral", "text": "분석 결과"}),
        "input_tokens": 150,
        "output_tokens": 60,
    }

    with patch("cloud_server.services.ai_service.settings") as mock_settings, \
         patch("cloud_server.services.ai_service.AIService._call_claude", return_value=claude_result), \
         patch("cloud_server.services.ai_service._daily_count", 0), \
         patch("cloud_server.services.ai_service.cache_get", return_value=None):
        mock_settings.ANTHROPIC_API_KEY = "valid-key"
        mock_settings.CLAUDE_MODEL = "test-model"
        mock_settings.AI_DAILY_LIMIT = 100
        mock_settings.AI_CACHE_TTL = 3600

        resp = client.get(f"/api/v1/ai/analysis/005930?type={analysis_type}", headers=headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["type"] == analysis_type
    assert data["source"] == "claude"


def test_invalid_type_returns_422(client, db):
    """잘못된 type → 422"""
    user = _make_user(db)
    headers = _auth_header(user)
    resp = client.get("/api/v1/ai/analysis/005930?type=invalid", headers=headers)
    assert resp.status_code == 422


# ── 이력 저장 ────────────────────────────────────────────────


def test_analysis_log_saved(client, db):
    """분석 호출 후 AIAnalysisLog 레코드 존재"""
    from cloud_server.models.ai import AIAnalysisLog

    user = _make_user(db)
    headers = _auth_header(user)

    with patch("cloud_server.services.ai_service.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = ""
        mock_settings.CLAUDE_MODEL = "test-model"
        mock_settings.AI_DAILY_LIMIT = 100
        mock_settings.AI_CACHE_TTL = 3600

        client.get("/api/v1/ai/analysis/005930?type=sentiment", headers=headers)

    # DB에서 이력 확인
    logs = db.query(AIAnalysisLog).filter(AIAnalysisLog.symbol == "005930").all()
    assert len(logs) >= 1
    assert logs[0].type == "sentiment"
    assert logs[0].source == "stub"


# ── 이력 조회 (어드민) ────────────────────────────────────────


def test_history_admin_only(client, db):
    """일반 유저 → 403, 어드민 → 200"""
    user = _make_user(db, email="user@test.com")
    admin = _make_user(db, email="admin@test.com", role="admin")

    # 일반 유저
    resp = client.get("/api/v1/ai/history", headers=_auth_header(user))
    assert resp.status_code == 403

    # 어드민
    resp = client.get("/api/v1/ai/history", headers=_auth_header(admin))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert "total" in data


# ── 상태 API ─────────────────────────────────────────────────


def test_status_api(client, db):
    """GET /api/v1/ai/status → available, model, daily_usage 반환"""
    user = _make_user(db)
    headers = _auth_header(user)
    resp = client.get("/api/v1/ai/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "available" in data
    assert "model" in data
    assert "daily_usage" in data
    assert "daily_limit" in data
    assert "cache_backend" in data


# ── 인증 없이 접근 금지 ──────────────────────────────────────


def test_unauthenticated_access_denied(client):
    """인증 없이 AI API 접근 → 401/403"""
    resp = client.get("/api/v1/ai/analysis/005930")
    assert resp.status_code in (401, 403)

    resp = client.get("/api/v1/ai/status")
    assert resp.status_code in (401, 403)

    resp = client.get("/api/v1/ai/history")
    assert resp.status_code in (401, 403)
