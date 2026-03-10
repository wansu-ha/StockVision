"""IndicatorProvider — 종목별 일봉 기반 기술적 지표 제공.

yfinance에서 60일 일봉을 조회하여 RSI, SMA, EMA, MACD, 볼린저, 평균거래량을 계산.
캐시는 1일 유효 — 일봉 지표는 장중 변하지 않음.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

_LOOKBACK_DAYS = 80  # 60일 + 여유
_EMPTY: dict[str, Any] = {}


class IndicatorProvider:
    """종목별 일봉 기반 기술적 지표 제공."""

    def __init__(self) -> None:
        # {symbol: {"date": date, "indicators": dict}}
        self._cache: dict[str, dict] = {}

    async def refresh(self, symbols: list[str]) -> None:
        """종목들의 일봉 지표를 (재)계산하여 캐시.

        yfinance는 blocking이므로 thread pool에서 실행.
        """
        today = date.today()
        stale = [s for s in symbols if self._is_stale(s, today)]
        if not stale:
            logger.debug("지표 캐시 유효 — 갱신 불필요 (%d종목)", len(symbols))
            return

        logger.info("지표 계산 시작: %s", stale)
        results = await asyncio.to_thread(self._fetch_and_calc_batch, stale)
        for sym, indicators in results.items():
            self._cache[sym] = {"date": today, "indicators": indicators}
        logger.info("지표 계산 완료: %d종목 성공", len(results))

    def get(self, symbol: str) -> dict:
        """evaluator가 기대하는 indicators dict 반환."""
        entry = self._cache.get(symbol)
        if not entry:
            return _EMPTY
        return entry["indicators"]

    def _is_stale(self, symbol: str, today: date) -> bool:
        entry = self._cache.get(symbol)
        return entry is None or entry["date"] != today

    # ── 데이터 조회 + 계산 (blocking, thread pool에서 호출) ──

    def _fetch_and_calc_batch(self, symbols: list[str]) -> dict[str, dict]:
        """여러 종목의 일봉을 조회하고 지표를 계산한다."""
        results: dict[str, dict] = {}
        for sym in symbols:
            try:
                indicators = self._fetch_and_calc(sym)
                if indicators:
                    results[sym] = indicators
            except Exception:
                logger.exception("지표 계산 실패 [%s]", sym)
        return results

    def _fetch_and_calc(self, symbol: str) -> dict | None:
        """단일 종목 일봉 조회 → 지표 계산."""
        ticker = _to_yf_ticker(symbol)
        df = yf.download(
            ticker,
            period=f"{_LOOKBACK_DAYS}d",
            auto_adjust=True,
            progress=False,
        )
        if df is None or df.empty or len(df) < 15:
            logger.warning("일봉 데이터 부족 [%s]: %d rows", symbol, 0 if df is None else len(df))
            return None

        closes = df["Close"].squeeze()
        volumes = df["Volume"].squeeze()
        return _calc_all_indicators(closes, volumes)


def _to_yf_ticker(symbol: str) -> str:
    """한국 종목코드를 yfinance 티커로 변환.

    KOSPI: {code}.KS, KOSDAQ: {code}.KQ
    대부분의 주요 종목은 KOSPI → .KS를 기본으로 사용.
    """
    if "." in symbol:
        return symbol  # 이미 yfinance 형식
    return f"{symbol}.KS"


def _calc_all_indicators(closes: pd.Series, volumes: pd.Series) -> dict:
    """evaluator가 기대하는 전체 indicators dict를 생성한다."""
    macd, macd_signal = _calc_macd(closes)
    bb_upper_20, bb_lower_20 = _calc_bollinger(closes, 20)

    return {
        # RSI
        "rsi_14": _calc_rsi(closes, 14),
        "rsi_21": _calc_rsi(closes, 21),
        # SMA
        "ma_5": _calc_sma(closes, 5),
        "ma_10": _calc_sma(closes, 10),
        "ma_20": _calc_sma(closes, 20),
        "ma_60": _calc_sma(closes, 60),
        # EMA
        "ema_12": _calc_ema(closes, 12),
        "ema_20": _calc_ema(closes, 20),
        "ema_26": _calc_ema(closes, 26),
        # MACD
        "macd": macd,
        "macd_signal": macd_signal,
        # 볼린저
        "bb_upper_20": bb_upper_20,
        "bb_lower_20": bb_lower_20,
        # 평균 거래량
        "avg_volume_20": _calc_avg_volume(volumes, 20),
    }


# ── 지표 계산 순수 함수 ──


def _calc_rsi(prices: pd.Series, period: int = 14) -> float | None:
    if len(prices) < period + 1:
        return None
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None


def _calc_sma(prices: pd.Series, period: int) -> float | None:
    if len(prices) < period:
        return None
    val = prices.rolling(period).mean().iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None


def _calc_ema(prices: pd.Series, period: int) -> float | None:
    if len(prices) < period:
        return None
    val = prices.ewm(span=period).mean().iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None


def _calc_macd(prices: pd.Series) -> tuple[float | None, float | None]:
    if len(prices) < 35:
        return None, None
    ema12 = prices.ewm(span=12).mean()
    ema26 = prices.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9).mean()
    m, s = macd_line.iloc[-1], signal.iloc[-1]
    if np.isnan(m) or np.isnan(s):
        return None, None
    return round(float(m), 2), round(float(s), 2)


def _calc_bollinger(prices: pd.Series, period: int = 20) -> tuple[float | None, float | None]:
    if len(prices) < period:
        return None, None
    sma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    u, l = upper.iloc[-1], lower.iloc[-1]
    if np.isnan(u) or np.isnan(l):
        return None, None
    return round(float(u), 2), round(float(l), 2)


def _calc_avg_volume(volumes: pd.Series, period: int = 20) -> float | None:
    if len(volumes) < period:
        return None
    val = volumes.rolling(period).mean().iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None
