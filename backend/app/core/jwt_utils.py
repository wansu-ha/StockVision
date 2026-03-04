import os
from datetime import datetime, timedelta
from jose import jwt, JWTError  # noqa: F401 (JWTError re-exported for callers)

_ALGORITHM = "HS256"
_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "24"))


def _secret() -> str:
    s = os.environ.get("JWT_SECRET", "")
    if not s:
        raise RuntimeError("JWT_SECRET 환경변수가 설정되지 않았습니다.")
    return s


def create_jwt(user_id: str, email: str, role: str = "user") -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=_EXPIRE_HOURS),
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def verify_jwt(token: str) -> dict:
    """JWT 검증 → payload dict 반환. 실패 시 JWTError 발생"""
    return jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
