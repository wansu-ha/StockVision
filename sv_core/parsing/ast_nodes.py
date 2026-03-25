"""DSL AST 노드 — grammar.md §2 구문 규칙 기반."""

from __future__ import annotations

from dataclasses import dataclass, field


# ── 기반 노드 ──

@dataclass(frozen=True, slots=True)
class Node:
    """AST 노드 기반 클래스. line/col은 소스 위치."""
    line: int = 0
    col: int = 0


# ── 식 (Expression) 노드 ──

@dataclass(frozen=True, slots=True)
class NumberLit(Node):
    value: float = 0.0


@dataclass(frozen=True, slots=True)
class BoolLit(Node):
    value: bool = False


@dataclass(frozen=True, slots=True)
class StringLit(Node):
    """문자열 리터럴 — 타임프레임 지정자 등."""
    value: str = ""


@dataclass(frozen=True, slots=True)
class FieldRef(Node):
    """내장 필드 참조 (현재가, 거래량 등)."""
    name: str = ""


@dataclass(frozen=True, slots=True)
class FuncCall(Node):
    """함수 호출 (RSI(14), 골든크로스(), 과매도() 등)."""
    name: str = ""
    args: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class BinOp(Node):
    """이항 연산 (AND, OR, +, -, *, /)."""
    op: str = ""
    left: Node = field(default_factory=Node)
    right: Node = field(default_factory=Node)


@dataclass(frozen=True, slots=True)
class UnaryOp(Node):
    """단항 연산 (NOT, 단항 -)."""
    op: str = ""
    operand: Node = field(default_factory=Node)


@dataclass(frozen=True, slots=True)
class Comparison(Node):
    """비교 연산 (>, >=, <, <=, ==, !=). 체이닝 금지."""
    op: str = ""
    left: Node = field(default_factory=Node)
    right: Node = field(default_factory=Node)


# ── 최상위 구조 ──

@dataclass(frozen=True, slots=True)
class CustomFuncDef(Node):
    """커스텀 함수 정의: 이름() = 식."""
    name: str = ""
    body: Node = field(default_factory=Node)


@dataclass(frozen=True, slots=True)
class BuyBlock(Node):
    """매수: 식."""
    expr: Node = field(default_factory=Node)


@dataclass(frozen=True, slots=True)
class SellBlock(Node):
    """매도: 식."""
    expr: Node = field(default_factory=Node)


@dataclass(frozen=True, slots=True)
class Script(Node):
    """최상위 AST — 커스텀 함수 정의 목록 + 매수/매도 블록."""
    custom_funcs: tuple[CustomFuncDef, ...] = ()
    buy_block: BuyBlock = field(default_factory=BuyBlock)
    sell_block: SellBlock = field(default_factory=SellBlock)
