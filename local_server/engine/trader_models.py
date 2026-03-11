"""System Trader 데이터 모델.

CandidateSignal: 평가 결과 후보 신호
BlockReason: 차단 사유
TradeDecisionBatch: 사이클 결과 (선택 + 차단)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class BlockReason(str, Enum):
    """후보 차단 사유."""

    DUPLICATE_SYMBOL = "DUPLICATE_SYMBOL"
    MAX_POSITIONS = "MAX_POSITIONS"
    DAILY_BUDGET_EXCEEDED = "DAILY_BUDGET_EXCEEDED"
    SELL_NO_HOLDING = "SELL_NO_HOLDING"
    UNKNOWN = "UNKNOWN"


@dataclass
class CandidateSignal:
    """전략 평가 후 생성된 매매 후보 신호."""

    signal_id: str
    cycle_id: str
    rule_id: int
    symbol: str
    side: str  # "BUY" | "SELL"
    priority: int
    desired_qty: int
    detected_at: datetime
    latest_price: float
    reason: str
    raw_rule: dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeDecisionBatch:
    """사이클 결과 — 선택된 후보 + 차단된 후보."""

    cycle_id: str
    selected: list[CandidateSignal] = field(default_factory=list)
    dropped: list[tuple[CandidateSignal, BlockReason]] = field(default_factory=list)
