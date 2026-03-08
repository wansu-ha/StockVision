"""
규칙 CRUD 통합 테스트

- 생성, 목록, 상세, 수정, 삭제
- version 증가 확인
- 소유권 격리 (타인 규칙 접근 불가)
"""
from cloud_server.tests.conftest import _auth_header, _make_user


def _create_rule(client, headers, name="RSI 매수", symbol="005930", **kwargs):
    payload = {"name": name, "symbol": symbol, "qty": 1, **kwargs}
    return client.post("/api/v1/rules", json=payload, headers=headers)


# ── CRUD ────────────────────────────────────────────────────────


def test_create_rule(client, db):
    user = _make_user(db)
    h = _auth_header(user)
    res = _create_rule(client, h)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["name"] == "RSI 매수"
    assert data["symbol"] == "005930"
    assert data["version"] == 1


def test_list_rules(client, db):
    user = _make_user(db)
    h = _auth_header(user)
    _create_rule(client, h, name="규칙1")
    _create_rule(client, h, name="규칙2")

    res = client.get("/api/v1/rules", headers=h)
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 2
    assert body["version"] >= 1


def test_get_rule(client, db):
    user = _make_user(db)
    h = _auth_header(user)
    created = _create_rule(client, h).json()["data"]

    res = client.get(f"/api/v1/rules/{created['id']}", headers=h)
    assert res.status_code == 200
    assert res.json()["data"]["id"] == created["id"]


def test_update_rule_increments_version(client, db):
    user = _make_user(db)
    h = _auth_header(user)
    created = _create_rule(client, h).json()["data"]
    assert created["version"] == 1

    res = client.put(
        f"/api/v1/rules/{created['id']}",
        json={"name": "수정된 규칙"},
        headers=h,
    )
    assert res.status_code == 200
    assert res.json()["data"]["version"] == 2
    assert res.json()["data"]["name"] == "수정된 규칙"


def test_delete_rule(client, db):
    user = _make_user(db)
    h = _auth_header(user)
    created = _create_rule(client, h).json()["data"]

    res = client.delete(f"/api/v1/rules/{created['id']}", headers=h)
    assert res.status_code == 200

    # 삭제 확인
    res2 = client.get(f"/api/v1/rules/{created['id']}", headers=h)
    assert res2.status_code == 404


# ── 소유권 격리 ────────────────────────────────────────────────


def test_cannot_access_other_user_rule(client, db):
    user1 = _make_user(db, email="user1@example.com")
    user2 = _make_user(db, email="user2@example.com")

    h1 = _auth_header(user1)
    h2 = _auth_header(user2)

    created = _create_rule(client, h1).json()["data"]

    # user2가 user1의 규칙 접근 시도
    assert client.get(f"/api/v1/rules/{created['id']}", headers=h2).status_code == 404
    assert client.put(f"/api/v1/rules/{created['id']}", json={"name": "X"}, headers=h2).status_code == 404
    assert client.delete(f"/api/v1/rules/{created['id']}", headers=h2).status_code == 404


# ── 중복 이름 ──────────────────────────────────────────────────


def test_duplicate_rule_name(client, db):
    user = _make_user(db)
    h = _auth_header(user)
    _create_rule(client, h, name="중복")
    res = _create_rule(client, h, name="중복")
    assert res.status_code == 409


# ── DSL 스크립트 ───────────────────────────────────────────────


def test_create_rule_with_script(client, db):
    user = _make_user(db)
    h = _auth_header(user)
    script = "매수: RSI(14) <= 30\n매도: RSI(14) >= 70"
    res = _create_rule(client, h, name="DSL 규칙", script=script)
    assert res.status_code == 201
    assert res.json()["data"]["script"] == script
