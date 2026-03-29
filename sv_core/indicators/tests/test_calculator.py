"""sv_core.indicators.calculator 유닛 테스트."""
import numpy as np
import pandas as pd
import pytest

from sv_core.indicators.calculator import (
    calc_all_indicators,
    calc_rsi,
    calc_sma,
    calc_ema,
    calc_macd,
    calc_bollinger,
    calc_avg_volume,
    calc_stochastic,
)


def _make_prices(values: list[float]) -> pd.Series:
    return pd.Series(values, dtype=float)


def _make_rising(n: int = 100, start: float = 10000) -> pd.Series:
    """상승 추세 시계열 (충분한 노이즈로 일부 하락 구간 포함)."""
    np.random.seed(42)
    noise = np.random.normal(0, 150, n)
    return pd.Series([start + i * 50 + noise[i] for i in range(n)], dtype=float)


def _make_falling(n: int = 100, start: float = 20000) -> pd.Series:
    """하락 추세 시계열 (충분한 노이즈로 일부 상승 구간 포함)."""
    np.random.seed(42)
    noise = np.random.normal(0, 80, n)
    return pd.Series([start - i * 100 + noise[i] for i in range(n)], dtype=float)


class TestCalcRsi:
    def test_rising_market_high_rsi(self):
        """상승장 RSI는 70 이상."""
        rsi = calc_rsi(_make_rising(60), 14)
        assert rsi is not None
        assert rsi > 70

    def test_falling_market_low_rsi(self):
        """하락장 RSI는 30 이하."""
        rsi = calc_rsi(_make_falling(60), 14)
        assert rsi is not None
        assert rsi < 30

    def test_insufficient_data(self):
        assert calc_rsi(_make_prices([100, 200, 300]), 14) is None

    def test_custom_period(self):
        rsi = calc_rsi(_make_rising(60), 21)
        assert rsi is not None


class TestCalcSma:
    def test_simple_average(self):
        prices = _make_prices([10, 20, 30, 40, 50])
        assert calc_sma(prices, 5) == 30.0

    def test_insufficient_data(self):
        assert calc_sma(_make_prices([10, 20]), 5) is None


class TestCalcEma:
    def test_returns_value(self):
        ema = calc_ema(_make_rising(20), 12)
        assert ema is not None
        assert isinstance(ema, float)

    def test_insufficient_data(self):
        assert calc_ema(_make_prices([10, 20]), 12) is None


class TestCalcMacd:
    def test_returns_tuple(self):
        macd, signal = calc_macd(_make_rising(50))
        assert macd is not None
        assert signal is not None

    def test_rising_market_positive_macd(self):
        macd, _ = calc_macd(_make_rising(50))
        assert macd > 0

    def test_insufficient_data(self):
        macd, signal = calc_macd(_make_prices([100] * 10))
        assert macd is None
        assert signal is None


class TestCalcBollinger:
    def test_upper_gt_lower(self):
        upper, lower = calc_bollinger(_make_rising(30), 20)
        assert upper is not None
        assert lower is not None
        assert upper > lower

    def test_insufficient_data(self):
        upper, lower = calc_bollinger(_make_prices([100] * 5), 20)
        assert upper is None
        assert lower is None


class TestCalcAvgVolume:
    def test_simple(self):
        volumes = _make_prices([1000] * 20)
        assert calc_avg_volume(volumes, 20) == 1000.0

    def test_insufficient_data(self):
        assert calc_avg_volume(_make_prices([100] * 5), 20) is None


class TestCalcAllIndicators:
    def test_returns_all_keys(self):
        closes = _make_rising(80)
        volumes = pd.Series([10000] * 80, dtype=float)
        result = calc_all_indicators(closes, volumes)

        expected_keys = {
            "rsi_14", "rsi_21",
            "ma_5", "ma_10", "ma_20", "ma_60",
            "ema_12", "ema_20", "ema_26",
            "macd", "macd_signal", "macd_hist",
            "bb_upper_20", "bb_lower_20",
            "avg_volume_20",
            "stoch_k_5_3", "stoch_d_5_3_3",
        }
        assert set(result.keys()) == expected_keys

    def test_short_data_has_nones(self):
        """데이터 부족 시 일부 지표가 None."""
        closes = _make_prices([100] * 10)
        volumes = pd.Series([1000] * 10, dtype=float)
        result = calc_all_indicators(closes, volumes)
        # ma_60은 60바 필요 → None
        assert result["ma_60"] is None
        # ma_5는 5바면 충분 → 값 있음
        assert result["ma_5"] is not None


