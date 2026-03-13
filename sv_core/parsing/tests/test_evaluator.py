"""평가기 단위 테스트."""

import pytest

from sv_core.parsing import parse, evaluate


def _ctx(**overrides):
    """기본 컨텍스트 생성."""
    base = {
        "현재가": 50000,
        "거래량": 1000,
        "수익률": 0,
        "보유수량": 0,
        "RSI": lambda period: 50,
        "MA": lambda period: 50000,
        "EMA": lambda period: 50000,
        "MACD": lambda: 0,
        "MACD_SIGNAL": lambda: 0,
        "볼린저_상단": lambda period: 55000,
        "볼린저_하단": lambda period: 45000,
        "평균거래량": lambda period: 500,
    }
    base.update(overrides)
    return base


class TestBasicEvaluation:
    def test_simple_true(self):
        ast = parse("매수: true\n매도: true")
        buy, sell = evaluate(ast, _ctx())
        assert buy is True and sell is True

    def test_simple_false(self):
        ast = parse("매수: false\n매도: false")
        buy, sell = evaluate(ast, _ctx())
        assert buy is False and sell is False

    def test_comparison_gt(self):
        ast = parse("매수: 현재가 > 40000\n매도: true")
        buy, _ = evaluate(ast, _ctx())
        assert buy is True

    def test_comparison_le(self):
        ast = parse("매수: 현재가 <= 40000\n매도: true")
        buy, _ = evaluate(ast, _ctx())
        assert buy is False

    def test_arithmetic(self):
        ast = parse("매수: 현재가 + 10000 > 55000\n매도: true")
        buy, _ = evaluate(ast, _ctx())
        assert buy is True


class TestLogicalOps:
    def test_and(self):
        ast = parse("매수: true AND false\n매도: true")
        buy, _ = evaluate(ast, _ctx())
        assert buy is False

    def test_or(self):
        ast = parse("매수: true OR false\n매도: true")
        buy, _ = evaluate(ast, _ctx())
        assert buy is True

    def test_not(self):
        ast = parse("매수: NOT false\n매도: true")
        buy, _ = evaluate(ast, _ctx())
        assert buy is True


class TestCustomFuncs:
    def test_custom_func_evaluation(self):
        script = "과매도() = RSI(14) <= 30\n매수: 과매도()\n매도: true"
        ast = parse(script)
        buy, _ = evaluate(ast, _ctx(RSI=lambda p: 25))
        assert buy is True
        buy2, _ = evaluate(ast, _ctx(RSI=lambda p: 50))
        assert buy2 is False


class TestPatternFuncs:
    def test_rsi_oversold(self):
        ast = parse("매수: RSI과매도()\n매도: true")
        buy, _ = evaluate(ast, _ctx(RSI=lambda p: 25))
        assert buy is True
        buy2, _ = evaluate(ast, _ctx(RSI=lambda p: 50))
        assert buy2 is False

    def test_rsi_overbought(self):
        ast = parse("매수: true\n매도: RSI과매수()")
        _, sell = evaluate(ast, _ctx(RSI=lambda p: 75))
        assert sell is True


class TestNullPropagation:
    def test_missing_field(self):
        """필드 None → 블록 False."""
        ast = parse("매수: 현재가 > 40000\n매도: true")
        buy, _ = evaluate(ast, _ctx(현재가=None))
        assert buy is False

    def test_missing_field_in_ctx(self):
        """컨텍스트에 필드 없음 → None → False."""
        ast = parse("매수: 현재가 > 40000\n매도: true")
        buy, _ = evaluate(ast, {"거래량": 100})
        assert buy is False

    def test_null_and(self):
        """null + AND → 단락 평가 없음 → False."""
        ast = parse("매수: 현재가 > 40000 AND true\n매도: true")
        buy, _ = evaluate(ast, _ctx(현재가=None))
        assert buy is False

    def test_null_or(self):
        """null + OR → False (단락 평가 없음)."""
        ast = parse("매수: 현재가 > 40000 OR true\n매도: true")
        buy, _ = evaluate(ast, _ctx(현재가=None))
        assert buy is False

    def test_div_by_zero(self):
        ast = parse("매수: 현재가 / 0 > 1\n매도: true")
        buy, _ = evaluate(ast, _ctx())
        assert buy is False

    def test_function_returns_none(self):
        ast = parse("매수: RSI(14) > 30\n매도: true")
        buy, _ = evaluate(ast, _ctx(RSI=lambda p: None))
        assert buy is False

    def test_function_raises(self):
        def bad_func(p):
            raise ValueError("fail")

        ast = parse("매수: RSI(14) > 30\n매도: true")
        buy, _ = evaluate(ast, _ctx(RSI=bad_func))
        assert buy is False


