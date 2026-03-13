"""DataAggregator — 복수 DataProvider 우선순위 라우팅.

capabilities 기반으로 적절한 프로바이더를 선택하고,
실패 시 다음 프로바이더로 폴백한다.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date

from cloud_server.data.provider import (
    DailyBar,
    DataProvider,
    DividendData,
    FinancialData,
    ProviderQuote,
)

logger = logging.getLogger(__name__)

_PROVIDER_TIMEOUT = 10.0  # 프로바이더별 타임아웃 (초)


class DataAggregator:
    """복수 DataProvider를 우선순위 기반으로 조회한다."""

    def __init__(self, providers: list[DataProvider]) -> None:
        self._providers = {p.name: p for p in providers}
        self._priority = [p.name for p in providers]

    async def get_daily_bars(
        self,
        symbol: str,
        start: date,
        end: date,
        preferred: str | None = None,
    ) -> list[DailyBar]:
        order = self._resolve_order("price", preferred)
        for name in order:
            provider = self._providers[name]
            if not await provider.supports_symbol(symbol):
                continue
            try:
                bars = await asyncio.wait_for(
                    provider.get_daily_bars(symbol, start, end),
                    timeout=_PROVIDER_TIMEOUT,
                )
                if bars:
                    logger.debug("daily_bars %s: provider=%s, count=%d", symbol, name, len(bars))
                    return bars
            except asyncio.TimeoutError:
                logger.warning("daily_bars 타임아웃: provider=%s, symbol=%s", name, symbol)
            except Exception as e:
                logger.warning("daily_bars 실패: provider=%s, symbol=%s, error=%s", name, symbol, e)

        logger.error("daily_bars 전체 실패: symbol=%s", symbol)
        return []

    async def get_quote(
        self,
        symbol: str,
        preferred: str | None = None,
    ) -> ProviderQuote | None:
        order = self._resolve_order("quote", preferred)
        for name in order:
            provider = self._providers[name]
            if not await provider.supports_symbol(symbol):
                continue
            try:
                quote = await asyncio.wait_for(
                    provider.get_quote(symbol),
                    timeout=_PROVIDER_TIMEOUT,
                )
                if quote:
                    return quote
            except asyncio.TimeoutError:
                logger.warning("quote 타임아웃: provider=%s, symbol=%s", name, symbol)
            except Exception as e:
                logger.warning("quote 실패: provider=%s, symbol=%s, error=%s", name, symbol, e)

        logger.error("quote 전체 실패: symbol=%s", symbol)
        return None

    async def get_financials(
        self,
        corp_code: str,
        year: int,
        quarter: int | None = None,
    ) -> FinancialData | None:
        for name in self._priority:
            provider = self._providers[name]
            if "financials" not in provider.capabilities():
                continue
            try:
                result = await asyncio.wait_for(
                    provider.get_financials(corp_code, year, quarter),
                    timeout=_PROVIDER_TIMEOUT,
                )
                if result:
                    return result
            except asyncio.TimeoutError:
                logger.warning("financials 타임아웃: provider=%s, corp=%s", name, corp_code)
            except Exception as e:
                logger.warning("financials 실패: provider=%s, corp=%s, error=%s", name, corp_code, e)
        return None

    async def get_dividends(
        self,
        symbol: str,
        year: int | None = None,
    ) -> list[DividendData]:
        for name in self._priority:
            provider = self._providers[name]
            if "dividends" not in provider.capabilities():
                continue
            try:
                result = await asyncio.wait_for(
                    provider.get_dividends(symbol, year),
                    timeout=_PROVIDER_TIMEOUT,
                )
                if result:
                    return result
            except asyncio.TimeoutError:
                logger.warning("dividends 타임아웃: provider=%s, symbol=%s", name, symbol)
            except Exception as e:
                logger.warning("dividends 실패: provider=%s, symbol=%s, error=%s", name, symbol, e)
        return []

    def _resolve_order(self, capability: str, preferred: str | None) -> list[str]:
        """capability를 지원하는 프로바이더를 우선순위 순으로 반환."""
        candidates = [
            n for n in self._priority
            if capability in self._providers[n].capabilities()
        ]
        if preferred and preferred in candidates:
            rest = [n for n in candidates if n != preferred]
            return [preferred] + rest
        return candidates
