"""v2 파서 테스트 — Task 1.3: v2 파서 구현."""
import pytest
from sv_core.parsing.parser import parse_v2
from sv_core.parsing.lexer import tokenize
from sv_core.parsing.tokens import TokenType
from sv_core.parsing.ast_nodes import (
    Action, ConstDecl, CustomFuncDef, IndexAccess, Rule, ScriptV2,
    NumberLit, StringLit, FieldRef, FuncCall, Comparison, BinOp,
)
from sv_core.parsing.errors import DSLSyntaxError, DSLNameError


# ── Task 1.1/1.2 토큰/AST 노드 테스트 (기존 유지) ──

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


# ── Task 1.3: v2 파서 테스트 ──

class TestV2Parser:
    def test_simple_rule(self):
        ast = parse_v2("RSI(14) < 30 → 매수 100%")
        assert isinstance(ast, ScriptV2)
        assert len(ast.rules) == 1
        rule = ast.rules[0]
        assert rule.action.side == "매수"
        assert rule.action.qty_type == "percent"
        assert rule.action.qty_value == 100.0

    def test_arrow_ascii(self):
        ast = parse_v2("RSI(14) < 30 -> 매수 100%")
        assert len(ast.rules) == 1

    def test_sell_all(self):
        ast = parse_v2("수익률 >= 5 → 매도 전량")
        assert ast.rules[0].action.side == "매도"
        assert ast.rules[0].action.qty_type == "all"

    def test_sell_rest(self):
        ast = parse_v2("고점 대비 <= -1.5 → 매도 나머지")
        assert ast.rules[0].action.qty_type == "all"  # 나머지 = 전량 별칭

    def test_sell_percent(self):
        ast = parse_v2("수익률 >= 3 → 매도 50%")
        assert ast.rules[0].action.qty_type == "percent"
        assert ast.rules[0].action.qty_value == 50.0

    def test_const_number(self):
        ast = parse_v2("기간 = 14\nRSI(기간) < 30 → 매수 100%")
        assert len(ast.consts) == 1
        assert ast.consts[0].name == "기간"
        assert isinstance(ast.consts[0].value, NumberLit)
        assert ast.consts[0].value.value == 14.0

    def test_const_string(self):
        ast = parse_v2('tf = "1d"\nRSI(14) < 30 → 매수 100%')
        assert len(ast.consts) == 1
        assert isinstance(ast.consts[0].value, StringLit)

    def test_custom_func_v2(self):
        """v2 커스텀 함수: 괄호 없는 정의, 괄호 없는 사용."""
        ast = parse_v2("내조건 = RSI(14) < 30\n내조건 → 매수 100%")
        assert len(ast.custom_funcs) == 1
        assert ast.custom_funcs[0].name == "내조건"
        rule_cond = ast.rules[0].condition
        assert isinstance(rule_cond, FuncCall)
        assert rule_cond.name == "내조건"

    def test_custom_func_v1_compat(self):
        """v1 커스텀 함수: 괄호 있는 정의."""
        ast = parse_v2("내조건() = RSI(14) < 30\n내조건() → 매수 100%")
        assert len(ast.custom_funcs) == 1

    def test_index_access(self):
        ast = parse_v2("현재가[1] > 현재가 → 매수 100%")
        cond = ast.rules[0].condition
        assert isinstance(cond, Comparison)
        assert isinstance(cond.left, IndexAccess)
        assert cond.left.index == 1

    def test_index_on_func_call(self):
        ast = parse_v2("RSI(14)[3] < 30 \u2192 \ub9e4\uc218 100%")
        cond = ast.rules[0].condition
        assert isinstance(cond.left, IndexAccess)
        assert cond.left.index == 3
        assert isinstance(cond.left.expr, FuncCall)

    def test_index_max_60(self):
        parse_v2("현재가[60] > 0 → 매수 100%")  # 최대 OK

    def test_index_over_60_error(self):
        with pytest.raises(DSLSyntaxError, match="범위"):
            parse_v2("현재가[61] > 0 → 매수 100%")

    def test_between(self):
        ast = parse_v2("수익률 BETWEEN -1 AND 1 → 매도 전량")
        cond = ast.rules[0].condition
        assert isinstance(cond, BinOp)
        assert cond.op == "AND"

    def test_multiple_rules_order(self):
        src = "수익률 <= -2 → 매도 전량\n수익률 >= 3 → 매도 50%\n고점 대비 <= -1.5 → 매도 나머지\nRSI(14) < 30 → 매수 100%"
        ast = parse_v2(src)
        assert len(ast.rules) == 4
        assert ast.rules[0].action.side == "매도"
        assert ast.rules[3].action.side == "매수"

    def test_no_paren_pattern_func(self):
        """괄호 없는 패턴 함수: 골든크로스 → 매수."""
        ast = parse_v2("골든크로스 → 매수 100%")
        cond = ast.rules[0].condition
        assert isinstance(cond, FuncCall)
        assert cond.name == "골든크로스"

    def test_no_rules_error(self):
        with pytest.raises(DSLSyntaxError, match="규칙"):
            parse_v2("기간 = 14")

    def test_name_resolution_const_over_builtin(self):
        """사용자 상수가 내장 필드보다 우선 (§2.5 rule 7)."""
        ast = parse_v2("수익률 = 5\n수익률 >= 3 → 매도 전량")
        assert len(ast.consts) == 1

    def test_comment_ignored(self):
        src = """-- 주석
기간 = 14
RSI(기간) < 30 → 매수 100%"""
        ast = parse_v2(src)
        assert len(ast.rules) == 1

    def test_multiple_rules(self):
        src = "수익률 <= -2 → 매도 전량\nRSI(14) < 30 → 매수 100%"
        ast = parse_v2(src)
        assert len(ast.rules) == 2


