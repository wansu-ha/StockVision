"""내장 필드/함수/패턴 함수 레지스트리 — spec §2.2, §3 기반."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ast_nodes import Node


# ── 내장 필드 (괄호 없음, 현재 시세 컨텍스트에서 resolve) ──

BUILTIN_FIELDS: set[str] = {
    "현재가",
    "거래량",
    "수익률",
    "보유수량",
}

# ── 내장 함수 (괄호 필수, 인자 있음) ──

@dataclass(frozen=True, slots=True)
class BuiltinFuncSpec:
    """내장 함수 명세.

    param_min/param_max: 인자 수 범위.
    모든 지표 함수는 마지막 인자로 타임프레임 문자열("5m", "1d" 등)을
    선택적으로 받을 수 있다.
    """
    name: str
    param_min: int
    param_max: int  # -1 = 가변
    return_type: str  # "number" | "boolean"


BUILTIN_FUNCTIONS: dict[str, BuiltinFuncSpec] = {
    # 지표 함수: 기존 인자 + 선택적 타임프레임
    "RSI": BuiltinFuncSpec("RSI", 1, 2, "number"),
    "MA": BuiltinFuncSpec("MA", 1, 2, "number"),
    "EMA": BuiltinFuncSpec("EMA", 1, 2, "number"),
    "MACD": BuiltinFuncSpec("MACD", 0, 1, "number"),
    "MACD_SIGNAL": BuiltinFuncSpec("MACD_SIGNAL", 0, 1, "number"),
    "볼린저_상단": BuiltinFuncSpec("볼린저_상단", 1, 2, "number"),
    "볼린저_하단": BuiltinFuncSpec("볼린저_하단", 1, 2, "number"),
    "평균거래량": BuiltinFuncSpec("평균거래량", 1, 2, "number"),
    # 크로스오버: 인자 고정
    "상향돌파": BuiltinFuncSpec("상향돌파", 2, 2, "boolean"),
    "하향돌파": BuiltinFuncSpec("하향돌파", 2, 2, "boolean"),
}

# ── 내장 패턴 함수 (괄호 필수, 인자 없음 — spec §3) ──

@dataclass(frozen=True, slots=True)
class PatternFuncSpec:
    """내장 패턴 함수 — DSL 정의 문자열로 평가기에서 인라인 전개."""
    name: str
    definition: str  # DSL 표현식 (매수:/매도: 없는 순수 식)


BUILTIN_PATTERNS: dict[str, PatternFuncSpec] = {
    "골든크로스": PatternFuncSpec("골든크로스", "상향돌파(MA(5), MA(20))"),
    "데드크로스": PatternFuncSpec("데드크로스", "하향돌파(MA(5), MA(20))"),
    "RSI과매도": PatternFuncSpec("RSI과매도", "RSI(14) <= 30"),
    "RSI과매수": PatternFuncSpec("RSI과매수", "RSI(14) >= 70"),
    "볼린저하단돌파": PatternFuncSpec("볼린저하단돌파", "현재가 <= 볼린저_하단(20)"),
    "볼린저상단돌파": PatternFuncSpec("볼린저상단돌파", "현재가 >= 볼린저_상단(20)"),
    "MACD골든크로스": PatternFuncSpec("MACD골든크로스", "상향돌파(MACD(), MACD_SIGNAL())"),
    "MACD데드크로스": PatternFuncSpec("MACD데드크로스", "하향돌파(MACD(), MACD_SIGNAL())"),
}

# ── 조회 유틸 ──

def is_builtin_field(name: str) -> bool:
    return name in BUILTIN_FIELDS


def get_builtin_func(name: str) -> BuiltinFuncSpec | None:
    return BUILTIN_FUNCTIONS.get(name)


def get_pattern_func(name: str) -> PatternFuncSpec | None:
    return BUILTIN_PATTERNS.get(name)


def is_builtin_name(name: str) -> bool:
    """내장 필드/함수/패턴 중 하나인지."""
    return name in BUILTIN_FIELDS or name in BUILTIN_FUNCTIONS or name in BUILTIN_PATTERNS