class TestCalcStochastic:
    def test_basic(self):
        """기본 스토캐스틱 계산."""
        n = 30
        highs = pd.Series([100 + i * 0.5 for i in range(n)], dtype=float)
        lows = pd.Series([90 + i * 0.5 for i in range(n)], dtype=float)
        closes = pd.Series([95 + i * 0.5 for i in range(n)], dtype=float)
        k, d = calc_stochastic(highs, lows, closes)
        assert k is not None
        assert d is not None
        assert 0 <= k <= 100
        assert 0 <= d <= 100

    def test_insufficient_data(self):
        """데이터 부족 시 None."""
        highs = pd.Series([100, 101, 102], dtype=float)
        lows = pd.Series([98, 99, 100], dtype=float)
        closes = pd.Series([99, 100, 101], dtype=float)
        k, d = calc_stochastic(highs, lows, closes)
        assert k is None
        assert d is None

    def test_overbought(self):
        """상승 추세 → %K가 높아야 함."""
        n = 30
        highs = pd.Series(range(100, 100 + n), dtype=float)
        lows = pd.Series(range(90, 90 + n), dtype=float)
        closes = pd.Series(range(99, 99 + n), dtype=float)  # 고가 근처
        k, d = calc_stochastic(highs, lows, closes)
        assert k is not None and k > 50


class TestPresetsParseV2:
    """모든 프리셋이 parse_v2()를 통과하는지 검증."""

    @pytest.fixture
    def presets(self):
        return [
            # 기존 7개
            ('trend-following', """기간 = 14\nMA(20) <= MA(60) AND 보유수량 > 0 → 매도 전량\nRSI(기간) < 30 AND MA(20) > MA(60) AND 보유수량 == 0 → 매수 100%\n수익률 <= -2 → 매도 전량\n수익률 >= 5 → 매도 전량"""),
            # 신규 8개
            ('macd-golden', """MACD골든크로스 AND RSI(14) >= 50 AND 보유수량 == 0 → 매수 100%\nMACD데드크로스 AND 보유수량 > 0 → 매도 전량\n수익률 <= -3 → 매도 전량"""),
            ('bb-rsi-reversal', """볼린저하단돌파 AND RSI과매도 AND 보유수량 == 0 → 매수 100%\n볼린저상단돌파 OR RSI과매수 → 매도 전량\n수익률 <= -4 → 매도 전량"""),
            ('stochastic-bounce', """슬로잉 = 3\n상향돌파(STOCH_K(5, 슬로잉), STOCH_D(5, 슬로잉)) AND STOCH_K(5, 슬로잉) <= 25 AND MA(20) > MA(60) AND 보유수량 == 0 → 매수 100%\n수익률 >= 4 OR STOCH_K(5, 슬로잉) >= 80 → 매도 전량\n수익률 <= -3 → 매도 전량"""),
            ('macd-divergence', """기간 = 20\n강세다이버전스(MACD_HIST(), 기간) AND RSI(14) < 50 AND 보유수량 == 0 → 매수 100%\n약세다이버전스(MACD_HIST(), 기간) AND 보유수량 > 0 → 매도 전량\n수익률 <= -3 → 매도 전량"""),
            ('triple-ma', """MA(5) > MA(20) AND MA(20) > MA(60) AND RSI(14) < 60 AND 보유수량 == 0 → 매수 100%\nMA(5) < MA(20) AND 보유수량 > 0 → 매도 전량\n수익률 <= -3 → 매도 전량"""),
            ('bb-squeeze-breakout', """배수 = 1.5\n상향돌파(현재가, 볼린저_상단(20)) AND 거래량 > 평균거래량(20) * 배수 AND 보유수량 == 0 → 매수 100%\n고점 대비 <= -2 → 매도 전량\n수익률 <= -3 → 매도 전량"""),
            ('morning-momentum', """시간제한 = 30\n목표수익 = 3\n손절 = -2\n등락률 >= 3 AND 장시작후 <= 시간제한 AND 거래량 > 평균거래량(20) * 3 AND 보유수량 == 0 → 매수 100%\n수익률 >= 목표수익 → 매도 전량\n수익률 <= 손절 → 매도 전량\n장시작후 >= 180 AND 보유수량 > 0 → 매도 전량"""),
            ('ema-cross', """단기 = 12\n장기 = 26\n상향돌파(EMA(단기), EMA(장기)) AND 보유수량 == 0 → 매수 100%\n하향돌파(EMA(단기), EMA(장기)) AND 보유수량 > 0 → 매도 전량\n수익률 <= -3 → 매도 전량"""),
        ]

    def test_all_presets_parse(self, presets):
        from sv_core.parsing.parser import parse_v2
        for preset_id, script in presets:
            ast = parse_v2(script)
            assert len(ast.rules) > 0, f"프리셋 {preset_id} 파싱 실패: 규칙 없음"
