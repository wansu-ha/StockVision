"""토큰 갱신 공유 유틸리티.

_refresh_lock: restore_session과 heartbeat _try_refresh가 공유하여 Token Rotation 경쟁 방지.
is_jwt_expired: JWT exp 클레임 확인 (60초 leeway).
"""
from __future__ import annotations

import asyncio
import base64
import json
import time

_refresh_lock = asyncio.Lock()


def is_jwt_expired(token: str, leeway: int = 60) -> bool:
    """JWT exp 클레임으로 만료 여부 확인. leeway초 여유를 둔다. 파싱 실패 시 만료로 간주."""
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload.get("exp", 0) < (time.time() + leeway)
    except Exception:
        return True