class TestV2Builtins:
    def test_atr_in_rule(self):
        ast = parse_v2("현재가 <= 진입가 - ATR(14) * 2 → 매도 전량")
        assert len(ast.rules) == 1

    def test_highest_lowest(self):
        ast = parse_v2("현재가 >= 최고가(20) → 매도 전량")
        assert len(ast.rules) == 1

    def test_disparity(self):
        ast = parse_v2("이격도(20) < -5 → 매수 100%")
        assert len(ast.rules) == 1

    def test_execution_count_field(self):
        ast = parse_v2("수익률 >= 3 AND 실행횟수 < 1 → 매도 50%")
        assert isinstance(ast.rules[0].condition, BinOp)

    def test_count_func(self):
        ast = parse_v2("횟수(수익률 >= 2, 보유봉) >= 1 → 매도 전량")
        assert len(ast.rules) == 1

    def test_consecutive_func(self):
        ast = parse_v2("연속(RSI(14) < 30) >= 3 → 매수 100%")
        assert len(ast.rules) == 1


class TestIndicatorCalc:
    def test_calc_atr(self):
        from sv_core.indicators.calculator import calc_atr
        import pandas as pd
        highs = pd.Series([102 + i for i in range(15)], dtype=float)
        lows = pd.Series([98 + i for i in range(15)], dtype=float)
        closes = pd.Series([100 + i for i in range(15)], dtype=float)
        result = calc_atr(highs, lows, closes, 14)
        assert result is not None

    def test_calc_highest(self):
        from sv_core.indicators.calculator import calc_highest
        import pandas as pd
        prices = pd.Series([100, 105, 102, 108, 103], dtype=float)
        assert calc_highest(prices, 5) == 108.0

    def test_calc_lowest(self):
        from sv_core.indicators.calculator import calc_lowest
        import pandas as pd
        prices = pd.Series([100, 105, 102, 108, 103], dtype=float)
        assert calc_lowest(prices, 5) == 100.0


class TestV1Compat:
    def test_v1_buy_sell_blocks(self):
        """v1 매수:/매도: → v2 규칙 자동 변환."""
        ast = parse_v2("매수: RSI(14) < 30\n매도: 수익률 >= 5")
        assert isinstance(ast, ScriptV2)
        assert len(ast.rules) == 2
        # 매수 규칙: RSI(14) < 30 AND 보유수량 == 0 → 매수 100%
        buy_rule = ast.rules[0]
        assert buy_rule.action.side == "매수"
        assert isinstance(buy_rule.condition, BinOp)
        assert buy_rule.condition.op == "AND"
        # 매도 규칙: 수익률 >= 5 → 매도 전량
        sell_rule = ast.rules[1]
        assert sell_rule.action.side == "매도"
        assert sell_rule.action.qty_type == "all"
