"""SignalManager — 신호 상태 관리, 중복 실행 방지.

규칙당 하루 1회 실행을 보장한다.
상태 머신: IDLE → TRIGGERED → FILLED / FAILED
매일 자정(날짜 변경) 시 모든 상태를 IDLE로 리셋한다.
"""
from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)


class SignalManager:
    """신호 상태 머신. 규칙당 하루 1회 실행 보장."""

    def __init__(self) -> None:
        self._states: dict[int, str] = {}  # rule_id → state
        self._last_reset: date = date.today()
        logger.warning("SignalManager 초기화 — 인메모리 상태, 재시작 시 당일 중복 실행 가능")

    def can_trigger(self, rule_id: int) -> bool:
        """실행 가능 여부 확인."""
        self._check_daily_reset()
        return self._states.get(rule_id, "IDLE") == "IDLE"

    def mark_triggered(self, rule_id: int) -> None:
        """신호 발생 마킹."""
        self._states[rule_id] = "TRIGGERED"
        logger.debug("Rule %d → TRIGGERED", rule_id)

    def mark_filled(self, rule_id: int) -> None:
        """주문 체결 마킹."""
        self._states[rule_id] = "FILLED"
        logger.info("Rule %d → FILLED", rule_id)

    def mark_failed(self, rule_id: int) -> None:
        """주문 실패 마킹."""
        self._states[rule_id] = "FAILED"
        logger.warning("Rule %d → FAILED", rule_id)

    def get_state(self, rule_id: int) -> str:
        """현재 상태 조회."""
        self._check_daily_reset()
        return self._states.get(rule_id, "IDLE")

    def reset_all(self) -> None:
        """모든 규칙 리셋 (테스트용)."""
        self._states.clear()
        self._last_reset = date.today()

    def _check_daily_reset(self) -> None:
        """날짜 변경 시 일일 리셋."""
        today = date.today()
        if today > self._last_reset:
            self._states.clear()
            self._last_reset = today
            logger.info("일일 리셋 완료 (%s)", today)
