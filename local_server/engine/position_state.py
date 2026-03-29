"""PositionState — 종목별 포지션 상태 추적. spec §3.3."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class PositionState:
    symbol: str
    entry_price: float = 0.0
    entry_time: datetime | None = None
    highest_price: float = 0.0
    pnl_high: float = 0.0
    bars_held: int = 0
    days_held: int = 0
    total_cost: float = 0.0
    total_qty: int = 0
    remaining_ratio: float = 1.0
    last_trade_date: date | None = None
    execution_counts: dict[int, int] = field(default_factory=dict)
    func_state: dict[str, Any] = field(default_factory=dict)

    @property
    def is_holding(self) -> bool:
        return self.total_qty > 0

    def record_buy(self, price: float, qty: int, at: datetime | None = None) -> None:
        if not self.is_holding:
            self.entry_time = at or datetime.now()
            self.bars_held = 1  # spec: 진입 사이클 = 1
            self.days_held = 1
            self.last_trade_date = (at or datetime.now()).date()
        self.total_cost += price * qty
        self.total_qty += qty
        self.entry_price = self.total_cost / self.total_qty
        self.highest_price = max(self.highest_price, price)

    def record_sell(self, qty: int) -> None:
        self.total_qty = max(0, self.total_qty - qty)
        if self.total_qty == 0:
            self.reset()

    def reset(self) -> None:
        self.entry_price = 0.0
        self.entry_time = None
        self.highest_price = 0.0
        self.pnl_high = 0.0
        self.bars_held = 0
        self.days_held = 0
        self.total_cost = 0.0
        self.total_qty = 0
        self.remaining_ratio = 1.0
        self.last_trade_date = None
        self.execution_counts.clear()
        self.func_state.clear()

    def update_cycle(self, current_price: float) -> None:
        if not self.is_holding:
            return
        self.bars_held += 1
        self.highest_price = max(self.highest_price, current_price)
        if self.entry_price > 0:
            pnl = (current_price - self.entry_price) / self.entry_price * 100
            self.pnl_high = max(self.pnl_high, pnl)

    def update_day(self, today: date) -> None:
        if not self.is_holding:
            return
        if self.last_trade_date and today > self.last_trade_date:
            self.days_held += 1
            self.last_trade_date = today

    def record_execution(self, rule_index: int) -> None:
        self.execution_counts[rule_index] = self.execution_counts.get(rule_index, 0) + 1

    def get_pnl_pct(self, current_price: float) -> float:
        if self.entry_price <= 0:
            return 0.0
        return (current_price - self.entry_price) / self.entry_price * 100

    def get_drawdown_pct(self, current_price: float) -> float:
        if self.highest_price <= 0:
            return 0.0
        return (current_price - self.highest_price) / self.highest_price * 100

    def to_context(self, current_price: float) -> dict[str, Any]:
        return {
            "수익률": self.get_pnl_pct(current_price),
            "보유수량": self.total_qty,
            "고점 대비": self.get_drawdown_pct(current_price),
            "수익률고점": self.pnl_high,
            "진입가": self.entry_price,
            "보유일": self.days_held,
            "보유봉": self.bars_held,
        }
