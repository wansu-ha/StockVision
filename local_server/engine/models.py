"""엔진 내부 데이터 모델.

sv_core.broker.models의 브로커 모델과는 별도로,
엔진 내부에서만 사용하는 보조 데이터 클래스를 정의한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class RuleConfig:
    """규칙 JSON을 파싱한 구조체."""

    id: int
    name: str
    symbol: str
    side: str  # "BUY" | "SELL"
    operator: str  # "AND" | "OR"
    conditions: list[dict] = field(default_factory=list)
    qty: int = 1
    order_type: str = "MARKET"  # "MARKET" | "LIMIT"
    limit_price: Optional[Decimal] = None
    is_active: bool = True
    priority: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> RuleConfig:
        """JSON dict → RuleConfig."""
        return cls(
            id=int(d["id"]),
            name=str(d.get("name", "")),
            symbol=str(d.get("symbol", "")),
            side=str(d.get("side", "BUY")),
            operator=str(d.get("operator", "AND")),
            conditions=d.get("conditions", []),
            qty=int(d.get("qty", 1)),
            order_type=str(d.get("order_type", "MARKET")),
            limit_price=Decimal(str(d["limit_price"])) if d.get("limit_price") else None,
            is_active=bool(d.get("is_active", True)),
            priority=int(d.get("priority", 0)),
        )


@dataclass
class MarketSnapshot:
    """특정 종목의 현재 시세 스냅샷."""

    symbol: str
    price: Decimal
    volume: int
    timestamp: Optional[datetime] = None
    # 지표 (BarBuilder / 외부에서 채움)
    indicators: dict = field(default_factory=dict)
