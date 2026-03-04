from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from app.core.jwt_utils import verify_jwt

_bearer = HTTPBearer()


def current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    """JWT 검증 → payload dict 반환. 실패 시 401"""
    try:
        return verify_jwt(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다.")


def require_admin(user: dict = Depends(current_user)) -> dict:
    """관리자 권한 확인. role != 'admin' 이면 403."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다.")
    return user
