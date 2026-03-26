"""DSL 렉서 — grammar.md §3 어휘 규칙 기반.

최장 일치, 한국어 식별자, 키워드 판별, 주석 무시.
"""

from __future__ import annotations

from .errors import DSLSyntaxError
from .tokens import BOOL_LITERALS, KEYWORDS, Token, TokenType


def tokenize(source: str) -> list[Token]:
    """소스 문자열을 Token 리스트로 변환."""
    tokens: list[Token] = []
    pos = 0
    line = 1
    col = 1
    length = len(source)

    while pos < length:
        ch = source[pos]

        # 공백/탭 — 무시 (NEWLINE 제외)
        if ch in (" ", "\t"):
            pos += 1
            col += 1
            continue

        # 줄바꿈
        if ch == "\n":
            tokens.append(Token(TokenType.NEWLINE, "\\n", line, col))
            pos += 1
            line += 1
            col = 1
            continue
        if ch == "\r":
            tokens.append(Token(TokenType.NEWLINE, "\\n", line, col))
            pos += 1
            if pos < length and source[pos] == "\n":
                pos += 1
            line += 1
            col = 1
            continue

        # 주석 — `--` 행 끝까지 무시
        if ch == "-" and pos + 1 < length and source[pos + 1] == "-":
            while pos < length and source[pos] not in ("\n", "\r"):
                pos += 1
            continue

        # 문자열 리터럴 — "..." (타임프레임 등)
        if ch == '"':
            start = pos
            start_col = col
            pos += 1
            col += 1
            while pos < length and source[pos] != '"':
                if source[pos] in ("\n", "\r"):
                    raise DSLSyntaxError("닫히지 않은 문자열", line, start_col)
                pos += 1
                col += 1
            if pos >= length:
                raise DSLSyntaxError("닫히지 않은 문자열", line, start_col)
            # 닫는 따옴표 건너뛰기
            pos += 1
            col += 1
            value = source[start + 1 : pos - 1]  # 따옴표 제외
            tokens.append(Token(TokenType.STRING, value, line, start_col))
            continue

        # 숫자 리터럴
        if ch.isdigit():
            start = pos
            start_col = col
            while pos < length and source[pos].isdigit():
                pos += 1
                col += 1
            if pos < length and source[pos] == ".":
                pos += 1
                col += 1
                if pos >= length or not source[pos].isdigit():
                    raise DSLSyntaxError(
                        "소수점 뒤에 숫자가 필요합니다", line, start_col,
                    )
                while pos < length and source[pos].isdigit():
                    pos += 1
                    col += 1
            tokens.append(Token(TokenType.NUMBER, source[start:pos], line, start_col))
            continue

        # 식별자/키워드 — 유니코드 문자 또는 _
        if _is_ident_start(ch):
            start = pos
            start_col = col
            while pos < length and _is_ident_cont(source[pos]):
                pos += 1
                col += 1
            word = source[start:pos]

            # bool 리터럴
            if word in BOOL_LITERALS:
                tokens.append(Token(TokenType.BOOL_LIT, word, line, start_col))
            # 키워드
            elif word in KEYWORDS:
                tokens.append(Token(KEYWORDS[word], word, line, start_col))
            # 일반 식별자
            else:
                tokens.append(Token(TokenType.IDENT, word, line, start_col))
            continue

        # 2문자 연산자 (최장 일치)
        if pos + 1 < length:
            two = source[pos : pos + 2]
            tt = _TWO_CHAR_OPS.get(two)
            if tt is not None:
                tokens.append(Token(tt, two, line, col))
                pos += 2
                col += 2
                continue

        # 1문자 연산자/구두점
        tt = _ONE_CHAR_OPS.get(ch)
        if tt is not None:
            tokens.append(Token(tt, ch, line, col))
            pos += 1
            col += 1
            continue

        raise DSLSyntaxError(f"예상치 못한 문자: '{ch}'", line, col)

    tokens.append(Token(TokenType.EOF, "", line, col))
    return tokens


# ── 내부 유틸 ──

_TWO_CHAR_OPS: dict[str, TokenType] = {
    ">=": TokenType.GE,
    "<=": TokenType.LE,
    "==": TokenType.EQ,
    "!=": TokenType.NE,
}

_ONE_CHAR_OPS: dict[str, TokenType] = {
    ">": TokenType.GT,
    "<": TokenType.LT,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    ",": TokenType.COMMA,
    ":": TokenType.COLON,
    "=": TokenType.ASSIGN,
}


def _is_ident_start(ch: str) -> bool:
    """식별자 시작 문자: 유니코드 문자 또는 _."""
    return ch == "_" or ch.isalpha()


def _is_ident_cont(ch: str) -> bool:
    """식별자 이어지는 문자: 유니코드 문자, 숫자, _."""
    return ch == "_" or ch.isalnum()
