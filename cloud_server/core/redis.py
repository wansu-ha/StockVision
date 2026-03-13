"""
Redis 연결 + 메모리 캐시 fallback

REDIS_URL 설정 시 Redis 사용, 미설정/연결 실패 시 메모리 캐시 fallback.
"""
import json
import logging
from datetime import datetime, timezone

from cloud_server.core.config import settings

logger = logging.getLogger(__name__)

_redis_client = None  # redis.Redis | None
_memory_cache: dict[str, tuple[str, float]] = {}  # key → (json_value, expire_at)


def get_redis():
    """Redis 연결 반환. 불가 시 None."""
    global _redis_client
    if not settings.REDIS_URL:
        return None
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis_client.ping()
            logger.info("Redis 연결 성공")
        except Exception as e:
            logger.warning("Redis 연결 실패, 메모리 캐시 사용: %s", e)
            _redis_client = None
    return _redis_client


def cache_get(key: str) -> dict | None:
    """캐시 조회 (Redis → 메모리 fallback)."""
    r = get_redis()
    if r:
        try:
            val = r.get(key)
            return json.loads(val) if val else None
        except Exception:
            pass
    # 메모리 fallback
    entry = _memory_cache.get(key)
    if entry:
        val, expire_at = entry
        if datetime.now(timezone.utc).timestamp() < expire_at:
            return json.loads(val)
        del _memory_cache[key]
    return None


def cache_set(key: str, value: dict, ttl: int) -> None:
    """캐시 저장 (Redis → 메모리 fallback)."""
    r = get_redis()
    data = json.dumps(value, ensure_ascii=False)
    if r:
        try:
            r.setex(key, ttl, data)
            return
        except Exception:
            pass
    # 메모리 fallback
    expire_at = datetime.now(timezone.utc).timestamp() + ttl
    _memory_cache[key] = (data, expire_at)


def cache_backend() -> str:
    """현재 캐시 백엔드 이름."""
    return "redis" if get_redis() else "memory"
