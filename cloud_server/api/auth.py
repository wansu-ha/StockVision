"""
인증 API

POST /api/v1/auth/register                    회원가입 + 이메일 인증 발송
GET  /api/v1/auth/verify-email                이메일 인증 완료
POST /api/v1/auth/login                       JWT + Refresh Token 발급
POST /api/v1/auth/refresh                     JWT 갱신 (Token Rotation)
POST /api/v1/auth/logout                      Refresh Token 무효화
POST /api/v1/auth/forgot-password             재설정 이메일 발송
POST /api/v1/auth/reset-password              새 비밀번호 설정
GET  /api/v1/auth/oauth/{provider}/login      OAuth 인증 URL 반환
POST /api/v1/auth/oauth/{provider}/callback   OAuth code 교환 → JWT 발급
POST /api/v1/auth/verify-password             비밀번호 재검증 (원격 arm용)
"""
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from cloud_server.core.database import get_db
from cloud_server.core.email import send_verification_email, send_password_reset_email
from cloud_server.core.rate_limit import check_login_rate, check_register_rate, check_forgot_pw_rate
from cloud_server.core.security import (
    create_jwt, generate_token, hash_password, hash_token, verify_password
)
from cloud_server.models.user import (
    EmailVerificationToken, PasswordResetToken, RefreshToken, User
)
from cloud_server.models.legal import LegalConsent
from cloud_server.api.dependencies import current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ── Pydantic 스키마 ──────────────────────────────────────────────────

MIN_PASSWORD_LENGTH = 8


def _validate_password_strength(v: str) -> str:
    """S7: 비밀번호 강도 검증 — 8자 이상 + 영문 + 숫자"""
    if len(v) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"비밀번호는 최소 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다.")
    if not re.search(r"[A-Za-z]", v):
        raise ValueError("비밀번호에 영문자가 포함되어야 합니다.")
    if not re.search(r"[0-9]", v):
        raise ValueError("비밀번호에 숫자가 포함되어야 합니다.")
    return v


class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    nickname: str | None = None
    terms_agreed: bool = False
    privacy_agreed: bool = False

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class LogoutBody(BaseModel):
    refresh_token: str


class ForgotPasswordBody(BaseModel):
    email: EmailStr


class ResetPasswordBody(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


# ── 회원가입 ──────────────────────────────────────────────────────────


@router.post("/register", status_code=200)
def register(body: RegisterBody, request: Request, db: Session = Depends(get_db)):
    """회원가입 + 이메일 인증 발송"""
    check_register_rate(request)

    # L1: 약관 동의 검증
    if not body.terms_agreed or not body.privacy_agreed:
        raise HTTPException(400, "이용약관과 개인정보처리방침에 동의해야 합니다.")

    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다.")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        nickname=body.nickname,
    )
    db.add(user)
    db.flush()  # user.id 확보

    token = generate_token()
    ev = EmailVerificationToken(
        user_id=user.id,
        token_hash=hash_token(token),  # S5: 해시 저장
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(ev)

    # L1: 약관 동의 기록
    for doc_type, version in [("terms", "1.1"), ("privacy", "1.1")]:
        db.add(LegalConsent(
            user_id=user.id, doc_type=doc_type, doc_version=version,
        ))

    db.commit()

    send_verification_email(body.email, token)
    return {"success": True, "message": "인증 메일을 확인하세요."}


# ── 이메일 인증 ───────────────────────────────────────────────────────


@router.get("/verify-email", status_code=200)
def verify_email(token: str, db: Session = Depends(get_db)):
    """이메일 인증 완료"""
    ev = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token_hash == hash_token(token),  # S5: 해시 비교
        EmailVerificationToken.used == False,  # noqa: E712
    ).first()

    if not ev:
        raise HTTPException(status_code=400, detail="유효하지 않은 인증 토큰입니다.")
    if ev.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="만료된 인증 토큰입니다.")

    ev.used = True
    ev.user.email_verified = True
    db.commit()
    return {"success": True, "message": "이메일 인증이 완료되었습니다."}


# ── 로그인 ────────────────────────────────────────────────────────────


@router.post("/login", status_code=200)
def login(body: LoginBody, request: Request, db: Session = Depends(get_db)):
    """로그인 → JWT + Refresh Token 발급"""
    check_login_rate(request)

    user = db.query(User).filter(User.email == body.email).first()

    if not user or not verify_password(user.password_hash, body.password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="이메일 인증이 필요합니다.")
    if not user.is_active or user.deleted_at:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다.")

    jwt_token = create_jwt(user.id, user.email, role=user.role)

    raw_rt = generate_token()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_rt),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(rt)

    user.last_login_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "data": {
            "access_token": jwt_token,  # A7: jwt → access_token
            "refresh_token": raw_rt,
            "expires_in": 3600,  # 1시간
        },
    }


# ── 토큰 갱신 (Rotation) ─────────────────────────────────────────────


