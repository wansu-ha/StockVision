"""렉서 단위 테스트."""

import pytest

from sv_core.parsing.lexer import tokenize
from sv_core.parsing.tokens import TokenType
from sv_core.parsing.errors import DSLSyntaxError


def _types(source: str) -> list[TokenType]:
    """토큰 타입 리스트 (NEWLINE, EOF 제외)."""
    return [t.type for t in tokenize(source) if t.type not in (TokenType.NEWLINE, TokenType.EOF)]


def _values(source: str) -> list[str]:
    """토큰 값 리스트 (NEWLINE, EOF 제외)."""
    return [t.value for t in tokenize(source) if t.type not in (TokenType.NEWLINE, TokenType.EOF)]


class TestBasicTokens:
    def test_number_integer(self):
        assert _types("42") == [TokenType.NUMBER]
        assert _values("42") == ["42"]

    def test_number_float(self):
        assert _values("3.14") == ["3.14"]

    def test_keywords(self):
        assert _types("매수 매도 AND OR NOT") == [
            TokenType.KW_BUY, TokenType.KW_SELL, TokenType.AND, TokenType.OR, TokenType.NOT,
        ]

    def test_bool_literals(self):
        assert _types("true false") == [TokenType.BOOL_LIT, TokenType.BOOL_LIT]

    def test_identifiers_korean(self):
        assert _types("현재가") == [TokenType.IDENT]
        assert _values("현재가") == ["현재가"]

    def test_identifiers_mixed(self):
        assert _values("RSI 과매도 MA_20") == ["RSI", "과매도", "MA_20"]


class TestOperators:
    def test_comparison_two_char(self):
        """최장 일치: >= > >."""
        assert _types(">= <= == !=") == [TokenType.GE, TokenType.LE, TokenType.EQ, TokenType.NE]

    def test_comparison_one_char(self):
        assert _types("> <") == [TokenType.GT, TokenType.LT]

    def test_arithmetic(self):
        assert _types("+ - * /") == [TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH]

    def test_assign_vs_eq(self):
        """= (할당) vs == (비교) 구분."""
        assert _types("= ==") == [TokenType.ASSIGN, TokenType.EQ]

    def test_punctuation(self):
        assert _types("( ) , :") == [TokenType.LPAREN, TokenType.RPAREN, TokenType.COMMA, TokenType.COLON]


class TestComments:
    def test_comment_ignored(self):
        tokens = tokenize("-- 이것은 주석\n매수")
        types = [t.type for t in tokens if t.type != TokenType.NEWLINE]
        assert types == [TokenType.KW_BUY, TokenType.EOF]

    def test_comment_at_eof(self):
        tokens = tokenize("매수\n-- 마지막 주석")
        types = [t.type for t in tokens if t.type != TokenType.NEWLINE]
        assert types == [TokenType.KW_BUY, TokenType.EOF]


class TestPositions:
    def test_line_col_tracking(self):
        tokens = tokenize("매수: true\n매도: false")
        buy = tokens[0]
        assert buy.line == 1 and buy.col == 1
        sell = [t for t in tokens if t.type == TokenType.KW_SELL][0]
        assert sell.line == 2 and sell.col == 1


class TestKeywordVsIdent:
    def test_keyword_prefix_is_ident(self):
        """'매수가' → IDENT (최장 일치로 '매수' + '가'가 아닌 '매수가' 전체)."""
        assert _types("매수가") == [TokenType.IDENT]
        assert _values("매수가") == ["매수가"]


class TestErrors:
    def test_unexpected_char(self):
        with pytest.raises(DSLSyntaxError, match="예상치 못한 문자"):
            tokenize("매수 @ 값")

    def test_dot_without_digits(self):
        with pytest.raises(DSLSyntaxError, match="소수점"):
            tokenize("3.")


class TestFullScript:
    def test_spec_example(self):
        """spec §2.3 예시 스크립트 토큰화."""
        source = (
            "-- 골든크로스 + 과매도\n"
            "과매도() = RSI(14) <= 30\n"
            "매수: 골든크로스() AND 과매도()\n"
            "매도: RSI(14) >= 70\n"
        )
        tokens = tokenize(source)
        # 주석이 무시되었는지 확인
        assert all(t.value != "--" for t in tokens)
        # EOF로 끝나는지
        assert tokens[-1].type == TokenType.EOF
