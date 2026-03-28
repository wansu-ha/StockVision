"""v2 파서 테스트 — Task 1.1: 토큰 확장."""
import pytest
from sv_core.parsing.lexer import tokenize
from sv_core.parsing.tokens import TokenType


class TestV2Tokens:
    def test_arrow_unicode(self):
        tokens = tokenize("조건 → 매수 100%")
        types = [t.type for t in tokens]
        assert TokenType.ARROW in types

    def test_arrow_ascii(self):
        tokens = tokenize("조건 -> 매도 전량")
        types = [t.type for t in tokens]
        assert TokenType.ARROW in types

    def test_percent(self):
        tokens = tokenize("매수 50%")
        assert tokens[1].type == TokenType.NUMBER
        assert tokens[2].type == TokenType.PERCENT

    def test_brackets(self):
        tokens = tokenize("현재가[1]")
        types = [t.type for t in tokens]
        assert TokenType.LBRACKET in types
        assert TokenType.RBRACKET in types

    def test_keyword_all(self):
        tokens = tokenize("매도 전량")
        assert tokens[1].type == TokenType.KW_ALL

    def test_keyword_rest(self):
        tokens = tokenize("매도 나머지")
        assert tokens[1].type == TokenType.KW_REST

    def test_keyword_between(self):
        tokens = tokenize("수익률 BETWEEN 1 AND 3")
        types = [t.type for t in tokens]
        assert TokenType.KW_BETWEEN in types
