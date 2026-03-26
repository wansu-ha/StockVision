"""기술적 지표 계산 순수 함수.

입력: pandas Series (가격/거래량)
출력: 스칼라 값 또는 딕셔너리

일봉/분봉 모두 동일한 함수로 계산한다.
타임프레임 차이는 호출 측에서 적절한 Series를 전달하여 처리.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def calc_all_indicators(closes: pd.Series, volumes: pd.Series) -> dict:
    """evaluator가 기대하는 전체 indicators dict를 생성한다.

    Args:
        closes: 종가 시계열 (오래된 순 → 최근 순)
        volumes: 거래량 시계열

    Returns:
        {"rsi_14": float|None, "ma_5": float|None, ...}
    """
    macd, macd_signal = calc_macd(closes)
    bb_upper_20, bb_lower_20 = calc_bollinger(closes, 20)

    return {
        # RSI
        "rsi_14": calc_rsi(closes, 14),
        "rsi_21": calc_rsi(closes, 21),
        # SMA
        "ma_5": calc_sma(closes, 5),
        "ma_10": calc_sma(closes, 10),
        "ma_20": calc_sma(closes, 20),
        "ma_60": calc_sma(closes, 60),
        # EMA
        "ema_12": calc_ema(closes, 12),
        "ema_20": calc_ema(closes, 20),
        "ema_26": calc_ema(closes, 26),
        # MACD
        "macd": macd,
        "macd_signal": macd_signal,
        # 볼린저
        "bb_upper_20": bb_upper_20,
        "bb_lower_20": bb_lower_20,
        # 평균 거래량
        "avg_volume_20": calc_avg_volume(volumes, 20),
    }


def calc_rsi(prices: pd.Series, period: int = 14) -> float | None:
    """RSI (Relative Strength Index)."""
    if len(prices) < period + 1:
        return None
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None


def calc_sma(prices: pd.Series, period: int) -> float | None:
    """단순 이동평균 (Simple Moving Average)."""
    if len(prices) < period:
        return None
    val = prices.rolling(period).mean().iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None


def calc_ema(prices: pd.Series, period: int) -> float | None:
    """지수 이동평균 (Exponential Moving Average)."""
    if len(prices) < period:
        return None
    val = prices.ewm(span=period).mean().iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None


def calc_macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[float | None, float | None]:
    """MACD (Moving Average Convergence Divergence).

    Returns:
        (macd_line, signal_line)
    """
    min_len = slow + signal
    if len(prices) < min_len:
        return None, None
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    m, s = macd_line.iloc[-1], signal_line.iloc[-1]
    if np.isnan(m) or np.isnan(s):
        return None, None
    return round(float(m), 2), round(float(s), 2)


def calc_bollinger(
    prices: pd.Series, period: int = 20, num_std: float = 2.0,
) -> tuple[float | None, float | None]:
    """볼린저 밴드 (Bollinger Bands).

    Returns:
        (upper_band, lower_band)
    """
    if len(prices) < period:
        return None, None
    sma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    u, l = upper.iloc[-1], lower.iloc[-1]
    if np.isnan(u) or np.isnan(l):
        return None, None
    return round(float(u), 2), round(float(l), 2)


def calc_avg_volume(volumes: pd.Series, period: int = 20) -> float | None:
    """평균 거래량."""
    if len(volumes) < period:
        return None
    val = volumes.rolling(period).mean().iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None
