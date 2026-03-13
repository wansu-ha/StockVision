"""DSL 평가기 — AST를 시세 컨텍스트에서 평가하여 (매수, 매도) boolean 반환.

context: {"현재가": float, "거래량": int, "RSI": Callable, "MA": Callable, ...}
state: {"cross_prev": {key: (prev_a, prev_b)}} — 엔진이 규칙별로 관리
"""

from __future__ import annotations

from typing import Any, Callable

from .ast_nodes import (
    BinOp,
    BoolLit,
    BuyBlock,
    Comparison,
    CustomFuncDef,
    FieldRef,
    FuncCall,
    Node,
    NumberLit,
    Script,
    SellBlock,
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
