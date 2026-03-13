"""
관심종목 API 통합 테스트

- 등록, 목록, 해제
- 중복 등록 처리
- 소유권 격리
"""
from cloud_server.tests.conftest import _auth_header, _make_user


def test_add_and_list_watchlist(client, db):
    user = _make_user(db)
    h = _auth_header(user)

    res = client.post("/api/v1/watchlist", json={"symbol": "005930"}, headers=h)
    assert res.status_code == 200
    assert res.json()["data"]["symbol"] == "005930"

    res2 = client.get("/api/v1/watchlist", headers=h)
    assert res2.json()["count"] == 1


def test_remove_watchlist(client, db):
    user = _make_user(db)
    h = _auth_header(user)

    client.post("/api/v1/watchlist", json={"symbol": "005930"}, headers=h)
    res = client.delete("/api/v1/watchlist/005930", headers=h)
    assert res.status_code == 200

    res2 = client.get("/api/v1/watchlist", headers=h)
    assert res2.json()["count"] == 0


def test_remove_nonexistent(client, db):
    user = _make_user(db)
    h = _auth_header(user)
    res = client.delete("/api/v1/watchlist/999999", headers=h)
    assert res.status_code == 404


def test_duplicate_add_returns_existing(client, db):
    user = _make_user(db)
    h = _auth_header(user)
    client.post("/api/v1/watchlist", json={"symbol": "005930"}, headers=h)
    res = client.post("/api/v1/watchlist", json={"symbol": "005930"}, headers=h)
    assert res.status_code == 200

    # 목록에 1개만 존재
    res2 = client.get("/api/v1/watchlist", headers=h)
    assert res2.json()["count"] == 1


def test_watchlist_isolation(client, db):
    user1 = _make_user(db, email="u1@example.com")
    user2 = _make_user(db, email="u2@example.com")

    client.post("/api/v1/watchlist", json={"symbol": "005930"}, headers=_auth_header(user1))

    # user2는 user1의 관심종목 안 보임
    res = client.get("/api/v1/watchlist", headers=_auth_header(user2))
    assert res.json()["count"] == 0
