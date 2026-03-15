"""로컬 서버 프로세스 인증.

시작 시 1회성 비밀을 생성하여 mutation API를 보호한다.
"""
import hmac
import secrets

from fastapi import Header, HTTPException, Request


def generate_secret() -> str:
    """32바이트 hex 비밀 생성 → 반환. 메모리(app.state)에만 보관."""
    return secrets.token_hex(32)


def is_secret_issued(request: Request) -> bool:
    """local_secret이 이미 클라이언트에 발급되었는지 확인."""
    return getattr(request.app.state, "_secret_issued", False)


def mark_secret_issued(request: Request) -> None:
    """local_secret이 클라이언트에 발급되었음을 표시."""
    request.app.state._secret_issued = True


async def require_local_secret(
    request: Request,
    x_local_secret: str = Header(None),
) -> None:
    """모든 보호 엔드포인트의 Depends.

    X-Local-Secret 헤더가 시작 시 생성된 비밀과 일치하는지 검증.
    """
    expected = request.app.state.local_secret
    if not x_local_secret or not hmac.compare_digest(x_local_secret, expected):
        raise HTTPException(status_code=403, detail="Invalid local secret")
