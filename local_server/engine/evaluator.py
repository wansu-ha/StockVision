"""RuleEvaluator — 규칙 조건 평가.

v2: DSL script → sv_core.parsing.evaluate → (buy, sell)
v1: JSON conditions → 기존 AND/OR 평가 → (buy, sell) 폴백
"""
from __future__ import annotations

import hashlib
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from sv_core.parsing import parse, evaluate as dsl_evaluate
from sv_core.parsing.ast_nodes import Script

logger = logging.getLogger(__name__)


class RuleEvaluator:
    """규칙 조건을 현재 데이터로 평가."""

    def __init__(self) -> None:
        # AST 캐시: {rule_id: (script_hash, ast)}
        self._ast_cache: dict[int, tuple[str, Script]] = {}
        # 상향돌파/하향돌파 state: {rule_id: state_dict}
        self._cross_states: dict[int, dict] = {}

    def evaluate(self, rule: dict, market_data: dict, context: dict) -> tuple[bool, bool]:
        """규칙 평가 → (매수 결과, 매도 결과).

        script가 있으면 DSL 경로, 없으면 v1 JSON 폴백.
        """
        script = rule.get("script")
        if script is not None:
            return self._eval_dsl(rule, market_data, context)
        return self._eval_json(rule, market_data, context)

    def invalidate_cache(self, rule_id: int) -> None:
        """규칙 업데이트 시 AST 캐시 무효화."""
        self._ast_cache.pop(rule_id, None)
        self._cross_states.pop(rule_id, None)

    def clear_cache(self) -> None:
        """전체 캐시 초기화."""
        self._ast_cache.clear()
        self._cross_states.clear()

    # ── DSL 경로 ──

    def _eval_dsl(self, rule: dict, market_data: dict, context: dict) -> tuple[bool, bool]:
        """DSL script → AST → evaluate."""
        rule_id = rule.get("id", 0)
        script = rule["script"]

        try:
            ast = self._get_or_parse(rule_id, script)
            eval_ctx = self._build_dsl_context(market_data, context)
            state = self._cross_states.setdefault(rule_id, {})
            return dsl_evaluate(ast, eval_ctx, state)
        except Exception:
            logger.exception("Rule %d DSL 평가 오류", rule_id)
            return (False, False)

    def _get_or_parse(self, rule_id: int, script: str) -> Script:
        """AST 캐시 조회, 미스 시 파싱."""
        script_hash = hashlib.md5(script.encode()).hexdigest()
        cached = self._ast_cache.get(rule_id)
        if cached and cached[0] == script_hash:
            return cached[1]

        ast = parse(script)
        self._ast_cache[rule_id] = (script_hash, ast)
        return ast

    @staticmethod
    def _build_dsl_context(market_data: dict, context: dict) -> dict[str, Any]:
        """market_data + context → DSL evaluator context dict.

        내장 필드 매핑 + 내장 함수 callable 제공.
        """
        price = market_data.get("price")
        volume = market_data.get("volume")
        indicators = market_data.get("indicators", {})

        ctx: dict[str, Any] = {}

        # 내장 필드
        ctx["현재가"] = float(price) if price is not None else None
        ctx["거래량"] = int(volume) if volume is not None else None
        ctx["수익률"] = context.get("수익률")
        ctx["보유수량"] = context.get("보유수량", 0)

        # 내장 함수 — 지표 데이터에서 resolve
        def make_indicator_func(name: str):
            def func(*args):
                key = f"{name}_{int(args[0])}" if args else name
                val = indicators.get(key)
                return float(val) if val is not None else None
            return func

        ctx["RSI"] = make_indicator_func("rsi")
        ctx["MA"] = make_indicator_func("ma")
        ctx["EMA"] = make_indicator_func("ema")
        ctx["평균거래량"] = make_indicator_func("avg_volume")
        ctx["볼린저_상단"] = make_indicator_func("bb_upper")
        ctx["볼린저_하단"] = make_indicator_func("bb_lower")
        ctx["MACD"] = lambda: float(v) if (v := indicators.get("macd")) is not None else None
        ctx["MACD_SIGNAL"] = lambda: float(v) if (v := indicators.get("macd_signal")) is not None else None

        return ctx

    # ── v1 JSON 폴백 ──

    def _eval_json(self, rule: dict, market_data: dict, context: dict) -> tuple[bool, bool]:
        """v1 JSON conditions 평가 → (buy, sell)."""
        buy_conds = rule.get("buy_conditions")
        sell_conds = rule.get("sell_conditions")

        buy = self._eval_conditions(buy_conds, market_data, context) if buy_conds else False
        sell = self._eval_conditions(sell_conds, market_data, context) if sell_conds else False
        return (buy, sell)

    def _eval_conditions(self, conds: dict, market_data: dict, context: dict) -> bool:
        """단일 조건 세트 평가 (v1)."""
        conditions = conds.get("conditions", [])
        if not conditions:
            return False

        op = conds.get("operator", "AND")
        results = [self._eval_single(c, market_data, context) for c in conditions]

        if op == "OR":
            return any(results)
        return all(results)

    def _eval_single(self, condition: dict, market_data: dict, context: dict) -> bool:
        """단일 조건 평가 (v1)."""
        cond_type = condition.get("type", "")
        field_name = condition.get("field", "")

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
            "==": a == b, "!=": a != b,
            "<": a < b, "<=": a <= b,
            ">": a > b, ">=": a >= b,
        }
        return ops.get(operator, False)
