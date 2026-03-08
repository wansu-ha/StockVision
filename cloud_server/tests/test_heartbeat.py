"""
하트비트 API 통합 테스트

- 하트비트 전송 + 버전 정보 반환
- 규칙 변경 후 version 반영 확인
"""
from datetime import datetime

from cloud_server.tests.conftest import _auth_header, _make_user


def _heartbeat_payload():
    return {
        "uuid": "test-uuid-1234",
        "version": "1.0.0",
        "os": "windows",
        "broker_connected": True,
        "engine_running": True,
        "active_rules_count": 2,
        "timestamp": datetime.utcnow().isoformat(),
    }


def test_heartbeat_returns_versions(client, db):
    user = _make_user(db)
    h = _auth_header(user)

    res = client.post("/api/v1/heartbeat", json=_heartbeat_payload(), headers=h)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "rules_version" in data
    assert "context_version" in data
    assert "watchlist_version" in data
    assert "stock_master_version" in data


def test_heartbeat_reflects_rule_version(client, db):
    user = _make_user(db)
    h = _auth_header(user)

    # 규칙 없을 때
    res1 = client.post("/api/v1/heartbeat", json=_heartbeat_payload(), headers=h)
    assert res1.json()["data"]["rules_version"] == 0

    # 규칙 생성
    client.post("/api/v1/rules", json={
        "name": "테스트", "symbol": "005930", "qty": 1,
    }, headers=h)

    res2 = client.post("/api/v1/heartbeat", json=_heartbeat_payload(), headers=h)
    assert res2.json()["data"]["rules_version"] == 1

    # 규칙 수정 → version 증가
    rules = client.get("/api/v1/rules", headers=h).json()["data"]
    rule_id = rules[0]["id"]
    client.put(f"/api/v1/rules/{rule_id}", json={"name": "수정됨"}, headers=h)

    res3 = client.post("/api/v1/heartbeat", json=_heartbeat_payload(), headers=h)
    assert res3.json()["data"]["rules_version"] == 2


def test_heartbeat_includes_server_version_info(client, db):
    """하트비트 응답에 latest_version, min_version, download_url이 포함된다."""
    user = _make_user(db)
    h = _auth_header(user)

    res = client.post("/api/v1/heartbeat", json=_heartbeat_payload(), headers=h)
    data = res.json()["data"]
    assert "latest_version" in data
    assert "min_version" in data
    assert "download_url" in data


def test_heartbeat_unauthenticated(client):
    res = client.post("/api/v1/heartbeat", json=_heartbeat_payload())
    assert res.status_code in (401, 403)
