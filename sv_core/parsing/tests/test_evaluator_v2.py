"""v2 평가기 단위 테스트."""

import pytest

from sv_core.parsing import parse_v2, evaluate_v2, EvalV2Result, ActionResult, ConditionSnapshot
from sv_core.parsing.evaluator import _Evaluator


def _ctx(**overrides):
    """기본 컨텍스트 생성."""
    base = {
        "현재가": 50000, "거래량": 1000, "수익률": 0,
        "보유수량": 0, "고점 대비": 0, "수익률고점": 0,
        "진입가": 0, "보유일": 0, "보유봉": 0,
        "실행횟수": 0, "장시작후": 30, "시간": 930, "요일": 1,
        "등락률": 2.5,
        "RSI": lambda period, tf=None: 50,
        "MA": lambda period, tf=None: 50000,
        "EMA": lambda period, tf=None: 50000,
        "MACD": lambda tf=None: 0,
        "MACD_SIGNAL": lambda tf=None: 0,
        "MACD_HIST": lambda tf=None: 0,
        "STOCH_K": lambda k=5, s=3, tf=None: 50,
        "STOCH_D": lambda k=5, s=3, d=3, tf=None: 50,
        "볼린저_상단": lambda period, tf=None: 55000,
        "볼린저_하단": lambda period, tf=None: 45000,
        "평균거래량": lambda period, tf=None: 500,
        "ATR": lambda period, tf=None: 1000,
        "최고가": lambda period, tf=None: 52000,
        "최저가": lambda period, tf=None: 48000,
        "이격도": lambda period, tf=None: 0,
    }
    base.update(overrides)
    return base


class TestEvalV2Basic:
    def test_single_buy(self):
        ast = parse_v2("현재가 > 40000 AND 보유수량 == 0 -> 매수 100%")
        result = evaluate_v2(ast, _ctx())
        assert result.action is not None
        assert result.action.side == "매수"
        assert result.action.qty_type == "percent"
        assert result.action.qty_value == 100.0

    def test_single_sell(self):
        ast = parse_v2("수익률 >= 5 -> 매도 전량")
        result = evaluate_v2(ast, _ctx(수익률=6))
        assert result.action is not None
        assert result.action.side == "매도"
        assert result.action.qty_type == "all"

    def test_no_match(self):
        ast = parse_v2("현재가 > 999999 -> 매수 100%")
        result = evaluate_v2(ast, _ctx())
        assert result.action is None

    def test_snapshots_always_recorded(self):
        source = "현재가 > 999999 -> 매수 100%\n수익률 >= 5 -> 매도 전량"
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx())
        assert len(result.snapshots) == 2
        assert result.snapshots[0].rule_index == 0
        assert result.snapshots[0].result is False
        assert result.snapshots[1].rule_index == 1
        assert result.snapshots[1].result is False


class TestEvalV2Priority:
    def test_full_sell_over_partial(self):
        """전량매도가 부분매도보다 우선."""
        source = (
            "수익률 >= 3 -> 매도 50%\n"
            "수익률 >= 1 -> 매도 전량"
        )
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(수익률=5))
        assert result.action is not None
        assert result.action.side == "매도"
        assert result.action.qty_type == "all"
        assert result.action.rule_index == 1

    def test_sell_over_buy(self):
        """매도가 매수보다 우선."""
        source = (
            "현재가 > 40000 AND 보유수량 == 0 -> 매수 100%\n"
            "수익률 >= 3 -> 매도 전량"
        )
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(수익률=5))
        assert result.action is not None
        assert result.action.side == "매도"

    def test_top_rule_wins(self):
        """같은 유형이면 위 규칙 우선."""
        source = (
            "수익률 >= 3 -> 매도 전량\n"
            "수익률 >= 1 -> 매도 전량"
        )
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(수익률=5))
        assert result.action.rule_index == 0

    def test_partial_when_no_full(self):
        """전량매도 없으면 부분매도."""
        source = (
            "수익률 >= 3 -> 매도 50%\n"
            "현재가 > 40000 -> 매수 100%"
        )
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(수익률=5))
        assert result.action.side == "매도"
        assert result.action.qty_type == "percent"

    def test_buy_only_when_no_sell(self):
        """매도 규칙 불발 시에만 매수."""
        source = (
            "수익률 >= 10 -> 매도 전량\n"
            "현재가 > 40000 AND 보유수량 == 0 -> 매수 100%"
        )
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(수익률=1))
        assert result.action.side == "매수"


