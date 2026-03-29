"""RuleEvaluator — 규칙 조건 평가.

v2: DSL script → sv_core.parsing.evaluate → (buy, sell)
v1: JSON conditions → 기존 AND/OR 평가 → (buy, sell) 폴백
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sv_core.parsing import parse, evaluate as dsl_evaluate
from sv_core.parsing import parse_v2, evaluate_v2 as _eval_v2, EvalV2Result
from sv_core.parsing.ast_nodes import Script, ScriptV2

logger = logging.getLogger(__name__)


class RuleEvaluator:
    """규칙 조건을 현재 데이터로 평가."""

    def __init__(self) -> None:
        # AST 캐시: {rule_id: (script_hash, ast)}
        self._ast_cache: dict[int, tuple[str, Script]] = {}
        # v2 AST 캐시: {rule_id: (script_hash, ast)}
        self._v2_ast_cache: dict[int, tuple[str, ScriptV2]] = {}
        # 상향돌파/하향돌파 state: {rule_id: state_dict}
        self._cross_states: dict[int, dict] = {}
        # v2 평가 state: {rule_id: state_dict}
        self._v2_states: dict[int, dict] = {}

    def evaluate(self, rule: dict, market_data: dict, context: dict) -> tuple[bool, bool]:
        """규칙 평가 → (매수 결과, 매도 결과).

        script가 있으면 DSL 경로, 없으면 v1 JSON 폴백.
        """
        script = rule.get("script")
        if script is not None:
            return self._eval_dsl(rule, market_data, context)
        return self._eval_json(rule, market_data, context)

    def evaluate_v2(
        self, rule: dict, market_data: dict, context: dict,
    ) -> EvalV2Result:
        """v2 DSL 평가 → EvalV2Result.

        v2 script를 파싱하고 evaluate_v2를 호출한다.
        v1 스크립트(매수:/매도:)도 parse_v2가 호환 처리한다.
        """
        rule_id = rule.get("id", 0)
        script = rule.get("script", "")

        try:
            ast = self._get_or_parse_v2(rule_id, script)
            eval_ctx = self._build_dsl_context(market_data, context)
            state = self._v2_states.setdefault(rule_id, {})
            return _eval_v2(ast, eval_ctx, state)
        except Exception:
            logger.exception("Rule %d v2 평가 오류", rule_id)
            return EvalV2Result(action=None)

    def invalidate_cache(self, rule_id: int) -> None:
        """규칙 업데이트 시 AST 캐시 무효화."""
        self._ast_cache.pop(rule_id, None)
        self._v2_ast_cache.pop(rule_id, None)
        self._cross_states.pop(rule_id, None)
        self._v2_states.pop(rule_id, None)

    def clear_cache(self) -> None:
        """전체 캐시 초기화."""
        self._ast_cache.clear()
        self._v2_ast_cache.clear()
        self._cross_states.clear()
        self._v2_states.clear()

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

    def _get_or_parse_v2(self, rule_id: int, script: str) -> ScriptV2:
        """v2 AST 캐시 조회, 미스 시 파싱."""
        script_hash = hashlib.md5(script.encode()).hexdigest()
        cached = self._v2_ast_cache.get(rule_id)
        if cached and cached[0] == script_hash:
            return cached[1]

        ast = parse_v2(script)
        self._v2_ast_cache[rule_id] = (script_hash, ast)
        return ast

    @staticmethod
    def is_v2_script(script: str) -> bool:
        """v2 스크립트 여부 판별.

        → 또는 -> 가 포함되면 v2. 매수:/매도: 만 있는 v1도
        parse_v2가 호환 처리하므로 True 반환.
        """
        if not script:
            return False
        # v2 화살표 문법
        if "→" in script or "->" in script:
            return True
        # v1 형식도 parse_v2가 호환 처리
        if "매수:" in script or "매도:" in script:
            return True
        return False

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

        # v2 포지션 필드 (PositionState.to_context() 호환)
        for key in ("고점 대비", "수익률고점", "진입가", "보유일", "보유봉"):
            if key in context:
                ctx[key] = context[key]

        # 시간 필드 — 현재 시각 기반
        now = datetime.now()
        ctx["시간"] = now.hour * 100 + now.minute
        market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
        ctx["장시작후"] = max(0, int((now - market_open).total_seconds() / 60))
        ctx["요일"] = now.isoweekday()

        # 내장 함수 — 지표 데이터에서 resolve
        # indicators는 {tf: {key: val}} 구조.
        # tf=None → "1d" (일봉), tf="5m" 등 → 해당 분봉 dict.
        # 해당 tf 캐시가 없으면 None 반환.
        def make_indicator_func(name: str):
            def func(period, tf=None):
                resolved_tf = tf or "1d"
                tf_dict = indicators.get(resolved_tf)
                if tf_dict is None:
                    return None
                key = f"{name}_{int(period)}"
                val = tf_dict.get(key)
                return float(val) if val is not None else None
            return func

        ctx["RSI"] = make_indicator_func("rsi")
        ctx["MA"] = make_indicator_func("ma")
        ctx["EMA"] = make_indicator_func("ema")
        ctx["평균거래량"] = make_indicator_func("avg_volume")
        ctx["볼린저_상단"] = make_indicator_func("bb_upper")
        ctx["볼린저_하단"] = make_indicator_func("bb_lower")

        def _macd(tf=None):
            resolved_tf = tf or "1d"
            tf_dict = indicators.get(resolved_tf)
            if tf_dict is None:
                return None
            v = tf_dict.get("macd")
            return float(v) if v is not None else None

        def _macd_signal(tf=None):
            resolved_tf = tf or "1d"
            tf_dict = indicators.get(resolved_tf)
            if tf_dict is None:
                return None
            v = tf_dict.get("macd_signal")
            return float(v) if v is not None else None

        ctx["MACD"] = _macd
        ctx["MACD_SIGNAL"] = _macd_signal

        def _macd_hist(tf=None):
            resolved_tf = tf or "1d"
            tf_dict = indicators.get(resolved_tf)
            if tf_dict is None:
                return None
            v = tf_dict.get("macd_hist")
            return float(v) if v is not None else None

        ctx["MACD_HIST"] = _macd_hist

        def _stoch_k(k_period=5, slowing=3, tf=None):
            resolved_tf = tf or "1d"
            tf_dict = indicators.get(resolved_tf)
            if tf_dict is None:
                return None
            key = f"stoch_k_{int(k_period)}_{int(slowing)}"
            val = tf_dict.get(key)
            return float(val) if val is not None else None

        def _stoch_d(k_period=5, slowing=3, d_period=3, tf=None):
            resolved_tf = tf or "1d"
            tf_dict = indicators.get(resolved_tf)
            if tf_dict is None:
                return None
            key = f"stoch_d_{int(k_period)}_{int(slowing)}_{int(d_period)}"
            val = tf_dict.get(key)
            return float(val) if val is not None else None

        ctx["STOCH_K"] = _stoch_k
        ctx["STOCH_D"] = _stoch_d

        # 등락률 — 전일 대비 %
        prev_close = market_data.get("prev_close")
        if price is not None and prev_close is not None and prev_close != 0:
            ctx["등락률"] = round((float(price) - float(prev_close)) / float(prev_close) * 100, 2)
        else:
            ctx["등락률"] = None

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
