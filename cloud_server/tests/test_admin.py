"""
어드민 API 통합 테스트

- 어드민 권한 검증 (일반 유저 → 403)
- 통계, 유저 목록, 유저 수정
"""
from cloud_server.tests.conftest import _auth_header, _make_user


def test_admin_stats(client, db):
    admin = _make_user(db, email="admin@example.com", role="admin")
    res = client.get("/api/v1/admin/stats", headers=_auth_header(admin))
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_admin_users_list(client, db):
    admin = _make_user(db, email="admin@example.com", role="admin")
    _make_user(db, email="user1@example.com")
    _make_user(db, email="user2@example.com")

    res = client.get("/api/v1/admin/users", headers=_auth_header(admin))
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 3  # admin + 2 users


def test_admin_deactivate_user(client, db):
    admin = _make_user(db, email="admin@example.com", role="admin")
    user = _make_user(db, email="target@example.com")

    res = client.patch(
        f"/api/v1/admin/users/{user.id}",
        json={"is_active": False},
        headers=_auth_header(admin),
    )
    assert res.status_code == 200

    # 비활성 유저 로그인 불가
    res2 = client.post("/api/v1/auth/login", json={
        "email": "target@example.com",
        "password": "test1234",
    })
    assert res2.status_code == 403


def test_non_admin_forbidden(client, db):
    user = _make_user(db, email="user@example.com", role="user")
    h = _auth_header(user)

    assert client.get("/api/v1/admin/stats", headers=h).status_code == 403
    assert client.get("/api/v1/admin/users", headers=h).status_code == 403


# ── 공개 엔드포인트 ────────────────────────────────────────────


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_version(client):
    res = client.get("/api/v1/version")
    assert res.status_code == 200
