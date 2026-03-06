"""파서 단위 테스트."""

import pytest

from sv_core.parsing import parse, DSLSyntaxError, DSLTypeError, DSLNameError
from sv_core.parsing.ast_nodes import (
    BinOp, BoolLit, BuyBlock, Comparison, CustomFuncDef,
    FieldRef, FuncCall, NumberLit, Script, SellBlock, UnaryOp,
)


class TestBasicParsing:
    def test_minimal_script(self):
        ast = parse("매수: true\n매도: false")
        assert isinstance(ast, Script)
        assert isinstance(ast.buy_block.expr, BoolLit)
        assert ast.buy_block.expr.value is True
        assert isinstance(ast.sell_block.expr, BoolLit)
        assert ast.sell_block.expr.value is False

    def test_comparison(self):
        ast = parse("매수: 현재가 > 50000\n매도: 현재가 < 40000")
        cmp = ast.buy_block.expr
        assert isinstance(cmp, Comparison)
        assert cmp.op == ">"
        assert isinstance(cmp.left, FieldRef)
        assert isinstance(cmp.right, NumberLit)

    def test_custom_func(self):
        ast = parse("과매도() = RSI(14) <= 30\n매수: 과매도()\n매도: true")
        assert len(ast.custom_funcs) == 1
        assert ast.custom_funcs[0].name == "과매도"
        assert isinstance(ast.buy_block.expr, FuncCall)


class TestOperatorPrecedence:
    def test_and_or_precedence(self):
        """A OR B AND C → A OR (B AND C)."""
        ast = parse("매수: true OR false AND true\n매도: true")
        expr = ast.buy_block.expr
        assert isinstance(expr, BinOp) and expr.op == "OR"
        assert isinstance(expr.right, BinOp) and expr.right.op == "AND"

    def test_not_precedence(self):
        """NOT A AND B → (NOT A) AND B."""
        ast = parse("매수: NOT true AND false\n매도: true")
        expr = ast.buy_block.expr
        assert isinstance(expr, BinOp) and expr.op == "AND"
        assert isinstance(expr.left, UnaryOp) and expr.left.op == "NOT"

    def test_arithmetic_precedence(self):
        """A + B * C → A + (B * C)."""
        ast = parse("매수: 현재가 + 거래량 * 2 > 100\n매도: true")
        cmp = ast.buy_block.expr
        assert isinstance(cmp, Comparison)
        add = cmp.left
        assert isinstance(add, BinOp) and add.op == "+"
        assert isinstance(add.right, BinOp) and add.right.op == "*"

    def test_unary_minus(self):
        ast = parse("매수: 수익률 <= -5\n매도: true")
        cmp = ast.buy_block.expr
        assert isinstance(cmp, Comparison)
        assert isinstance(cmp.right, UnaryOp) and cmp.right.op == "-"

    def test_parentheses(self):
        """(A OR B) AND C — 괄호로 우선순위 오버라이드."""
        ast = parse("매수: (true OR false) AND true\n매도: true")
        expr = ast.buy_block.expr
        assert isinstance(expr, BinOp) and expr.op == "AND"
        assert isinstance(expr.left, BinOp) and expr.left.op == "OR"


