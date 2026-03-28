"""IndicatorProvider — 종목별 일봉/분봉 기반 기술적 지표 제공.

일봉: yfinance에서 80일 일봉을 배치 조회, 캐시 1일 유효.
분봉: cloud_server MinuteBar API에서 조회, 캐시 1분 유효.
      캐시 만료 시 None 반환 (평가 건너뜀).
      엔진 루프(evaluate_all)가 매 사이클마다 refresh_minute()를 호출하여 갱신.

종목 시장 구분:
    market_map을 통해 KOSPI(.KS) / KOSDAQ(.KQ)를 구분한다.
    market 미확인 종목은 .KS로 시도 후 데이터 없으면 .KQ로 재시도.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from sv_core.indicators import calc_all_indicators

logger = logging.getLogger(__name__)

_LOOKBACK_DAYS = 80  # 60일 + 여유
_MINUTE_LOOKBACK = 200  # 분봉 최대 조회 건수
_MINUTE_CACHE_TTL = timedelta(minutes=1)  # 분봉 캐시 유효기간
_EMPTY: dict[str, Any] = {}


class IndicatorProvider:
    """종목별 일봉/분봉 기반 기술적 지표 제공."""

    def __init__(self) -> None:
        # 일봉 캐시: {symbol: {"date": date, "indicators": dict}}
        self._daily_cache: dict[str, dict] = {}
        # 분봉 캐시: {symbol: {tf: {"expires": datetime, "indicators": dict}}}
        self._minute_cache: dict[str, dict[str, dict]] = {}

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
        stale = [s for s in symbols if self._is_daily_stale(s, today)]
        if not stale:
            logger.debug("지표 캐시 유효 — 갱신 불필요 (%d종목)", len(symbols))
            return

        _market_map = market_map or {}
        logger.info("지표 계산 시작: %s", stale)
        results = await asyncio.to_thread(self._fetch_and_calc_batch, stale, _market_map)
        for sym, indicators in results.items():
            self._daily_cache[sym] = {"date": today, "indicators": indicators}
        logger.info("지표 계산 완료: %d종목 성공", len(results))

    async def refresh_minute(self, symbol: str, tf: str) -> None:
        """분봉 지표를 계산하여 캐시.

        cloud_server MinuteBar API에서 분봉을 조회하고
        calc_all_indicators로 지표를 계산한다.
        CloudClient가 없거나 조회 실패 시 캐시를 갱신하지 않는다.

        Args:
            symbol: 종목코드
            tf: 타임프레임 ("1m", "5m", "15m", "1h")
        """
        from local_server.cloud.heartbeat import get_cloud_client
        client = get_cloud_client()
        if client is None:
            logger.debug("CloudClient 없음 — 분봉 지표 갱신 생략 [%s %s]", symbol, tf)
            return

        try:
            path = f"/api/v1/stocks/{symbol}/bars?resolution={tf}&limit={_MINUTE_LOOKBACK}"
            resp = await client._get(path)
            data: list[dict] = resp.get("data", []) if isinstance(resp, dict) else []
        except Exception:
            logger.warning("분봉 조회 실패 [%s %s]", symbol, tf)
            return

        if len(data) < 15:
            logger.debug("분봉 데이터 부족 [%s %s]: %d건", symbol, tf, len(data))
            return

        try:
            valid = [b for b in data if b.get("close") is not None]
            closes = pd.Series([float(b["close"]) for b in valid])
            volumes = pd.Series([float(b.get("volume") or 0) for b in valid])
            if len(closes) < 15:
                return
            indicators = calc_all_indicators(closes, volumes)
        except Exception:
            logger.exception("분봉 지표 계산 실패 [%s %s]", symbol, tf)
            return

        if symbol not in self._minute_cache:
            self._minute_cache[symbol] = {}
        self._minute_cache[symbol][tf] = {
            "expires": datetime.now() + _MINUTE_CACHE_TTL,
            "indicators": indicators,
        }
        logger.debug("분봉 지표 캐시 갱신 [%s %s]", symbol, tf)

    def get(self, symbol: str, tf: str = "1d") -> dict | None:
        """evaluator가 기대하는 indicators dict 반환.

        Args:
            symbol: 종목코드
            tf: 타임프레임. "1d"=일봉, "1m"/"5m" 등=분봉.

        Returns:
            지표 dict. 분봉 캐시 만료/미존재 시 None 반환.
            일봉 캐시 미존재 시 빈 dict 반환 (기존 동작 유지).
        """
        if tf == "1d":
            entry = self._daily_cache.get(symbol)
            return entry["indicators"] if entry else _EMPTY

        # 분봉
        sym_cache = self._minute_cache.get(symbol, {})
        entry = sym_cache.get(tf)
        if entry is None:
            return None
        if datetime.now() > entry["expires"]:
            # 만료 — 캐시 항목 제거 후 None 반환
            sym_cache.pop(tf, None)
            return None
        return entry["indicators"]

    def _is_daily_stale(self, symbol: str, today: date) -> bool:
        entry = self._daily_cache.get(symbol)
        return entry is None or entry["date"] != today

    # ── 일봉 데이터 조회 + 계산 (blocking, thread pool에서 호출) ──

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
