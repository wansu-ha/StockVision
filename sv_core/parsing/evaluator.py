"""DSL 평가기 — AST를 시세 컨텍스트에서 평가하여 (매수, 매도) boolean 반환.

context: {"현재가": float, "거래량": int, "RSI": Callable, "MA": Callable, ...}
state: {"cross_prev": {key: (prev_a, prev_b)}} — 엔진이 규칙별로 관리
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .ast_nodes import (
    Action,
    BinOp,
    BoolLit,
    BuyBlock,
    Comparison,
    ConstDecl,
    CustomFuncDef,
    FieldRef,
    FuncCall,
    Node,
    NumberLit,
    Rule,
    Script,
    ScriptV2,
    SellBlock,
    StringLit,
    UnaryOp,
)
from .builtins import (
    BUILTIN_FIELDS,
    BUILTIN_FUNCTIONS,
    BUILTIN_PATTERNS,
    get_pattern_func,
)
from .parser import parse as parse_script


# null 표현 (None = 결측치)
_NULL = None


def evaluate(
    ast: Script,
    context: dict[str, Any],
    state: dict[str, Any] | None = None,
) -> tuple[bool, bool]:
    """AST 평가 → (매수 결과, 매도 결과).

    어느 블록에서든 null 발생 시 해당 블록 전체 = False.
    """
    if state is None:
        state = {}
    if "cross_prev" not in state:
        state["cross_prev"] = {}

    ev = _Evaluator(context, state)

    # 커스텀 함수 선언 순서대로 평가 → 결과 캐시
    for func_def in ast.custom_funcs:
        ev.eval_custom_def(func_def)

    buy_result = ev.eval_block(ast.buy_block)
    sell_result = ev.eval_block(ast.sell_block)

    return (buy_result, sell_result)


class _Evaluator:
    def __init__(self, context: dict[str, Any], state: dict[str, Any]):
        self._ctx = context
        self._state = state
        self._custom_cache: dict[str, Any] = {}  # 커스텀 함수 결과 캐시

    def eval_custom_def(self, func_def: CustomFuncDef):
        """커스텀 함수를 평가하고 결과 캐시."""
        result = self._eval(func_def.body)
        self._custom_cache[func_def.name] = result

    def eval_block(self, block: BuyBlock | SellBlock) -> bool:
        """블록 평가. null 발생 → False."""
        result = self._eval(block.expr)
        if result is _NULL:
            return False
        return bool(result)

    def _eval(self, node: Node) -> Any:
        """AST 노드 재귀 평가. null 전파."""
        if isinstance(node, NumberLit):
            return node.value

        if isinstance(node, BoolLit):
            return node.value

        if isinstance(node, StringLit):
            return node.value

        if isinstance(node, FieldRef):
            return self._resolve_field(node.name)

        if isinstance(node, FuncCall):
            return self._eval_func_call(node)

        if isinstance(node, Comparison):
            return self._eval_comparison(node)

        if isinstance(node, BinOp):
            return self._eval_binop(node)

        if isinstance(node, UnaryOp):
            return self._eval_unary(node)

        return _NULL

    def _resolve_field(self, name: str) -> Any:
        """내장 필드 resolve."""
        val = self._ctx.get(name)
        return val  # None이면 null 전파

    def _eval_func_call(self, node: FuncCall) -> Any:
        name = node.name

        # 1. 커스텀 함수
        if name in self._custom_cache:
            return self._custom_cache[name]

        # 2. 내장 패턴 함수 — 정의를 인라인 파싱+평가
        pat = get_pattern_func(name)
        if pat is not None:
            return self._eval_pattern(pat.definition)

        # 3. 내장 함수
        if name == "상향돌파":
            return self._eval_cross_above(node)
        if name == "하향돌파":
            return self._eval_cross_below(node)
        if name == "강세다이버전스":
            return self._eval_divergence(node, bullish=True)
        if name == "약세다이버전스":
            return self._eval_divergence(node, bullish=False)

        # 일반 내장 함수 — context에서 callable 조회
        func = self._ctx.get(name)
        if func is None:
            return _NULL
        if not callable(func):
            return _NULL

        # 인자 평가
        args = []
        for arg in node.args:
            val = self._eval(arg)
            if val is _NULL:
                return _NULL
            args.append(val)

        try:
            return func(*args)
        except Exception:
            return _NULL

    def _eval_pattern(self, definition: str) -> Any:
        """패턴 함수 정의를 파싱 + 평가.

        패턴 정의는 순수 expression이므로 매수:/매도: 없이 파싱.
        trick: 임시로 "매수: {def}\n매도: true" 래핑.
        """
        wrapped = f"매수: {definition}\n매도: true"
        try:
            ast = parse_script(wrapped)
        except Exception:
            return _NULL
        return self._eval(ast.buy_block.expr)

    def _eval_cross_above(self, node: FuncCall) -> Any:
        """상향돌파(A, B): 직전 A < B 이고 현재 A >= B."""
        if len(node.args) != 2:
            return _NULL
        a = self._eval(node.args[0])
        b = self._eval(node.args[1])
        if a is _NULL or b is _NULL:
            return _NULL

        key = self._cross_key(node)
        prev = self._state["cross_prev"].get(key)
        self._state["cross_prev"][key] = (a, b)

        if prev is None:
            return False  # 첫 평가 → false

        prev_a, prev_b = prev
        if prev_a is _NULL or prev_b is _NULL:
            return False
        return prev_a < prev_b and a >= b

    def _eval_cross_below(self, node: FuncCall) -> Any:
        """하향돌파(A, B): 직전 A > B 이고 현재 A <= B."""
        if len(node.args) != 2:
            return _NULL
        a = self._eval(node.args[0])
        b = self._eval(node.args[1])
        if a is _NULL or b is _NULL:
            return _NULL

        key = self._cross_key(node)
        prev = self._state["cross_prev"].get(key)
        self._state["cross_prev"][key] = (a, b)

        if prev is None:
            return False

        prev_a, prev_b = prev
        if prev_a is _NULL or prev_b is _NULL:
            return False
        return prev_a > prev_b and a <= b

    def _cross_key(self, node: FuncCall) -> str:
        """상향/하향돌파 state 키 — 함수명 + 인자 AST repr."""
        arg_repr = "|".join(repr(a) for a in node.args)
        return f"{node.name}:{arg_repr}"

    # ── 다이버전스 ──

    def _eval_divergence(self, node: FuncCall, *, bullish: bool) -> Any:
        """강세/약세 다이버전스 감지.

        강세: 가격 저점↓ + 지표 저점↑ (하락 모멘텀 소진)
        약세: 가격 고점↑ + 지표 고점↓ (상승 모멘텀 소진)

        state["divergence_hist"]에 (price, indicator) 히스토리를 축적한다.
        """
        if len(node.args) < 1:
            return _NULL

        # 첫 인자: 지표 함수 호출 → 현재 값
        indicator_val = self._eval(node.args[0])
        if indicator_val is _NULL or indicator_val is None:
            return False

        # 두 번째 인자: lookback 기간 (기본 20)
        lookback = 20
        if len(node.args) >= 2:
            lb = self._eval(node.args[1])
            if lb is not _NULL and lb is not None:
                lookback = int(lb)

        # 현재 가격
        price = self._ctx.get("현재가")
        if price is None:
            return False

        # 히스토리 축적
        if "divergence_hist" not in self._state:
            self._state["divergence_hist"] = {}
        key = self._cross_key(node)
        hist = self._state["divergence_hist"].setdefault(key, [])
        hist.append((float(price), float(indicator_val)))
        # lookback 초과분 트리밍
        if len(hist) > lookback:
            self._state["divergence_hist"][key] = hist[-lookback:]
            hist = self._state["divergence_hist"][key]

        if len(hist) < 5:
            return False  # 최소 5봉 필요

        return self._detect_divergence(hist, bullish=bullish)

    @staticmethod
    def _detect_divergence(hist: list[tuple[float, float]], *, bullish: bool) -> bool:
        """히스토리에서 로컬 극값 2개를 찾아 다이버전스 판정."""
        prices = [h[0] for h in hist]
        indicators = [h[1] for h in hist]
        n = len(prices)

        if bullish:
            # 로컬 저점 찾기 (양쪽보다 낮은 점)
            extrema = []
            for i in range(1, n - 1):
                if prices[i] < prices[i - 1] and prices[i] < prices[i + 1]:
                    extrema.append(i)
            if len(extrema) < 2:
                return False
            # 가장 최근 2개
            i1, i2 = extrema[-2], extrema[-1]
            # 가격 저점↓ + 지표 저점↑
            return prices[i2] < prices[i1] and indicators[i2] > indicators[i1]
        else:
            # 로컬 고점 찾기
            extrema = []
            for i in range(1, n - 1):
                if prices[i] > prices[i - 1] and prices[i] > prices[i + 1]:
                    extrema.append(i)
            if len(extrema) < 2:
                return False
            i1, i2 = extrema[-2], extrema[-1]
            # 가격 고점↑ + 지표 고점↓
            return prices[i2] > prices[i1] and indicators[i2] < indicators[i1]

    def _eval_comparison(self, node: Comparison) -> Any:
        left = self._eval(node.left)
        right = self._eval(node.right)
        if left is _NULL or right is _NULL:
            return _NULL
        op = node.op
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        return _NULL

    def _eval_binop(self, node: BinOp) -> Any:
        left = self._eval(node.left)
        right = self._eval(node.right)

        # null 전파 (AND/OR 포함 — 단락 평가 없음, spec §7.4)
        if left is _NULL or right is _NULL:
            return _NULL

        op = node.op
        if op == "AND":
            return bool(left) and bool(right)
        if op == "OR":
            return bool(left) or bool(right)
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            if right == 0:
                return _NULL  # 0 나누기 → null
            return left / right
        return _NULL

    def _eval_unary(self, node: UnaryOp) -> Any:
        val = self._eval(node.operand)
        if val is _NULL:
            return _NULL
        if node.op == "NOT":
            return not bool(val)
        if node.op == "-":
            return -val
        return _NULL


# ── v2 평가기 ──


@dataclass(slots=True)
class ActionResult:
    """실행할 행동."""
    rule_index: int
    side: str           # "매수" | "매도"
    qty_type: str       # "percent" | "all"
    qty_value: float    # percent일 때 0~100
    expr_text: str = ""


@dataclass(slots=True)
class ConditionSnapshot:
    """규칙별 조건 평가 결과."""
    rule_index: int
    result: bool | None   # True/False/None(null)
    details: dict = field(default_factory=dict)


@dataclass(slots=True)
class EvalV2Result:
    """v2 평가 결과."""
    action: ActionResult | None
    snapshots: list[ConditionSnapshot] = field(default_factory=list)


class _EvaluatorV2:
    """v2 AST 평가기.

    _Evaluator를 내부적으로 재사용하여 표현식 평가.
    상태 함수(횟수, 연속)는 별도 처리.
    """

    def __init__(
        self,
        ast: ScriptV2,
        context: dict[str, Any],
        state: dict[str, Any],
    ):
        self._ast = ast
        self._ctx = context
        self._state = state
        self._snapshots: list[ConditionSnapshot] = []

        # 상수를 컨텍스트에 주입
        for const in ast.consts:
            val = self._eval_const_value(const)
            self._ctx[const.name] = val

        # 내부 _Evaluator — 표현식 평가 위임
        self._ev = _Evaluator(self._ctx, self._state)

        # 커스텀 함수 평가
        for func_def in ast.custom_funcs:
            self._ev.eval_custom_def(func_def)

    def _eval_const_value(self, const: ConstDecl) -> Any:
        """상수 값 평가 (NumberLit/StringLit)."""
        node = const.value
        if isinstance(node, NumberLit):
            return node.value
        if isinstance(node, StringLit):
            return node.value
        return _NULL

    def evaluate(self) -> EvalV2Result:
        """모든 규칙 평가 → 우선순위에 따라 최대 1개 행동 선택."""
        triggered: list[tuple[int, Rule]] = []

        for i, rule in enumerate(self._ast.rules):
            result, details = self._eval_condition(rule.condition)
            self._snapshots.append(ConditionSnapshot(
                rule_index=i,
                result=result,
                details=details,
            ))
            if result is True:
                triggered.append((i, rule))

        # 우선순위: 전량매도 > 부분매도 > 매수
        action = self._resolve_priority(triggered)
        return EvalV2Result(action=action, snapshots=self._snapshots)

    def _eval_condition(self, node: Node) -> tuple[bool | None, dict]:
        """조건 평가 → (결과, 세부 필드값).

        상태 함수(횟수, 연속)를 가로채서 처리한 뒤 나머지는 _Evaluator에 위임.
        """
        details: dict = {}
        result = self._eval_with_state_funcs(node, details)
        if result is _NULL:
            return None, details
        return bool(result), details

    def _eval_with_state_funcs(self, node: Node, details: dict) -> Any:
        """상태 함수를 처리하면서 표현식 평가.

        FieldRef / FuncCall 노드에서 details에 현재 값을 기록.
        """
        if isinstance(node, FieldRef):
            val = self._ctx.get(node.name)
            if val is not _NULL and val is not None:
                details[node.name] = val
            return val

        if isinstance(node, FuncCall):
            # 상태 함수 특수 처리
            if node.name == "횟수":
                return self._eval_count_func(node, details)
            if node.name == "연속":
                return self._eval_consecutive_func(node, details)

            # 일반 함수 — _Evaluator에 위임
            val = self._ev._eval(node)
            # 함수 호출 결과를 details에 기록
            func_repr = self._func_repr(node)
            if val is not _NULL and val is not None:
                details[func_repr] = val
            return val

        if isinstance(node, Comparison):
            left = self._eval_with_state_funcs(node.left, details)
            right = self._eval_with_state_funcs(node.right, details)
            if left is _NULL or right is _NULL:
                return _NULL
            op = node.op
            if op == ">":
                return left > right
            if op == ">=":
                return left >= right
            if op == "<":
                return left < right
            if op == "<=":
                return left <= right
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            return _NULL

        if isinstance(node, BinOp):
            left = self._eval_with_state_funcs(node.left, details)
            right = self._eval_with_state_funcs(node.right, details)
            if left is _NULL or right is _NULL:
                return _NULL
            op = node.op
            if op == "AND":
                return bool(left) and bool(right)
            if op == "OR":
                return bool(left) or bool(right)
            # 산술은 _Evaluator에 위임
            return self._ev._eval(node)

        if isinstance(node, UnaryOp):
            val = self._eval_with_state_funcs(node.operand, details)
            if val is _NULL:
                return _NULL
            if node.op == "NOT":
                return not bool(val)
            if node.op == "-":
                return -val
            return _NULL

        # 그 외 (NumberLit, BoolLit, StringLit 등) — _Evaluator에 위임
        return self._ev._eval(node)

    def _eval_count_func(self, node: FuncCall, details: dict) -> Any:
        """횟수(조건, 기간) — 기간 내 조건 True 봉 수."""
        if len(node.args) != 2:
            return _NULL

        # 조건은 AST 노드 — 매 사이클 평가
        cond_node = node.args[0]
        period_val = self._ev._eval(node.args[1])
        if period_val is _NULL:
            return _NULL
        period = int(period_val)

        # 조건 평가
        cond_result = self._ev._eval(cond_node)
        cond_bool = bool(cond_result) if cond_result is not _NULL else False

        # state key
        key = f"count:{self._node_repr(cond_node)}"
        history = self._state.setdefault("count_history", {})
        hist_list: list[bool] = history.setdefault(key, [])
        hist_list.append(cond_bool)

        # 윈도우 초과분 트리밍 (메모리 누수 방지)
        if period > 0 and len(hist_list) > period:
            history[key] = hist_list[-period:]
            hist_list = history[key]

        # 윈도우 내 True 수
        window = hist_list[-period:] if period > 0 else []
        result = sum(1 for v in window if v)

        func_repr = f"횟수({self._node_repr(cond_node)}, {period})"
        details[func_repr] = result
        return result

    def _eval_consecutive_func(self, node: FuncCall, details: dict) -> Any:
        """연속(조건) — 현재 연속 True 봉 수."""
        if len(node.args) != 1:
            return _NULL

        cond_node = node.args[0]
        cond_result = self._ev._eval(cond_node)
        cond_bool = bool(cond_result) if cond_result is not _NULL else False

        key = f"consecutive:{self._node_repr(cond_node)}"
        consec = self._state.setdefault("consecutive", {})

        if cond_bool:
            consec[key] = consec.get(key, 0) + 1
        else:
            consec[key] = 0

        result = consec[key]
        func_repr = f"연속({self._node_repr(cond_node)})"
        details[func_repr] = result
        return result

    def _resolve_priority(
        self,
        triggered: list[tuple[int, Rule]],
    ) -> ActionResult | None:
        """우선순위: 전량매도 > 부분매도 > 매수."""
        full_sell: ActionResult | None = None
        partial_sell: ActionResult | None = None
        buy: ActionResult | None = None

        for idx, rule in triggered:
            act = rule.action
            ar = ActionResult(
                rule_index=idx,
                side=act.side,
                qty_type=act.qty_type,
                qty_value=act.qty_value,
            )
            if act.side == "매도" and act.qty_type == "all" and full_sell is None:
                full_sell = ar
            elif act.side == "매도" and act.qty_type == "percent" and partial_sell is None:
                partial_sell = ar
            elif act.side == "매수" and buy is None:
                buy = ar

        if full_sell is not None:
            return full_sell
        if partial_sell is not None:
            return partial_sell
        return buy

    @staticmethod
    def _func_repr(node: FuncCall) -> str:
        """함수 호출의 문자열 표현."""
        args = ", ".join(_EvaluatorV2._node_repr(a) for a in node.args)
        return f"{node.name}({args})" if args else f"{node.name}()"

    @staticmethod
    def _node_repr(node: Node) -> str:
        """AST 노드의 간략 문자열 표현 (state key 용)."""
        if isinstance(node, NumberLit):
            v = node.value
            return str(int(v)) if v == int(v) else str(v)
        if isinstance(node, BoolLit):
            return "true" if node.value else "false"
        if isinstance(node, StringLit):
            return f'"{node.value}"'
        if isinstance(node, FieldRef):
            return node.name
        if isinstance(node, FuncCall):
            return _EvaluatorV2._func_repr(node)
        if isinstance(node, Comparison):
            l = _EvaluatorV2._node_repr(node.left)
            r = _EvaluatorV2._node_repr(node.right)
            return f"{l} {node.op} {r}"
        if isinstance(node, BinOp):
            l = _EvaluatorV2._node_repr(node.left)
            r = _EvaluatorV2._node_repr(node.right)
            return f"{l} {node.op} {r}"
        if isinstance(node, UnaryOp):
            o = _EvaluatorV2._node_repr(node.operand)
            return f"{node.op} {o}"
        return repr(node)


def evaluate_v2(
    ast: ScriptV2,
    context: dict[str, Any],
    state: dict[str, Any] | None = None,
) -> EvalV2Result:
    """v2 AST 평가 → EvalV2Result.

    모든 규칙을 평가(투명성)하고, 우선순위에 따라 최대 1개 행동 반환.
    """
    if state is None:
        state = {}
    if "cross_prev" not in state:
        state["cross_prev"] = {}

    ev = _EvaluatorV2(ast, dict(context), state)
    return ev.evaluate()
