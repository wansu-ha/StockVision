"""
자동매매 규칙 데이터 모델
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Condition:
    variable: str   # "price" | "rsi_14" | context 키
    operator: str   # ">" | "<" | ">=" | "<=" | "=="
    value: float


@dataclass
class TradingRule:
    rule_id: int
    name: str
    symbol: str                     # "005930"
    side: str                       # "BUY" | "SELL"
    conditions: list[Condition]
    quantity: int
    is_active: bool
    last_executed: datetime | None = None


def rule_from_dict(d: dict) -> TradingRule:
    """JSON 딕셔너리 → TradingRule"""
    conditions = [
        Condition(
            variable=str(c["variable"]),
            operator=str(c["operator"]),
            value=float(c["value"]),
        )
        for c in d.get("conditions", [])
    ]
    return TradingRule(
        rule_id=int(d["id"]),
        name=str(d.get("name", "")),
        symbol=str(d.get("stock_code", "")),
        side=str(d.get("side", "BUY")),
        conditions=conditions,
        quantity=int(d.get("quantity", 0)),
        is_active=bool(d.get("is_active", True)),
    )