@router.post("/refresh", status_code=200)
def refresh(body: RefreshBody, db: Session = Depends(get_db)):
    """JWT 갱신 (Refresh Token Rotation)"""
    token_hash = hash_token(body.refresh_token)
    rt = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()

    if not rt or rt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh Token이 만료되었거나 유효하지 않습니다.")

    user = rt.user

    # Rotation: 기존 토큰 삭제 후 새 토큰 발급
    rt.rotated_at = datetime.utcnow()
    db.delete(rt)
    db.flush()

    new_raw_rt = generate_token()
    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_raw_rt),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(new_rt)

    new_jwt = create_jwt(user.id, user.email, role=user.role)
    db.commit()

    return {
        "success": True,
        "data": {
            "access_token": new_jwt,  # A7: jwt → access_token
            "refresh_token": new_raw_rt,
            "expires_in": 3600,
        },
    }


# ── 로그아웃 ──────────────────────────────────────────────────────────


@router.post("/logout", status_code=200)
def logout(body: LogoutBody, db: Session = Depends(get_db)):
    """Refresh Token 무효화"""
    token_hash = hash_token(body.refresh_token)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if rt:
        db.delete(rt)
        db.commit()
    return {"success": True}


# ── 비밀번호 재설정 요청 ──────────────────────────────────────────────


@router.post("/forgot-password", status_code=200)
def forgot_password(body: ForgotPasswordBody, request: Request, db: Session = Depends(get_db)):
    """비밀번호 재설정 이메일 발송"""
    check_forgot_pw_rate(request)

    # 이메일 열거 방지: 항상 200 반환
    user = db.query(User).filter(User.email == body.email).first()
    if user:
        token = generate_token()
        prt = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(token),  # S5: 해시 저장
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db.add(prt)
        db.commit()
        send_password_reset_email(body.email, token)
    return {"success": True, "message": "비밀번호 재설정 메일을 확인하세요."}


# ── 비밀번호 재설정 ───────────────────────────────────────────────────


@router.post("/reset-password", status_code=200)
def reset_password(body: ResetPasswordBody, db: Session = Depends(get_db)):
    """새 비밀번호 설정"""
    prt = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == hash_token(body.token),  # S5: 해시 비교
        PasswordResetToken.used == False,  # noqa: E712
    ).first()

    if not prt or prt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="유효하지 않거나 만료된 토큰입니다.")

    user = prt.user
    user.password_hash = hash_password(body.new_password)
    prt.used = True

    # 기존 세션 전체 무효화
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete()
    db.commit()

    return {"success": True, "message": "비밀번호가 재설정되었습니다."}


# ── OAuth2 소셜 로그인 ─────────────────────────────────────────────


class OAuthCallbackBody(BaseModel):
    code: str
    redirect_uri: str


@router.get("/oauth/{provider}/login")
def oauth_login(provider: str, redirect_uri: str = ""):
    """OAuth2 인증 URL 반환."""
    from cloud_server.services.oauth_service import OAuthService

    if provider == "google":
        url = OAuthService.get_google_auth_url(redirect_uri)
    elif provider == "kakao":
        url = OAuthService.get_kakao_auth_url(redirect_uri)
    else:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 제공자: {provider}")

    return {"success": True, "data": {"auth_url": url}}


@router.post("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    body: OAuthCallbackBody,
    db: Session = Depends(get_db),
):
    """OAuth2 code 교환 → JWT 발급."""
    from cloud_server.services.oauth_service import OAuthService

    try:
        if provider == "google":
            tokens = await OAuthService.exchange_google_code(body.code, body.redirect_uri)
            profile = await OAuthService.get_google_profile(tokens["access_token"])
            provider_user_id = profile.get("id", "")
            email = profile.get("email", "")
            name = profile.get("name", "")
        elif provider == "kakao":
            tokens = await OAuthService.exchange_kakao_code(body.code, body.redirect_uri)
            profile = await OAuthService.get_kakao_profile(tokens["access_token"])
            provider_user_id = profile.get("id", "")
            email = profile.get("email", "")
            name = profile.get("name", "")
        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 제공자: {provider}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth2 인증 실패: {e}")

    result = OAuthService.login_or_register(
        provider=provider,
        provider_user_id=provider_user_id,
        email=email,
        name=name,
        db=db,
    )
    return {"success": True, "data": result}


# ── 비밀번호 재검증 (원격 arm용) ────────────────────────────────────


class VerifyPasswordBody(BaseModel):
    password: str


@router.post("/verify-password")
def verify_password_endpoint(
    body: VerifyPasswordBody,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """비밀번호 재검증 (원격 arm 확인용). JWT 발급 없이 성공/실패만 반환."""
    from cloud_server.api.dependencies import current_user  # noqa: already imported above

    db_user = db.query(User).filter(User.id == user["sub"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    if not db_user.password_hash:
        raise HTTPException(status_code=400, detail="OAuth 전용 계정입니다. OAuth 재인증을 사용하세요.")

    if not verify_password(db_user.password_hash, body.password):
        raise HTTPException(status_code=401, detail="비밀번호가 올바르지 않습니다.")

    return {"success": True}