class TestEvalV2Constants:
    def test_const_substitution(self):
        source = (
            "손절 = -3\n"
            "수익률 <= 손절 -> 매도 전량"
        )
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(수익률=-5))
        assert result.action is not None
        assert result.action.side == "매도"

    def test_const_in_comparison(self):
        source = (
            "기간 = 14\n"
            "RSI(기간) < 30 -> 매수 100%"
        )
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 25))
        assert result.action is not None
        assert result.action.side == "매수"


class TestEvalV2CustomFunc:
    def test_custom_func_no_parens(self):
        """괄호 없는 커스텀 함수."""
        source = (
            "과매도 = RSI(14) <= 30\n"
            "과매도 AND 보유수량 == 0 -> 매수 100%"
        )
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 25))
        assert result.action is not None
        assert result.action.side == "매수"

    def test_custom_func_with_parens(self):
        """괄호 있는 커스텀 함수."""
        source = (
            "과매도() = RSI(14) <= 30\n"
            "과매도() AND 보유수량 == 0 -> 매수 100%"
        )
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 25))
        assert result.action is not None
        assert result.action.side == "매수"


class TestEvalV2Between:
    def test_between_true(self):
        source = "RSI(14) BETWEEN 40 AND 60 -> 매수 100%"
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 50))
        assert result.action is not None

    def test_between_false_below(self):
        source = "RSI(14) BETWEEN 40 AND 60 -> 매수 100%"
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 30))
        assert result.action is None

    def test_between_false_above(self):
        source = "RSI(14) BETWEEN 40 AND 60 -> 매수 100%"
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 70))
        assert result.action is None


class TestEvalV2StateFunctions:
    def test_count_over_cycles(self):
        """횟수: 여러 사이클에 걸쳐 조건 True 횟수 카운트."""
        source = "횟수(수익률 >= 2, 5) >= 2 -> 매도 전량"
        ast = parse_v2(source)
        state = {}

        # 사이클 1: 수익률=3 → True (1/5)
        r1 = evaluate_v2(ast, _ctx(수익률=3), state)
        assert r1.action is None  # 1 < 2

        # 사이클 2: 수익률=1 → False (1/5)
        r2 = evaluate_v2(ast, _ctx(수익률=1), state)
        assert r2.action is None

        # 사이클 3: 수익률=5 → True (2/5)
        r3 = evaluate_v2(ast, _ctx(수익률=5), state)
        assert r3.action is not None
        assert r3.action.side == "매도"

    def test_consecutive_3_times(self):
        """연속: 3봉 연속 True."""
        source = "연속(수익률 >= 1) >= 3 -> 매도 전량"
        ast = parse_v2(source)
        state = {}

        r1 = evaluate_v2(ast, _ctx(수익률=2), state)
        assert r1.action is None  # 1회

        r2 = evaluate_v2(ast, _ctx(수익률=2), state)
        assert r2.action is None  # 2회

        r3 = evaluate_v2(ast, _ctx(수익률=2), state)
        assert r3.action is not None  # 3회
        assert r3.action.side == "매도"

    def test_consecutive_reset(self):
        """연속: 중간에 False면 리셋."""
        source = "연속(수익률 >= 1) >= 3 -> 매도 전량"
        ast = parse_v2(source)
        state = {}

        evaluate_v2(ast, _ctx(수익률=2), state)  # 1회
        evaluate_v2(ast, _ctx(수익률=2), state)  # 2회
        evaluate_v2(ast, _ctx(수익률=0), state)  # 리셋
        evaluate_v2(ast, _ctx(수익률=2), state)  # 1회
        r = evaluate_v2(ast, _ctx(수익률=2), state)  # 2회
        assert r.action is None  # 아직 3회 아님


class TestEvalV2Snapshots:
    def test_details_populated(self):
        """스냅샷에 조건 필드값이 기록된다."""
        source = "수익률 >= 5 -> 매도 전량"
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(수익률=3))
        snap = result.snapshots[0]
        assert snap.result is False
        assert "수익률" in snap.details
        assert snap.details["수익률"] == 3

    def test_all_rules_have_snapshots(self):
        """실행되지 않은 규칙도 스냅샷에 포함."""
        source = (
            "수익률 >= 10 -> 매도 전량\n"
            "수익률 >= 5 -> 매도 50%\n"
            "현재가 > 40000 AND 보유수량 == 0 -> 매수 100%"
        )
        ast = parse_v2(source)
        result = evaluate_v2(ast, _ctx(수익률=3))
        assert len(result.snapshots) == 3
        for i, snap in enumerate(result.snapshots):
            assert snap.rule_index == i


