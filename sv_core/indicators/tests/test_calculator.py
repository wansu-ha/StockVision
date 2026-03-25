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
            "macd", "macd_signal",
            "bb_upper_20", "bb_lower_20",
            "avg_volume_20",
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