class TestCrossover:
    def test_cross_above_first_eval(self):
        """첫 평가 → False."""
        ast = parse("매수: 상향돌파(RSI(14), 30)\n매도: true")
        buy, _ = evaluate(ast, _ctx(RSI=lambda p: 35), {})
        assert buy is False

    def test_cross_above_triggered(self):
        """이전 A < B, 현재 A >= B → True."""
        ast = parse("매수: 상향돌파(RSI(14), 30)\n매도: true")
        state = {}
        evaluate(ast, _ctx(RSI=lambda p: 25), state)  # RSI=25 < 30
        buy, _ = evaluate(ast, _ctx(RSI=lambda p: 35), state)  # RSI=35 >= 30
        assert buy is True

    def test_cross_above_not_triggered(self):
        """이전 A >= B → 돌파 아님."""
        ast = parse("매수: 상향돌파(RSI(14), 30)\n매도: true")
        state = {}
        evaluate(ast, _ctx(RSI=lambda p: 35), state)  # RSI=35 >= 30
        buy, _ = evaluate(ast, _ctx(RSI=lambda p: 40), state)  # 여전히 위
        assert buy is False

    def test_cross_below_triggered(self):
        ast = parse("매수: true\n매도: 하향돌파(RSI(14), 70)")
        state = {}
        evaluate(ast, _ctx(RSI=lambda p: 75), state)  # RSI=75 > 70
        _, sell = evaluate(ast, _ctx(RSI=lambda p: 65), state)  # RSI=65 <= 70
        assert sell is True


class TestEndToEnd:
    def test_full_strategy(self):
        """spec §2.3 완전 전략."""
        source = (
            "과매도() = RSI(14) <= 30\n"
            "거래량확인() = 거래량 > 평균거래량(20) * 2\n"
            "\n"
            "매수: 골든크로스() AND 과매도() AND 거래량확인()\n"
            "매도: RSI(14) >= 70 OR 수익률 >= 3 OR 수익률 <= -5\n"
        )
        ast = parse(source)
        state = {}

        # 1차 평가: 골든크로스 첫 평가 = false → 매수 false
        ctx1 = _ctx(RSI=lambda p: 25, 거래량=1500)
        buy1, sell1 = evaluate(ast, ctx1, state)
        assert buy1 is False  # 골든크로스 첫 평가
        assert sell1 is False

        # 2차 평가: MA(5) < MA(20) → MA(5) >= MA(20) 돌파 + RSI 과매도 + 거래량
        # (골든크로스 = 상향돌파(MA(5), MA(20)))
        # MA 함수가 period에 따라 다른 값 반환 필요
        def ma_prev(period):
            return 49000 if period == 5 else 50000  # 5일선 < 20일선

        def ma_now(period):
            return 51000 if period == 5 else 50000  # 5일선 > 20일선

        ctx2 = _ctx(RSI=lambda p: 25, 거래량=1500, MA=ma_prev)
        evaluate(ast, ctx2, state)  # 이전값 저장

        ctx3 = _ctx(RSI=lambda p: 25, 거래량=1500, MA=ma_now)
        buy3, sell3 = evaluate(ast, ctx3, state)
        assert buy3 is True  # 골든크로스 + 과매도 + 거래량
        assert sell3 is False

        # 매도: RSI >= 70
        ctx4 = _ctx(RSI=lambda p: 75, MA=ma_now)
        _, sell4 = evaluate(ast, ctx4, state)
        assert sell4 is True