# ── 신규 함수 테스트 ──


class TestEvalV2NewFunctions:
    """MACD_HIST, STOCH_K/D, 등락률 테스트."""

    def test_macd_hist_positive(self):
        ast = parse_v2("MACD_HIST() > 0 AND 보유수량 == 0 → 매수 100%")
        result = evaluate_v2(ast, _ctx(MACD_HIST=lambda tf=None: 1.5))
        assert result.action is not None
        assert result.action.side == "매수"

    def test_macd_hist_negative_no_match(self):
        ast = parse_v2("MACD_HIST() > 0 → 매수 100%")
        result = evaluate_v2(ast, _ctx(MACD_HIST=lambda tf=None: -1.0))
        assert result.action is None

    def test_stoch_k_oversold(self):
        ast = parse_v2("STOCH_K(5, 3) < 20 AND 보유수량 == 0 → 매수 100%")
        result = evaluate_v2(ast, _ctx(STOCH_K=lambda k=5, s=3, tf=None: 15))
        assert result.action is not None
        assert result.action.side == "매수"

    def test_stoch_d_overbought(self):
        ast = parse_v2("STOCH_D(5, 3, 3) >= 80 → 매도 전량")
        result = evaluate_v2(ast, _ctx(STOCH_D=lambda k=5, s=3, d=3, tf=None: 85))
        assert result.action is not None
        assert result.action.side == "매도"

    def test_change_rate_field(self):
        """등락률 필드 테스트."""
        ast = parse_v2("등락률 >= 3 AND 보유수량 == 0 → 매수 100%")
        result = evaluate_v2(ast, _ctx(등락률=5.0))
        assert result.action is not None
        assert result.action.side == "매수"

    def test_change_rate_below_threshold(self):
        ast = parse_v2("등락률 >= 3 → 매수 100%")
        result = evaluate_v2(ast, _ctx(등락률=1.0))
        assert result.action is None


class TestEvalV2Divergence:
    """강세/약세 다이버전스 테스트."""

    def test_bullish_divergence_detected(self):
        """가격 저점↓ + 지표 저점↑ → True."""
        hist = [
            (100, -5), (98, -6), (96, -7),
            (97, -6),
            (95, -5), (94, -4),
            (93, -3),
            (95, -2),
        ]
        assert _Evaluator._detect_divergence(hist, bullish=True) is True

    def test_bullish_divergence_not_detected(self):
        """가격↓ 지표↓ → False."""
        hist = [
            (100, -5), (98, -6), (96, -7),
            (97, -6),
            (95, -8), (94, -9),
            (93, -10),
            (95, -9),
        ]
        assert _Evaluator._detect_divergence(hist, bullish=True) is False

    def test_bearish_divergence_detected(self):
        """가격 고점↑ + 지표 고점↓ → True."""
        hist = [
            (90, 5), (92, 6), (94, 7),
            (93, 6),
            (95, 5), (96, 4),
            (97, 3),
            (95, 2),
        ]
        assert _Evaluator._detect_divergence(hist, bullish=False) is True

    def test_bearish_divergence_not_detected(self):
        """가격↑ 지표↑ → False."""
        hist = [
            (90, 5), (92, 6), (94, 7),
            (93, 6),
            (95, 8), (96, 9),
            (97, 10),
            (95, 9),
        ]
        assert _Evaluator._detect_divergence(hist, bullish=False) is False

    def test_insufficient_data(self):
        """데이터 부족 시 False."""
        hist = [(100, -5), (98, -6), (96, -7)]
        assert _Evaluator._detect_divergence(hist, bullish=True) is False

    def test_divergence_via_evaluate_v2(self):
        """evaluate_v2를 통한 다이버전스 통합 테스트 (히스토리 축적)."""
        ast = parse_v2("강세다이버전스(MACD_HIST(), 20) AND 보유수량 == 0 → 매수 100%")
        state = {}

        # 히스토리를 충분히 쌓는다 (강세 다이버전스 패턴)
        prices =  [100, 98, 96, 97, 95, 94, 93, 95]
        indvals = [ -5, -6, -7, -6, -5, -4, -3, -2]
        result = None
        for p, iv in zip(prices, indvals):
            result = evaluate_v2(
                ast,
                _ctx(현재가=p, MACD_HIST=lambda tf=None, _v=iv: _v),
                state,
            )
        # 8봉 쌓인 후 → 강세 다이버전스 감지되어야 함
        assert result is not None
        assert result.action is not None
        assert result.action.side == "매수"
