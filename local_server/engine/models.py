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
    """규칙 JSON을 파싱한 구조체.

    v2: DSL script 기반. script가 None이면 v1 JSON 폴백.
    """

    id: int
    name: str
    symbol: str
    is_active: bool = True
    priority: int = 0

    # v2 DSL
    script: Optional[str] = None
    execution: dict = field(default_factory=lambda: {
        "order_type": "MARKET", "qty_type": "FIXED", "qty_value": 1,
    })
    trigger_policy: dict = field(default_factory=lambda: {
        "frequency": "ONCE_PER_DAY",
    })

    # v1 하위 호환
    buy_conditions: Optional[dict] = None
    sell_conditions: Optional[dict] = None
    operator: str = "AND"
    qty: int = 1
    order_type: str = "MARKET"
    limit_price: Optional[Decimal] = None

    @classmethod
    def from_dict(cls, d: dict) -> RuleConfig:
        """JSON dict → RuleConfig. v2/v1 양쪽 지원."""
        # execution: 우선순위 — non-null이면 JSON, null이면 개별 필드 폴백
        execution = d.get("execution")
        if execution is None:
            execution = {
                "order_type": str(d.get("order_type", "MARKET")).upper(),
                "qty_type": "FIXED",
                "qty_value": int(d.get("qty", 1)),
                "limit_price": d.get("limit_price"),
            }

        return cls(
            id=int(d["id"]),
            name=str(d.get("name", "")),
            symbol=str(d.get("symbol", "")),
            is_active=bool(d.get("is_active", True)),
            priority=int(d.get("priority", 0)),
            script=d.get("script"),
            execution=execution,
            trigger_policy=d.get("trigger_policy") or {"frequency": "ONCE_PER_DAY"},
            buy_conditions=d.get("buy_conditions"),
            sell_conditions=d.get("sell_conditions"),
            operator=str(d.get("operator", "AND")),
            qty=int(d.get("qty", 1)),
            order_type=str(d.get("order_type", "MARKET")),
            limit_price=Decimal(str(d["limit_price"])) if d.get("limit_price") else None,
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
