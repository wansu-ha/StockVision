"""오프라인 변경사항 큐 저장소.

클라우드 서버에 연결할 수 없을 때 로컬 변경사항(규칙 생성/수정, 관심종목 등)을
sync_queue.json에 적재한다. 클라우드 복구 시 flush하여 반영한다.
충돌 해결: last-write-wins (timestamp 기반).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_PATH = Path.home() / ".stockvision" / "sync_queue.json"

ActionType = Literal[
    "rule_create",
    "rule_update",
    "rule_delete",
    "watchlist_add",
    "watchlist_remove",
]


MAX_QUEUE_SIZE = 100


class SyncQueue:
    """오프라인 변경사항 큐."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or DEFAULT_QUEUE_PATH
        self._queue: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with self._path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                self._queue = data if isinstance(data, list) else []
            except (json.JSONDecodeError, OSError) as e:
                logger.error("sync 큐 로드 실패: %s", e)
                self._queue = []
        else:
            self._queue = []

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(self._queue, f, ensure_ascii=False, indent=2)

    def enqueue(self, action_type: ActionType, data: dict[str, Any]) -> None:
        """변경사항을 큐에 추가한다. 크기 초과 시 오래된 항목부터 제거."""
        while len(self._queue) >= MAX_QUEUE_SIZE:
            removed = self._queue.pop(0)
            logger.warning("SyncQueue 초과 — 오래된 항목 제거: %s", removed.get("type"))
        entry = {
            "type": action_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._queue.append(entry)
        self._save()
        logger.debug("sync 큐 적재: %s (총 %d건)", action_type, len(self._queue))

    def peek_all(self) -> list[dict[str, Any]]:
        """큐의 모든 항목을 반환한다 (제거하지 않음)."""
        return list(self._queue)

    def dequeue(self) -> dict[str, Any] | None:
        """큐에서 가장 오래된 항목을 꺼낸다."""
        if not self._queue:
            return None
        item = self._queue.pop(0)
        self._save()
        return item

    def clear(self) -> int:
        """큐를 비우고 제거된 항목 수를 반환한다."""
        count = len(self._queue)
        self._queue = []
        self._save()
        logger.info("sync 큐 초기화: %d개 제거", count)
        return count

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def count(self) -> int:
        return len(self._queue)


_instance: SyncQueue | None = None


def get_sync_queue() -> SyncQueue:
    global _instance
    if _instance is None:
        _instance = SyncQueue()
    return _instance
