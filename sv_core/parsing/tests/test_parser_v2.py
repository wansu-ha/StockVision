"""v2 파서 테스트 — Task 1.1: 토큰 확장, Task 1.2: AST 노드."""
import pytest
from sv_core.parsing.lexer import tokenize
from sv_core.parsing.tokens import TokenType
from sv_core.parsing.ast_nodes import (
    Action, ConstDecl, IndexAccess, Rule, ScriptV2,
    NumberLit, StringLit, FieldRef, FuncCall, Comparison, BinOp,
)


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


class TestV2ASTNodes:
    def test_const_decl_number(self):
        node = ConstDecl(name="기간", value=NumberLit(value=14.0))
        assert node.name == "기간"
        assert node.value.value == 14.0

    def test_const_decl_string(self):
        node = ConstDecl(name="tf", value=StringLit(value="1d"))
        assert node.name == "tf"

    def test_index_access(self):
        node = IndexAccess(expr=FieldRef(name="현재가"), index=1)
        assert node.index == 1

    def test_action_percent(self):
        action = Action(side="매수", qty_type="percent", qty_value=50.0)
        assert action.side == "매수"
        assert action.qty_type == "percent"
        assert action.qty_value == 50.0

    def test_action_all(self):
        action = Action(side="매도", qty_type="all")
        assert action.qty_type == "all"

    def test_rule(self):
        rule = Rule(
            condition=Comparison(op=">", left=FieldRef(name="수익률"), right=NumberLit(value=5.0)),
            action=Action(side="매도", qty_type="all"),
        )
        assert isinstance(rule.condition, Comparison)
        assert rule.action.side == "매도"

    def test_script_v2(self):
        s = ScriptV2(
            consts=(ConstDecl(name="손절", value=NumberLit(value=-2.0)),),
            rules=(Rule(
                condition=FieldRef(name="골든크로스"),
                action=Action(side="매수", qty_type="percent", qty_value=100.0),
            ),),
        )
        assert len(s.consts) == 1
        assert len(s.rules) == 1
