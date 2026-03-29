"""조건 상태 추적기 — spec §3.6 T1~T5.

매 사이클 각 규칙의 조건 평가 결과를 기록하고, 트리거 이력을 추적.
조건 상태 API에서 이 데이터를 읽어 프론트에 전달.
"""
from __future__ import annotations
from collections import deque
from typing import Any


class ConditionTracker:
    def __init__(self, max_triggers: int = 100) -> None:
        self._latest: dict[int, dict[str, Any]] = {}  # rule_id → latest snapshot
        self._triggers: dict[int, deque[dict]] = {}     # rule_id → trigger history
        self._max = max_triggers

    def record(self, rule_id: int, cycle: str,
               conditions: list[dict], position: dict,
               action: dict | None) -> None:
        """매 사이클 조건 상태 기록."""
        self._latest[rule_id] = {
            "rule_id": rule_id, "cycle": cycle,
            "conditions": conditions, "position": position,
            "action": action,
        }

    def record_trigger(self, rule_id: int, at: str,
                       index: int, action: str) -> None:
        """규칙 트리거 기록."""
        if rule_id not in self._triggers:
            self._triggers[rule_id] = deque(maxlen=self._max)
        self._triggers[rule_id].append({"at": at, "index": index, "action": action})

    def get_latest(self, rule_id: int) -> dict | None:
        snap = self._latest.get(rule_id)
        if snap is None:
            return None
        result = dict(snap)
        result["triggered_history"] = list(self._triggers.get(rule_id, []))
        return result

    def get_all_latest(self) -> dict[int, dict]:
        return {rid: self.get_latest(rid) for rid in self._latest}

    def get_trigger_history(self, rule_id: int) -> list[dict]:
        return list(self._triggers.get(rule_id, []))
