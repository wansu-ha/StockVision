"""ContextCache — AI 컨텍스트 인메모리 캐시.

클라우드 서버에서 주기적으로 fetch한 시장 컨텍스트를
TTL 기반으로 메모리에 캐싱한다.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional


class ContextCache:
    """AI 컨텍스트 인메모리 캐시."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._cache: dict[str, Any] = {}
        self._last_update: Optional[datetime] = None
        self._ttl = timedelta(seconds=ttl_seconds)

    def update(self, context: dict[str, Any]) -> None:
        """캐시 갱신."""
        self._cache = dict(context)
        self._last_update = datetime.now()

    def get(self) -> dict[str, Any]:
        """캐시 전체 조회. TTL 만료되어도 마지막 데이터 반환 (폴백)."""
        return dict(self._cache)

    def get_field(self, field: str, default: Any = None) -> Any:
        """특정 필드 조회."""
        return self._cache.get(field, default)

    def is_valid(self) -> bool:
        """캐시 유효 여부 (TTL 내)."""
        if self._last_update is None:
            return False
        return datetime.now() - self._last_update <= self._ttl

    def clear(self) -> None:
        """캐시 초기화."""
        self._cache.clear()
        self._last_update = None

    @property
    def last_update(self) -> Optional[datetime]:
        return self._last_update
