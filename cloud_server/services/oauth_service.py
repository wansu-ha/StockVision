"""OAuth2 서비스 — Google/Kakao 인증 처리.

외부 의존성 없이 httpx로 직접 HTTP 호출.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

import httpx
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cloud_server.core.config import settings
from cloud_server.core.security import create_jwt, generate_token, hash_token
from cloud_server.models.oauth_account import OAuthAccount
from cloud_server.models.user import RefreshToken, User

logger = logging.getLogger(__name__)

# Google OAuth2 endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Kakao OAuth2 endpoints
KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USERINFO_URL = "https://kapi.kakao.com/v2/user/me"


class OAuthService:
    """OAuth2 인증 처리."""

    # ── Google ──

    @staticmethod
    def get_google_auth_url(redirect_uri: str) -> str:
        """Google OAuth2 인증 URL 생성."""
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GOOGLE_AUTH_URL}?{qs}"

    @staticmethod
    async def exchange_google_code(code: str, redirect_uri: str) -> dict:
        """Google authorization code → access_token 교환."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def get_google_profile(access_token: str) -> dict:
        """Google access_token으로 사용자 프로필 조회."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()

    # ── Kakao ──

    @staticmethod
    def get_kakao_auth_url(redirect_uri: str) -> str:
        """Kakao OAuth2 인증 URL 생성."""
        params = {
            "client_id": settings.KAKAO_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{KAKAO_AUTH_URL}?{qs}"

    @staticmethod
    async def exchange_kakao_code(code: str, redirect_uri: str) -> dict:
        """Kakao authorization code → access_token 교환."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(KAKAO_TOKEN_URL, data={
                "code": code,
                "client_id": settings.KAKAO_CLIENT_ID,
                "client_secret": settings.KAKAO_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def get_kakao_profile(access_token: str) -> dict:
        """Kakao access_token으로 사용자 프로필 조회."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                KAKAO_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            account = data.get("kakao_account", {})
            return {
                "id": str(data["id"]),
                "email": account.get("email", ""),
                "name": account.get("profile", {}).get("nickname", ""),
            }

    # ── 공통: 로그인 또는 가입 ──

    @staticmethod
    def login_or_register(
        provider: str,
        provider_user_id: str,
        email: str,
        name: str,
        db: Session,
    ) -> dict:
        """OAuth2 로그인 or 자동 가입. JWT 발급."""
        # 이메일 필수 검증 (Kakao 미동의 등)
        if not email:
            raise HTTPException(
                status_code=400,
                detail="이메일 동의가 필요합니다. Kakao 설정에서 이메일 제공을 허용해주세요.",
            )

        # 1. 기존 OAuth 연동 확인
        oauth = db.query(OAuthAccount).filter(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        ).first()

        if oauth:
            user = oauth.user
        else:
            # 2. 같은 이메일 기존 사용자 확인 → 계정 연동
            user = db.query(User).filter(User.email == email).first()
            if not user:
                # 3. 신규 가입
                user = User(
                    email=email,
                    password_hash=None,  # OAuth 전용 계정 — 비밀번호 없음
                    nickname=name,
                    email_verified=True,  # OAuth2는 자동 인증
                )
                db.add(user)
                try:
                    db.flush()
                except IntegrityError:
                    db.rollback()
                    user = db.query(User).filter(User.email == email).first()
                    if not user:
                        raise  # 진짜 에러 (이메일 외 unique 제약 위반)

            # OAuth 연동 레코드 생성
            oauth = OAuthAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
            )
            db.add(oauth)

        # email_verified 보장 (기존 미인증 계정도 OAuth 로그인 시 인증 처리)
        if not user.email_verified:
            user.email_verified = True

        user.last_login_at = datetime.utcnow()

        # JWT + Refresh Token 발급
        jwt_token = create_jwt(user.id, user.email, role=user.role)
        raw_rt = generate_token()
        rt = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_rt),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add(rt)
        db.commit()

        return {
            "access_token": jwt_token,
            "refresh_token": raw_rt,
            "expires_in": 3600,
        }