class TestSpecExamples:
    def test_spec_example(self):
        """spec §2.3 예시."""
        source = (
            "과매도() = RSI(14) <= 30\n"
            "거래량확인() = 거래량 > 평균거래량(20) * 2\n"
            "\n"
            "매수: 골든크로스() AND 과매도() AND 거래량확인()\n"
            "매도: RSI(14) >= 70 OR 수익률 >= 3 OR 수익률 <= -5\n"
        )
        ast = parse(source)
        assert len(ast.custom_funcs) == 2
        assert ast.custom_funcs[0].name == "과매도"
        assert ast.custom_funcs[1].name == "거래량확인"

    def test_advanced_example(self):
        """grammar.md 고급 예시."""
        source = (
            "저가권() = 현재가 <= 볼린저_하단(20) * 1.02\n"
            "거래량폭발() = 거래량 >= 평균거래량(20) * 3\n"
            "추세전환() = MACD골든크로스() AND NOT 데드크로스()\n"
            "적정가격() = 현재가 >= MA(5) - (MA(20) - MA(5)) / 2\n"
            "\n"
            "매수: 저가권() AND 거래량폭발() AND (추세전환() OR 상향돌파(RSI(14), 30))\n"
            "매도: 볼린저상단돌파() OR 수익률 >= 5 OR 수익률 <= -3\n"
        )
        ast = parse(source)
        assert len(ast.custom_funcs) == 4


class TestSemanticErrors:
    def test_missing_buy(self):
        with pytest.raises(DSLSyntaxError, match="매수: 블록이 없습니다"):
            parse("매도: true")

    def test_missing_sell(self):
        with pytest.raises(DSLSyntaxError, match="매도: 블록이 없습니다"):
            parse("매수: true")

    def test_duplicate_buy(self):
        with pytest.raises(DSLSyntaxError, match="매수: 블록이 중복됩니다"):
            parse("매수: true\n매수: false\n매도: true")

    def test_duplicate_sell(self):
        with pytest.raises(DSLSyntaxError, match="매도: 블록이 중복됩니다"):
            parse("매수: true\n매도: true\n매도: false")

    def test_custom_func_duplicate(self):
        with pytest.raises(DSLNameError, match="이미 정의되었습니다"):
            parse("a() = true\na() = false\n매수: a()\n매도: true")

    def test_custom_func_recursion(self):
        with pytest.raises(DSLNameError, match="자기 자신을 참조합니다"):
            parse("재귀() = 재귀()\n매수: true\n매도: true")

    def test_undefined_ident(self):
        with pytest.raises(DSLNameError, match="정의되지 않은 식별자"):
            parse("매수: 없는변수 > 0\n매도: true")

    def test_undefined_func(self):
        with pytest.raises(DSLNameError, match="정의되지 않은 식별자"):
            parse("매수: 없는함수()\n매도: true")

    def test_comparison_chaining(self):
        with pytest.raises(DSLSyntaxError, match="비교 연산을 연속으로"):
            parse("매수: 현재가 > 100 > 50\n매도: true")

    def test_custom_func_with_args(self):
        with pytest.raises(DSLSyntaxError, match="인자를 받지 않습니다"):
            parse("f() = true\n매수: f(1)\n매도: true")

    def test_builtin_func_wrong_args(self):
        with pytest.raises(DSLSyntaxError, match="1개 인자가 필요하지만"):
            parse("매수: RSI(14, 20) > 30\n매도: true")


class TestTypeErrors:
    def test_buy_block_not_boolean(self):
        with pytest.raises(DSLTypeError, match="boolean"):
            parse("매수: RSI(14)\n매도: true")

    def test_sell_block_not_boolean(self):
        with pytest.raises(DSLTypeError, match="boolean"):
            parse("매수: true\n매도: 현재가")

    def test_and_with_number(self):
        with pytest.raises(DSLTypeError, match="boolean"):
            parse("매수: 현재가 AND true\n매도: true")

    def test_or_with_number(self):
        with pytest.raises(DSLTypeError, match="boolean"):
            parse("매수: true OR 현재가\n매도: true")

    def test_not_with_number(self):
        with pytest.raises(DSLTypeError, match="boolean"):
            parse("매수: NOT 현재가\n매도: true")

    def test_comparison_with_boolean(self):
        with pytest.raises(DSLTypeError, match="숫자"):
            parse("매수: true > 30\n매도: true")

    def test_arithmetic_with_boolean(self):
        with pytest.raises(DSLTypeError, match="숫자"):
            parse("매수: true + 1 > 0\n매도: true")
