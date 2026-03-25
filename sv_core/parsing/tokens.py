"""DSL 토큰 정의 — grammar.md §3 어휘 규칙 기반."""

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # 리터럴
    NUMBER = auto()
    STRING = auto()    # "5m", "1d" 등 타임프레임 문자열
    BOOL_LIT = auto()  # true, false

    # 식별자
    IDENT = auto()

    # 키워드
    KW_BUY = auto()   # 매수
    KW_SELL = auto()   # 매도
    AND = auto()
    OR = auto()
    NOT = auto()

    # 비교 연산자
    GT = auto()    # >
    GE = auto()    # >=
    LT = auto()    # <
    LE = auto()    # <=
    EQ = auto()    # ==
    NE = auto()    # !=

    # 산술 연산자
    PLUS = auto()   # +
    MINUS = auto()  # -
    STAR = auto()   # *
    SLASH = auto()  # /

    # 구두점
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    COMMA = auto()   # ,
    COLON = auto()   # :
    ASSIGN = auto()  # = (커스텀 함수 정의)

    # 구조
    NEWLINE = auto()
    EOF = auto()


# 키워드 매핑 (IDENT 추출 후 대조)
KEYWORDS: dict[str, TokenType] = {
    "매수": TokenType.KW_BUY,
    "매도": TokenType.KW_SELL,
    "AND": TokenType.AND,
    "OR": TokenType.OR,
    "NOT": TokenType.NOT,
}

# 예약어 (IDENT로 사용 불가)
BOOL_LITERALS: dict[str, bool] = {
    "true": True,
    "false": False,
}


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    value: str
    line: int
    col: int
