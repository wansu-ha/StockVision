"""DataAggregator 팩토리.

앱 시작 시 호출하여 가용 프로바이더로 Aggregator를 구성한다.
"""
from __future__ import annotations

import logging

from cloud_server.core.config import settings
from cloud_server.data.aggregator import DataAggregator
from cloud_server.data.provider import DataProvider
from cloud_server.data.yfinance_provider import YFinanceProvider

logger = logging.getLogger(__name__)

_aggregator: DataAggregator | None = None


def create_aggregator(market_lookup: dict[str, str] | None = None) -> DataAggregator:
    """가용 프로바이더로 DataAggregator를 생성한다."""
    providers: list[DataProvider] = []

    # DART (재무/배당 정본)
    if settings.DART_API_KEY:
        from cloud_server.data.dart_provider import DartProvider
        providers.append(DartProvider(settings.DART_API_KEY))
        logger.info("DataProvider 등록: dart")

    # YFinance (가격/배당 폴백, 항상 가용)
    providers.append(YFinanceProvider(market_lookup=market_lookup))
    logger.info("DataProvider 등록: yfinance")

    return DataAggregator(providers)


def get_aggregator() -> DataAggregator:
    """앱 전역 Aggregator 인스턴스를 반환한다."""
    global _aggregator
    if _aggregator is None:
        _aggregator = create_aggregator()
    return _aggregator


def set_aggregator(agg: DataAggregator) -> None:
    """테스트 또는 lifespan에서 Aggregator를 주입한다."""
    global _aggregator
    _aggregator = agg
