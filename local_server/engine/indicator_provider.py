"""IndicatorProvider — 종목별 일봉 기반 기술적 지표 제공.

yfinance에서 80일 일봉을 배치 조회하여 RSI, SMA, EMA, MACD, 볼린저, 평균거래량을 계산.
캐시는 1일 유효 — 일봉 지표는 장중 변하지 않음.

종목 시장 구분:
    market_map을 통해 KOSPI(.KS) / KOSDAQ(.KQ)를 구분한다.
    market 미확인 종목은 .KS로 시도 후 데이터 없으면 .KQ로 재시도.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

import pandas as pd
import yfinance as yf

from sv_core.indicators import calc_all_indicators

logger = logging.getLogger(__name__)

_LOOKBACK_DAYS = 80  # 60일 + 여유
_EMPTY: dict[str, Any] = {}


class IndicatorProvider:
    """종목별 일봉 기반 기술적 지표 제공."""

    def __init__(self) -> None:
        # {symbol: {"date": date, "indicators": dict}}
        self._cache: dict[str, dict] = {}

    async def refresh(
        self,
        symbols: list[str],
        market_map: dict[str, str] | None = None,
    ) -> None:
        """종목들의 일봉 지표를 (재)계산하여 캐시.

        Args:
            symbols: 종목코드 목록
            market_map: {symbol: "KOSPI"|"KOSDAQ"} — 없으면 KOSPI(.KS) 기본
        """
        today = date.today()
        stale = [s for s in symbols if self._is_stale(s, today)]
        if not stale:
            logger.debug("지표 캐시 유효 — 갱신 불필요 (%d종목)", len(symbols))
            return

        _market_map = market_map or {}
        logger.info("지표 계산 시작: %s", stale)
        results = await asyncio.to_thread(self._fetch_and_calc_batch, stale, _market_map)
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

    def _fetch_and_calc_batch(
        self,
        symbols: list[str],
        market_map: dict[str, str],
    ) -> dict[str, dict]:
        """여러 종목의 일봉을 배치 조회하고 지표를 계산한다."""
        # 티커 → 종목코드 매핑
        ticker_to_sym: dict[str, str] = {
            _to_yf_ticker(sym, market_map.get(sym, "")): sym
            for sym in symbols
        }
        tickers = list(ticker_to_sym.keys())

        # yfinance 배치 조회
        try:
            df_by_ticker = _download_batch(tickers)
        except Exception:
            logger.exception("yfinance 배치 조회 실패")
            return {}

        results: dict[str, dict] = {}
        for ticker, sym in ticker_to_sym.items():
            df = df_by_ticker.get(ticker)

            # market 미확인 + 데이터 없음 → 반대 suffix 재시도
            if (df is None or df.empty or len(df) < 15) and not market_map.get(sym):
                alt = f"{sym}.KQ" if ticker.endswith(".KS") else f"{sym}.KS"
                try:
                    df_alt = yf.download(
                        alt,
                        period=f"{_LOOKBACK_DAYS}d",
                        auto_adjust=True,
                        progress=False,
                    )
                    if not df_alt.empty and len(df_alt) >= 15:
                        df = df_alt
                        logger.info("대체 티커 사용 [%s → %s]", ticker, alt)
                except Exception:
                    pass

            if df is None or df.empty or len(df) < 15:
                logger.warning("일봉 데이터 부족 [%s]", sym)
                continue

            try:
                closes = df["Close"].squeeze()
                volumes = df["Volume"].squeeze()
                indicators = calc_all_indicators(closes, volumes)
                if indicators:
                    results[sym] = indicators
            except Exception:
                logger.exception("지표 계산 실패 [%s]", sym)

        return results


# ── 티커 변환 ──


def _to_yf_ticker(symbol: str, market: str = "") -> str:
    """한국 종목코드를 yfinance 티커로 변환.

    KOSPI: {code}.KS, KOSDAQ: {code}.KQ
    market 미확인 시 KOSPI(.KS)를 기본으로 사용.
    """
    if "." in symbol:
        return symbol  # 이미 yfinance 형식
    if market == "KOSDAQ":
        return f"{symbol}.KQ"
    return f"{symbol}.KS"


def _download_batch(tickers: list[str]) -> dict[str, pd.DataFrame]:
    """yfinance 배치 다운로드. 티커 → DataFrame 반환."""
    if not tickers:
        return {}

    period = f"{_LOOKBACK_DAYS}d"

    if len(tickers) == 1:
        df = yf.download(tickers[0], period=period, auto_adjust=True, progress=False)
        return {tickers[0]: df}

    df_all = yf.download(
        tickers,
        period=period,
        auto_adjust=True,
        progress=False,
        group_by="ticker",
    )

    # MultiIndex: df_all[ticker] → 종목별 DataFrame
    result: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        if ticker in df_all:
            result[ticker] = df_all[ticker].dropna(how="all")
    return result


# 지표 계산 함수는 sv_core.indicators.calculator로 이동됨
