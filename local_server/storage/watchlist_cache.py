"""관심종목 JSON 캐시 저장소.

클라우드 서버와 동기화된 관심종목을 로컬 watchlist.json에 캐시한다.
네트워크 단절 시에도 마지막 동기화된 관심종목으로 UI가 동작할 수 있다.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_WATCHLIST_PATH = Path.home() / ".stockvision" / "watchlist.json"


class WatchlistCache:
    """관심종목 JSON 캐시."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or DEFAULT_WATCHLIST_PATH
        self._items: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with self._path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                self._items = data if isinstance(data, list) else []
                logger.info("관심종목 캐시 로드: %d개", len(self._items))
            except (json.JSONDecodeError, OSError) as e:
                logger.error("관심종목 캐시 로드 실패: %s", e)
                self._items = []
        else:
            self._items = []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(self._items, f, ensure_ascii=False, indent=2)

    def get_all(self) -> list[dict[str, Any]]:
        """전체 관심종목을 반환한다."""
        return list(self._items)

    def sync(self, items: list[dict[str, Any]]) -> None:
        """클라우드에서 받은 관심종목으로 전량 교체한다."""
        self._items = list(items)
        self._save()
        logger.info("관심종목 캐시 동기화: %d개", len(self._items))

    def add(self, symbol: str, name: str = "") -> bool:
        """관심종목을 추가한다. 이미 있으면 False."""
        if any(item.get("symbol") == symbol for item in self._items):
            return False
        self._items.append({"symbol": symbol, "name": name})
        self._save()
        return True

    def remove(self, symbol: str) -> bool:
        """관심종목을 제거한다. 없으면 False."""
        before = len(self._items)
        self._items = [item for item in self._items if item.get("symbol") != symbol]
        if len(self._items) < before:
            self._save()
            return True
        return False

    def has(self, symbol: str) -> bool:
        return any(item.get("symbol") == symbol for item in self._items)

    def count(self) -> int:
        return len(self._items)


_instance: WatchlistCache | None = None


def get_watchlist_cache() -> WatchlistCache:
    global _instance
    if _instance is None:
        _instance = WatchlistCache()
    return _instance
