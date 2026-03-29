"""내장 필드/함수/패턴 함수 레지스트리 — spec §2.2, §3 기반."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ast_nodes import Node


# ── 내장 필드 (괄호 없음, 현재 시세 컨텍스트에서 resolve) ──

BUILTIN_FIELDS: set[str] = {
    # 기존
    "현재가",
    "거래량",
    "수익률",
    "보유수량",
    # v2 포지션 필드
    "고점 대비",     # 보유 중 최고가 대비 하락률%
    "수익률고점",     # 보유 중 최고 수익률%
    "진입가",        # 평균 진입 단가
    "보유일",        # 영업일 수
    "보유봉",        # 봉 수
    # v2 시간 필드
    "시간",          # 현재 시각 HHMM (정수)
    "장시작후",       # 장 시작 후 경과 분
    "요일",          # 1=월 ~ 5=금
    # v2 상태 필드
    "실행횟수",       # 이 규칙의 현재 포지션 내 실행 횟수
    # v2 시세 필드
    "등락률",         # 전일 대비 등락률 %
}

# 복합 필드 (공백 포함) — 파서에서 lookahead 결합 시 사용
COMPOUND_FIELDS: dict[str, str] = {
    "고점": "고점 대비",  # "고점" + "대비" → "고점 대비"
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
    "MACD_HIST": BuiltinFuncSpec("MACD_HIST", 0, 3, "number"),
    "볼린저_상단": BuiltinFuncSpec("볼린저_상단", 1, 2, "number"),
    "볼린저_하단": BuiltinFuncSpec("볼린저_하단", 1, 2, "number"),
    "평균거래량": BuiltinFuncSpec("평균거래량", 1, 2, "number"),
    # 스토캐스틱
    "STOCH_K": BuiltinFuncSpec("STOCH_K", 0, 2, "number"),
    "STOCH_D": BuiltinFuncSpec("STOCH_D", 0, 3, "number"),
    # 크로스오버: 인자 고정
    "상향돌파": BuiltinFuncSpec("상향돌파", 2, 2, "boolean"),
    "하향돌파": BuiltinFuncSpec("하향돌파", 2, 2, "boolean"),
    # v2 지표 함수
    "ATR": BuiltinFuncSpec("ATR", 1, 2, "number"),
    "최고가": BuiltinFuncSpec("최고가", 1, 2, "number"),
    "최저가": BuiltinFuncSpec("최저가", 1, 2, "number"),
    "이격도": BuiltinFuncSpec("이격도", 1, 2, "number"),
    # v2 상태 함수
    "횟수": BuiltinFuncSpec("횟수", 2, 2, "number"),
    "연속": BuiltinFuncSpec("연속", 1, 1, "number"),
    # 다이버전스 감지
    "강세다이버전스": BuiltinFuncSpec("강세다이버전스", 1, 2, "boolean"),
    "약세다이버전스": BuiltinFuncSpec("약세다이버전스", 1, 2, "boolean"),
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


def to_schema() -> dict:
    """DSL 스키마를 JSON 직렬화 가능한 dict로 반환."""
    import hashlib
    import json

    functions = {
        name: {
            "min_args": spec.param_min,
            "max_args": spec.param_max,
            "return_type": spec.return_type,
        }
        for name, spec in BUILTIN_FUNCTIONS.items()
    }
    patterns = {
        name: {"definition": spec.definition}
        for name, spec in BUILTIN_PATTERNS.items()
    }

    # fields + functions + patterns 내용 기반 해시
    content = json.dumps(
        {"fields": sorted(BUILTIN_FIELDS), "functions": functions, "patterns": patterns},
        sort_keys=True,
        ensure_ascii=False,
    )
    version = hashlib.md5(content.encode()).hexdigest()

    return {
        "version": version,
        "fields": sorted(BUILTIN_FIELDS),
        "compound_fields": COMPOUND_FIELDS,
        "functions": functions,
        "patterns": patterns,
    }
