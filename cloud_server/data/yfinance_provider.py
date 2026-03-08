"""YFinance DataProvider 구현.

가격(일봉), 현재가, 배당 데이터를 Yahoo Finance에서 조회한다.
한국 주식(.KS/.KQ), 미국 주식, 지수(^), 환율(=X) 지원.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

from cloud_server.data.provider import (
    DailyBar,
    DataProvider,
    DividendData,
    ProviderQuote,
)

logger = logging.getLogger(__name__)


class YFinanceProvider(DataProvider):
    """Yahoo Finance 기반 데이터 프로바이더."""

    def __init__(self, market_lookup: dict[str, str] | None = None) -> None:
        # symbol → market ("KOSPI"/"KOSDAQ") 매핑. Aggregator가 StockMaster에서 주입.
        self._market_lookup: dict[str, str] = market_lookup or {}

    @property
    def name(self) -> str:
        return "yfinance"

    def capabilities(self) -> set[str]:
        return {"price", "quote", "dividends"}

    async def get_daily_bars(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> list[DailyBar]:
        yf_symbol = self._to_yf_symbol(symbol)
        return await asyncio.to_thread(self._fetch_daily, yf_symbol, start, end)

    async def get_quote(self, symbol: str) -> ProviderQuote | None:
        yf_symbol = self._to_yf_symbol(symbol)
        return await asyncio.to_thread(self._fetch_quote, yf_symbol, symbol)

    async def get_dividends(
        self,
        symbol: str,
        year: int | None = None,
    ) -> list[DividendData]:
        yf_symbol = self._to_yf_symbol(symbol)
        return await asyncio.to_thread(self._fetch_dividends, yf_symbol, symbol, year)

    async def supports_symbol(self, symbol: str) -> bool:
        # 6자리 숫자(한국), 알파벳(미국), ^접두어(지수), =X(환율)
        return True

    # ── 내부 구현 (sync, to_thread로 호출) ────────

    def _fetch_daily(self, yf_symbol: str, start: date, end: date) -> list[DailyBar]:
        try:
            df = yf.download(
                yf_symbol,
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),
                auto_adjust=True,
                progress=False,
            )
            if df.empty:
                return []

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            bars: list[DailyBar] = []
            for ts, row in df.iterrows():
                close_val = row.get("Close")
                if close_val is None or (isinstance(close_val, float) and np.isnan(close_val)):
                    continue
                bars.append(DailyBar(
                    date=ts.date() if hasattr(ts, "date") else ts,
                    open=self._to_float(row.get("Open")),
                    high=self._to_float(row.get("High")),
                    low=self._to_float(row.get("Low")),
                    close=self._to_float(close_val),
                    volume=int(row.get("Volume", 0)),
                ))
            return bars
        except Exception as e:
            logger.warning("yfinance daily bars 실패 %s: %s", yf_symbol, e)
            return []

    def _fetch_quote(self, yf_symbol: str, internal_symbol: str) -> ProviderQuote | None:
        try:
            ticker = yf.Ticker(yf_symbol)
            info = ticker.fast_info
            price = float(info.get("lastPrice", 0) or info.get("previousClose", 0))
            prev = float(info.get("previousClose", 0))
            change = price - prev if prev else 0.0
            change_pct = (change / prev * 100) if prev else 0.0
            return ProviderQuote(
                symbol=internal_symbol,
                price=price,
                change=round(change, 2),
                change_pct=round(change_pct, 4),
                volume=int(info.get("lastVolume", 0)),
                timestamp=datetime.utcnow().isoformat(),
            )
        except Exception as e:
            logger.warning("yfinance quote 실패 %s: %s", yf_symbol, e)
            return None

    def _fetch_dividends(
        self, yf_symbol: str, internal_symbol: str, year: int | None,
    ) -> list[DividendData]:
        try:
            ticker = yf.Ticker(yf_symbol)
            divs = ticker.dividends
            if divs is None or divs.empty:
                return []

            result: list[DividendData] = []
            # 연도별 합산
            yearly: dict[str, float] = {}
            for ts, amount in divs.items():
                yr = str(ts.year)
                if year and yr != str(year):
                    continue
                yearly[yr] = yearly.get(yr, 0.0) + float(amount)

            for yr, total in yearly.items():
                result.append(DividendData(
                    symbol=internal_symbol,
                    fiscal_year=yr,
                    dividend_per_share=round(total, 2),
                    dividend_yield=None,
                    ex_date=None,
                    pay_date=None,
                    payout_ratio=None,
                ))
            return result
        except Exception as e:
            logger.warning("yfinance dividends 실패 %s: %s", yf_symbol, e)
            return []

    # ── 심볼 변환 ─────────────────────────────────

    def _to_yf_symbol(self, symbol: str) -> str:
        """내부 심볼 → yfinance 심볼 변환."""
        if symbol.startswith("^") or "=" in symbol:
            return symbol
        if symbol.isdigit() and len(symbol) == 6:
            market = self._market_lookup.get(symbol, "").upper()
            if market == "KOSDAQ":
                return f"{symbol}.KQ"
            return f"{symbol}.KS"  # KOSPI 기본값
        return symbol

    @staticmethod
    def _to_float(value) -> float:
        if value is None:
            return 0.0
        try:
            f = float(value)
            return 0.0 if np.isnan(f) else round(f, 2)
        except (TypeError, ValueError):
            return 0.0
