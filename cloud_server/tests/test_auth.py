"""
인증 API 통합 테스트

- 회원가입, 이메일 인증, 로그인, 토큰 갱신, 로그아웃
- 비밀번호 재설정
- 에러 케이스 (중복 이메일, 잘못된 비밀번호, 미인증 등)
"""
from unittest.mock import patch

from cloud_server.models.user import EmailVerificationToken, PasswordResetToken
from cloud_server.tests.conftest import _auth_header, _make_user


# ── 회원가입 ────────────────────────────────────────────────────


@patch("cloud_server.api.auth.send_verification_email")
def test_register_success(mock_email, client, db):
    res = client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "securepass123",
        "terms_agreed": True,
        "privacy_agreed": True,
    })
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    mock_email.assert_called_once()


@patch("cloud_server.api.auth.send_verification_email")
def test_register_duplicate_email(mock_email, client, db):
    _make_user(db, email="dup@example.com")
    res = client.post("/api/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "securepass123",
        "terms_agreed": True,
        "privacy_agreed": True,
    })
    assert res.status_code == 409


def test_register_short_password(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "short@example.com",
        "password": "abc",
    })
    assert res.status_code == 422  # pydantic validation


# ── 이메일 인증 ────────────────────────────────────────────────


@patch("cloud_server.api.auth.send_verification_email")
def test_verify_email(mock_email, client, db):
    # 가입
    client.post("/api/v1/auth/register", json={
        "email": "verify@example.com",
        "password": "securepass123",
        "terms_agreed": True,
        "privacy_agreed": True,
    })
    # 이메일 mock에서 raw 토큰 추출 (S5: DB에는 해시만 저장)
    raw_token = mock_email.call_args[0][1]
    assert raw_token is not None

    res = client.get(f"/api/v1/auth/verify-email?token={raw_token}")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_verify_email_invalid_token(client):
    res = client.get("/api/v1/auth/verify-email?token=invalid-token")
    assert res.status_code == 400


# ── 로그인 ──────────────────────────────────────────────────────


def test_login_success(client, db):
    _make_user(db, email="login@example.com", password="pass1234")
    res = client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "pass1234",
    })
    assert res.status_code == 200
    data = res.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["expires_in"] == 3600


def test_login_wrong_password(client, db):
    _make_user(db, email="wrong@example.com", password="correct")
    res = client.post("/api/v1/auth/login", json={
        "email": "wrong@example.com",
        "password": "incorrect",
    })
    assert res.status_code == 401


def test_login_unverified(client, db):
    _make_user(db, email="unverified@example.com", verified=False)
    res = client.post("/api/v1/auth/login", json={
        "email": "unverified@example.com",
        "password": "test1234",
    })
    assert res.status_code == 403


def test_login_inactive(client, db):
    _make_user(db, email="inactive@example.com", active=False)
    res = client.post("/api/v1/auth/login", json={
        "email": "inactive@example.com",
        "password": "test1234",
    })
    assert res.status_code == 403


# ── 토큰 갱신 ──────────────────────────────────────────────────


def test_refresh_token_rotation(client, db):
    _make_user(db, email="refresh@example.com", password="pass1234")
    login = client.post("/api/v1/auth/login", json={
        "email": "refresh@example.com",
        "password": "pass1234",
    })
    rt = login.json()["data"]["refresh_token"]

    # 갱신
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert res.status_code == 200
    new_data = res.json()["data"]
    assert "access_token" in new_data
    assert new_data["refresh_token"] != rt  # rotation

    # 이전 토큰 재사용 불가
    res2 = client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert res2.status_code == 401


def test_refresh_invalid_token(client):
    res = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid"})
    assert res.status_code == 401


# ── 로그아웃 ────────────────────────────────────────────────────


def test_logout(client, db):
    _make_user(db, email="logout@example.com", password="pass1234")
    login = client.post("/api/v1/auth/login", json={
        "email": "logout@example.com",
        "password": "pass1234",
    })
    rt = login.json()["data"]["refresh_token"]

    res = client.post("/api/v1/auth/logout", json={"refresh_token": rt})
    assert res.status_code == 200

    # 로그아웃 후 갱신 불가
    res2 = client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert res2.status_code == 401


# ── 비밀번호 재설정 ────────────────────────────────────────────


@patch("cloud_server.api.auth.send_password_reset_email")
def test_forgot_and_reset_password(mock_email, client, db):
    _make_user(db, email="reset@example.com", password="oldpass12")

    # forgot
    res = client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    assert res.status_code == 200
    mock_email.assert_called_once()

    # 이메일 mock에서 raw 토큰 추출 (S5: DB에는 해시만 저장)
    raw_token = mock_email.call_args[0][1]
    assert raw_token is not None

    # reset
    res2 = client.post("/api/v1/auth/reset-password", json={
        "token": raw_token,
        "new_password": "newpass12",
    })
    assert res2.status_code == 200

    # 새 비밀번호로 로그인
    res3 = client.post("/api/v1/auth/login", json={
        "email": "reset@example.com",
        "password": "newpass12",
    })
    assert res3.status_code == 200


@patch("cloud_server.api.auth.send_password_reset_email")
def test_forgot_password_nonexistent_email(mock_email, client):
    """이메일 열거 방지 — 존재하지 않는 이메일도 200 반환"""
    res = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert res.status_code == 200
    mock_email.assert_not_called()


# ── 인증 필요 엔드포인트 ───────────────────────────────────────


def test_unauthenticated_access(client):
    """JWT 없이 인증 필요 API 접근 → 401"""
    res = client.get("/api/v1/rules")
    assert res.status_code in (401, 403)
