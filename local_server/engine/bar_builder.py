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

from local_server.engine.ports import BarStorePort

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

    def __init__(self, bar_store: BarStorePort | None = None) -> None:
        # symbol → 현재 구성 중인 분봉 데이터
        self._current: dict[str, dict] = {}
        # symbol → 직전 완성 분봉
        self._completed: dict[str, Bar] = {}
        # symbol → 최근 시세 (price, volume)
        self._latest: dict[str, dict] = {}
        self._bar_store = bar_store

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
            completed = Bar(
                timestamp=bar["timestamp"],
                open=bar["open"],
                high=bar["high"],
                low=bar["low"],
                close=bar["close"],
                volume=bar["volume"],
            )
            self._completed[symbol] = completed

            # MinuteBarStore에 완성 분봉 저장
            if self._bar_store is not None:
                try:
                    self._bar_store.save_bars(symbol, [{
                        "time": completed.timestamp.isoformat(),
                        "open": float(completed.open),
                        "high": float(completed.high),
                        "low": float(completed.low),
                        "close": float(completed.close),
                        "volume": completed.volume,
                    }])
                except Exception as e:
                    logger.warning("분봉 저장 실패 (%s): %s", symbol, e)

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

    async def fill_gap(self, symbol: str, broker) -> int:
        """WS 끊김 동안 누락된 분봉을 REST 현재가로 보충한다.

        Returns:
            보충된 분봉 수 (0이면 gap 없음)
        """
        latest = self._latest.get(symbol)
        if not latest or "timestamp" not in latest:
            return 0

        now = datetime.now()
        last = latest["timestamp"]
        gap_minutes = (now - last).total_seconds() / 60

        if gap_minutes < 2:
            return 0

        try:
            quote = await broker.get_quote(symbol)
            price = quote.price if hasattr(quote, "price") else Decimal(0)
            if price > 0:
                self.on_quote(symbol, price, 0, now)
                return 1
        except Exception as e:
            logger.error("분봉 gap fill 실패 (%s): %s", symbol, e)

        return 0

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
