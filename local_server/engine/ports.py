"""engine이 host에게 요구하는 인터페이스 계약 (Ports & Adapters 패턴).

engine/ 내부 모듈은 이 파일의 Protocol과 상수만 참조한다.
host(local_server 나머지)가 구체 구현(Adapter)을 조립하여 주입한다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol

# ── LOG_TYPE 상수 ──
# engine이 쓰는 로그 타입. host의 log_db.py에도 동일 값이 있으나,
# engine은 이 파일에서만 import한다.
# Phase 2에서 sv_runtime/ 이동 시 단일 원천 위치를 재검토.

LOG_TYPE_FILL = "FILL"
LOG_TYPE_ORDER = "ORDER"
LOG_TYPE_ERROR = "ERROR"
LOG_TYPE_STRATEGY = "STRATEGY"
LOG_TYPE_ALERT = "ALERT"


# ── Port Protocols ──


class LogPort(Protocol):
    """실행 로그 기록 포트."""

    async def write(
        self,
        log_type: str,
        message: str,
        *,
        symbol: str | None = None,
        meta: dict[str, Any] | None = None,
        intent_id: str | None = None,
    ) -> None: ...

    def today_realized_pnl(self) -> float: ...

    def today_executed_amount(self) -> Decimal: ...


class BarDataPort(Protocol):
    """분봉 데이터 조회 포트."""

    async def fetch_minute_bars(
        self, symbol: str, tf: str, limit: int,
    ) -> list[dict]: ...


class BarStorePort(Protocol):
    """분봉 저장 포트."""

    def save_bars(self, symbol: str, bars: list[dict]) -> None: ...


class ReferenceDataPort(Protocol):
    """종목 메타(시장 구분) 조회 포트."""

    def get_market_map(self) -> dict[str, str]: ...
