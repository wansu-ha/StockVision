"""SignalManager — 신호 상태 관리, 중복 실행 방지.

v2: 매수/매도 독립 상태 + trigger_policy (ONCE, ONCE_PER_DAY) 지원.
상태 머신: IDLE → TRIGGERED → FILLED / FAILED
매일 자정(날짜 변경) 시 ONCE_PER_DAY 상태를 IDLE로 리셋.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Callable

logger = logging.getLogger(__name__)


class SignalManager:
    """신호 상태 머신. 매수/매도 독립, trigger_policy 지원."""

    def __init__(self) -> None:
        self._buy_states: dict[int, str] = {}   # rule_id → state
        self._sell_states: dict[int, str] = {}  # rule_id → state
        self._last_reset: date = date.today()
        # ONCE 정책: 체결 시 규칙 비활성화 콜백
        self._deactivate_callback: Callable[[int], None] | None = None
        logger.warning("SignalManager 초기화 — 인메모리 상태, 재시작 시 당일 중복 실행 가능")

    def set_deactivate_callback(self, callback: Callable[[int], None]) -> None:
        """ONCE 정책: 규칙 비활성화 콜백 등록."""
        self._deactivate_callback = callback

    def can_trigger(self, rule_id: int, side: str) -> bool:
        """실행 가능 여부 확인 (매수/매도 독립)."""
        self._check_daily_reset()
        states = self._buy_states if side == "BUY" else self._sell_states
        return states.get(rule_id, "IDLE") == "IDLE"

    def mark_triggered(self, rule_id: int, side: str) -> None:
        """신호 발생 마킹."""
        states = self._buy_states if side == "BUY" else self._sell_states
        states[rule_id] = "TRIGGERED"
        logger.debug("Rule %d %s → TRIGGERED", rule_id, side)

    def mark_filled(self, rule_id: int, side: str, trigger_policy: dict | None = None) -> None:
        """주문 체결 마킹."""
        states = self._buy_states if side == "BUY" else self._sell_states
        states[rule_id] = "FILLED"
        logger.info("Rule %d %s → FILLED", rule_id, side)

        # ONCE 정책: 1회 체결 → 규칙 비활성화
        policy = trigger_policy or {}
        if policy.get("frequency") == "ONCE" and self._deactivate_callback:
            self._deactivate_callback(rule_id)
            logger.info("Rule %d: ONCE 정책 — 비활성화", rule_id)

    def mark_failed(self, rule_id: int, side: str) -> None:
        """주문 실패 → IDLE 복귀 (재시도 허용)."""
        states = self._buy_states if side == "BUY" else self._sell_states
        states[rule_id] = "IDLE"
        logger.warning("Rule %d %s → FAILED → IDLE", rule_id, side)

    def get_state(self, rule_id: int, side: str) -> str:
        """현재 상태 조회."""
        self._check_daily_reset()
        states = self._buy_states if side == "BUY" else self._sell_states
        return states.get(rule_id, "IDLE")

    def reset_all(self) -> None:
        """모든 규칙 리셋 (테스트용)."""
        self._buy_states.clear()
        self._sell_states.clear()
        self._last_reset = date.today()

    def _check_daily_reset(self) -> None:
        """날짜 변경 시 ONCE_PER_DAY 리셋."""
        today = date.today()
        if today > self._last_reset:
            self._buy_states.clear()
            self._sell_states.clear()
            self._last_reset = today
            logger.info("일일 리셋 완료 (%s)", today)
