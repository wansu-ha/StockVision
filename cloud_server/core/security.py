"""
보안 유틸리티

- JWT 발급/검증 (HS256, 1시간 만료)
- Argon2id 비밀번호 해싱
- Refresh Token 생성 (SHA-256 해시 저장)
"""
import hashlib
import os
import secrets
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from jose import JWTError, jwt  # noqa: F401 (JWTError re-exported)

from cloud_server.core.config import settings

# Argon2id 설정 (OWASP 2023 권장)
_ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """비밀번호 → Argon2id 해시"""
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """비밀번호 검증. 일치하면 True"""
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_jwt(user_id: str, email: str, role: str = "user") -> str:
    """JWT 발급 (1시간 만료)"""
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def verify_jwt(token: str) -> dict:
    """JWT 검증 → payload dict 반환. 실패 시 JWTError 발생"""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])


def generate_token() -> str:
    """URL-safe 랜덤 토큰 생성 (Refresh Token, 인증 링크 등)"""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """토큰 → SHA-256 해시 (DB 저장용)"""
    return hashlib.sha256(token.encode()).hexdigest()
