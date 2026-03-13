"""ResultStore — 규칙별 최근 실행 결과 메모리 저장소."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ResultStatus(str, Enum):
    """실행 결과 상태."""

    SUCCESS = "SUCCESS"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass
class LastRuleResult:
    """규칙별 최근 실행 결과."""

    rule_id: int
    status: ResultStatus
    reason: str
    at: str  # ISO 형식 문자열


# 싱글턴 인메모리 저장소
_store: dict[int, LastRuleResult] = {}


def record_result(rule_id: int, status: ResultStatus, reason: str = "") -> None:
    """실행 결과를 기록한다."""
    _store[rule_id] = LastRuleResult(
        rule_id=rule_id,
        status=status,
        reason=reason,
        at=datetime.now().isoformat(),
    )


def get_all_results() -> dict[int, LastRuleResult]:
    """전체 결과 반환."""
    return dict(_store)


def get_result(rule_id: int) -> LastRuleResult | None:
    """특정 규칙 결과 반환."""
    return _store.get(rule_id)


def to_dict(result: LastRuleResult) -> dict[str, Any]:
    """API 응답용 직렬화."""
    return {
        "rule_id": result.rule_id,
        "status": result.status.value,
        "reason": result.reason,
        "at": result.at,
    }
