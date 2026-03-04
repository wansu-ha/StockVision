import hashlib
import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.email import send_verification_email, send_password_reset_email
from app.core.jwt_utils import create_jwt
from app.core.password import hash_password, verify_password
from app.models.auth import (
    User, RefreshToken, EmailVerificationToken, PasswordResetToken
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_CLOUD_URL = os.environ.get("CLOUD_URL", "http://localhost:8000")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _token() -> str:
    return secrets.token_urlsafe(32)


# ── Pydantic 스키마 ──────────────────────────────────────────────────

class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    nickname: str | None = None


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


# ── 회원가입 ──────────────────────────────────────────────────────────

@router.post("/register", status_code=200)
def register(body: RegisterBody, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="이미 사용 중인 이메일입니다.")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        nickname=body.nickname,
    )
    db.add(user)
    db.flush()  # user.id 확보

    token = _token()
    ev = EmailVerificationToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(ev)
    db.commit()

    send_verification_email(body.email, token, _CLOUD_URL)
    return {"success": True, "message": "인증 메일을 확인하세요."}


# ── 이메일 인증 ───────────────────────────────────────────────────────

@router.get("/verify-email", status_code=200)
def verify_email(token: str, db: Session = Depends(get_db)):
    ev = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == token,
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
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()

    if not user or not verify_password(user.password_hash, body.password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="이메일 인증이 필요합니다.")

    jwt_token = create_jwt(user.id, user.email, role=user.role)

    raw_rt = _token()
    rt = RefreshToken(
        user_id=user.id,
        token_hash=_sha256(raw_rt),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(rt)
    db.commit()

    return {
        "success": True,
        "jwt": jwt_token,
        "refresh_token": raw_rt,
        "expires_in": 86400,
    }


# ── 토큰 갱신 (Rotation) ─────────────────────────────────────────────

@router.post("/refresh", status_code=200)
def refresh(body: RefreshBody, db: Session = Depends(get_db)):
    token_hash = _sha256(body.refresh_token)
    rt = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()

    if not rt or rt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Refresh Token이 만료되었거나 유효하지 않습니다.")

    user = rt.user

    # Rotation: 기존 토큰 삭제 후 새 토큰 발급
    db.delete(rt)
    db.flush()

    new_raw_rt = _token()
    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=_sha256(new_raw_rt),
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(new_rt)

    new_jwt = create_jwt(user.id, user.email, role=user.role)
    db.commit()

    return {
        "success": True,
        "jwt": new_jwt,
        "refresh_token": new_raw_rt,
        "expires_in": 86400,
    }


# ── 로그아웃 ──────────────────────────────────────────────────────────

@router.post("/logout", status_code=200)
def logout(body: LogoutBody, db: Session = Depends(get_db)):
    token_hash = _sha256(body.refresh_token)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if rt:
        db.delete(rt)
        db.commit()
    return {"success": True}


# ── 비밀번호 재설정 요청 ──────────────────────────────────────────────

@router.post("/forgot-password", status_code=200)
def forgot_password(body: ForgotPasswordBody, db: Session = Depends(get_db)):
    # 이메일 열거 방지: 항상 200 반환
    user = db.query(User).filter(User.email == body.email).first()
    if user:
        token = _token()
        prt = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db.add(prt)
        db.commit()
        send_password_reset_email(body.email, token, _CLOUD_URL)
    return {"success": True, "message": "비밀번호 재설정 메일을 확인하세요."}


# ── 비밀번호 재설정 ───────────────────────────────────────────────────

@router.post("/reset-password", status_code=200)
def reset_password(body: ResetPasswordBody, db: Session = Depends(get_db)):
    prt = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == body.token,
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
