"""지표 히스토리 링버퍼 — spec §5.5."""
from __future__ import annotations
from collections import deque


class IndicatorHistory:
    def __init__(self, max_size: int = 60) -> None:
        self._max = max_size
        self._data: dict[str, deque[float]] = {}

    def push(self, key: str, value: float) -> None:
        if key not in self._data:
            self._data[key] = deque(maxlen=self._max)
        self._data[key].append(value)

    def get(self, key: str, index: int) -> float | None:
        buf = self._data.get(key)
        if buf is None or index >= len(buf):
            return None
        return buf[-(index + 1)]

    def as_list(self, key: str) -> list[float]:
        return list(self._data.get(key, []))

    def clear(self) -> None:
        self._data.clear()
