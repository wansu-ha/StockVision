"""RuleEvaluator — 규칙 조건 평가 (AND/OR 논리).

규칙의 conditions 리스트를 현재 시세 데이터와 AI 컨텍스트로 평가하여
True/False를 반환한다.
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)


class RuleEvaluator:
    """규칙 조건을 현재 데이터로 평가."""

    def evaluate(self, rule: dict, market_data: dict, context: dict) -> bool:
        """규칙의 조건을 평가한다.

        Args:
            rule: 규칙 dict (operator, conditions 포함)
            market_data: 시세 데이터 (price, volume, rsi_14, ...)
            context: AI 컨텍스트 (market_kospi_rsi, ...)

        Returns:
            True이면 조건 충족, False면 미충족
        """
        conditions = rule.get("conditions", [])
        if not conditions:
            return False

        op = rule.get("operator", "AND")
        results = [self._eval_single(c, market_data, context) for c in conditions]

        if op == "OR":
            return any(results)
        # 기본 AND
        return all(results)

    def _eval_single(self, condition: dict, market_data: dict, context: dict) -> bool:
        """단일 조건 평가."""
        cond_type = condition.get("type", "")
        field_name = condition.get("field", "")

        # 데이터 소스 선택
        if cond_type in ("price", "indicator", "volume"):
            value = market_data.get(field_name)
        elif cond_type == "context":
            value = context.get(field_name)
        else:
            return False

        if value is None:
            return False

        return self._compare(value, condition.get("operator", ""), condition.get("value"))

    @staticmethod
    def _compare(value: Any, operator: str, expected: Any) -> bool:
        """비교 연산. Decimal 안전."""
        try:
            a = Decimal(str(value))
            b = Decimal(str(expected))
        except (InvalidOperation, TypeError, ValueError):
            return False

        ops: dict[str, bool] = {
            "==": a == b,
            "!=": a != b,
            "<": a < b,
            "<=": a <= b,
            ">": a > b,
            ">=": a >= b,
        }
        return ops.get(operator, False)
