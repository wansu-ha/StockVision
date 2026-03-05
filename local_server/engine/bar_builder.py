"""BarBuilder — WS 시세로 1분 OHLCV 분봉 구성.

subscribe_quotes 콜백에서 on_quote()를 호출하면
종목별로 1분 OHLCV를 구성한다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Bar:
    """1분 OHLCV 분봉."""

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class BarBuilder:
    """WS 시세로 1분 OHLCV 구성."""

    def __init__(self) -> None:
        # symbol → 현재 구성 중인 분봉 데이터
        self._current: dict[str, dict] = {}
        # symbol → 직전 완성 분봉
        self._completed: dict[str, Bar] = {}
        # symbol → 최근 시세 (price, volume)
        self._latest: dict[str, dict] = {}

    def on_quote(
        self,
        symbol: str,
        price: Decimal,
        volume: int,
        timestamp: datetime | None = None,
    ) -> None:
        """WS 시세 수신 시 호출."""
        ts = timestamp or datetime.now()
        minute_key = ts.replace(second=0, microsecond=0)

        # 최근 시세 갱신
        self._latest[symbol] = {"price": price, "volume": volume, "timestamp": ts}

        if symbol not in self._current:
            self._current[symbol] = self._new_bar(minute_key, price, volume)
            return

        bar = self._current[symbol]
        if bar["timestamp"] == minute_key:
            # 같은 분 → 업데이트
            bar["high"] = max(bar["high"], price)
            bar["low"] = min(bar["low"], price)
            bar["close"] = price
            bar["volume"] += volume
        else:
            # 분 경계 → 이전 분봉 완성, 새 분봉 시작
            self._completed[symbol] = Bar(
                timestamp=bar["timestamp"],
                open=bar["open"],
                high=bar["high"],
                low=bar["low"],
                close=bar["close"],
                volume=bar["volume"],
            )
            self._current[symbol] = self._new_bar(minute_key, price, volume)

    def get_latest(self, symbol: str) -> Optional[dict]:
        """종목의 최신 시세 조회 (evaluate_all에서 사용)."""
        return self._latest.get(symbol)

    def get_current_bar(self, symbol: str) -> Optional[Bar]:
        """현재 구성 중인 분봉."""
        data = self._current.get(symbol)
        if data is None:
            return None
        return Bar(
            timestamp=data["timestamp"],
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            volume=data["volume"],
        )

    def get_completed_bar(self, symbol: str) -> Optional[Bar]:
        """직전 완성 분봉."""
        return self._completed.get(symbol)

    @staticmethod
    def _new_bar(timestamp: datetime, price: Decimal, volume: int) -> dict:
        return {
            "timestamp": timestamp,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": volume,
        }
