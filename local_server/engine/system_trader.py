"""SystemTrader — 포트폴리오 수준 매매 판단.

개별 규칙 평가 후보(CandidateSignal)를 모아서
포지션 제한, 예산, 중복 종목 등 포트폴리오 제약을 적용한 뒤
실제 실행할 신호만 선택한다.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from local_server.engine.trader_models import (
    BlockReason,
    CandidateSignal,
    TradeDecisionBatch,
)

logger = logging.getLogger(__name__)


class SystemTrader:
    """포트폴리오 제약 기반 매매 판단."""

    def __init__(
        self,
        max_positions: int = 5,
        budget_ratio: Decimal = Decimal("0.1"),
    ) -> None:
        self._max_positions = max_positions
        self._budget_ratio = budget_ratio

    def process_cycle(
        self,
        cycle_id: str,
        candidates: list[CandidateSignal],
        current_positions: set[str],
        cash: Decimal,
        today_executed: Decimal,
    ) -> TradeDecisionBatch:
        """후보 목록을 포트폴리오 제약으로 필터링.

        Args:
            cycle_id: 사이클 식별자
            candidates: priority 내림차순 정렬된 후보 목록
            current_positions: 현재 보유 종목 set
            cash: 현재 현금 잔고
            today_executed: 오늘 누적 체결 금액

        Returns:
            TradeDecisionBatch (선택 + 차단)
        """
        batch = TradeDecisionBatch(cycle_id=cycle_id)

        # priority 내림차순 정렬 (호출 전 정렬되었더라도 보장)
        sorted_candidates = sorted(candidates, key=lambda c: c.priority, reverse=True)

        # 이번 사이클에서 선택된 BUY 종목 추적
        selected_buy_symbols: set[str] = set()
        # 이번 사이클에서 추가된 포지션 수
        added_positions = 0
        # 이번 사이클 누적 예산
        cycle_budget = today_executed

        max_daily = cash * self._budget_ratio

        for candidate in sorted_candidates:
            if candidate.side == "BUY":
                reason = self._check_buy(
                    candidate,
                    current_positions,
                    selected_buy_symbols,
                    added_positions,
                    cycle_budget,
                    max_daily,
                )
                if reason is not None:
                    batch.dropped.append((candidate, reason))
                    continue

                batch.selected.append(candidate)
                selected_buy_symbols.add(candidate.symbol)
                added_positions += 1
                cycle_budget += Decimal(str(candidate.latest_price)) * candidate.desired_qty

            elif candidate.side == "SELL":
                if candidate.symbol not in current_positions:
                    batch.dropped.append((candidate, BlockReason.SELL_NO_HOLDING))
                    continue
                batch.selected.append(candidate)

        return batch

    def _check_buy(
        self,
        candidate: CandidateSignal,
        current_positions: set[str],
        selected_buy_symbols: set[str],
        added_positions: int,
        cycle_budget: Decimal,
        max_daily: Decimal,
    ) -> BlockReason | None:
        """BUY 후보 차단 조건 체크. None이면 통과."""
        # 중복 종목 (이미 보유 또는 이번 사이클에서 선택됨)
        if candidate.symbol in current_positions or candidate.symbol in selected_buy_symbols:
            return BlockReason.DUPLICATE_SYMBOL

        # 최대 포지션 수 초과
        total_positions = len(current_positions) + added_positions
        if total_positions >= self._max_positions:
            return BlockReason.MAX_POSITIONS

        # 일일 예산 초과
        order_amount = Decimal(str(candidate.latest_price)) * candidate.desired_qty
        if cycle_budget + order_amount > max_daily:
            return BlockReason.DAILY_BUDGET_EXCEEDED

        return None
