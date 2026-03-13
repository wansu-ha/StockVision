"""DataProvider ABC 및 데이터 클래스.

시장 데이터(가격, 재무, 배당)를 통합 인터페이스로 제공한다.
BrokerAdapter(주문 실행)와 명확히 분리된 읽기 전용 추상화.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class DailyBar:
    """일봉 데이터 한 건."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class ProviderQuote:
    """현재가 스냅샷 (REST 단건 조회용)."""

    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    timestamp: str  # ISO 8601


@dataclass
class FinancialData:
    """재무 데이터."""

    corp_code: str
    symbol: str
    period: str  # "2025Q4", "2025"
    revenue: int | None
    operating_income: int | None
    net_income: int | None
    total_assets: int | None
    total_equity: int | None
    total_debt: int | None
    eps: float | None
    per: float | None
    pbr: float | None
    roe: float | None
    debt_ratio: float | None
    extra: dict = field(default_factory=dict)


@dataclass
class DividendData:
    """배당 데이터."""

    symbol: str
    fiscal_year: str
    dividend_per_share: float
    dividend_yield: float | None
    ex_date: date | None
    pay_date: date | None
    payout_ratio: float | None


class DataProvider(ABC):
    """시장 데이터 제공자 추상 기반 클래스.

    읽기 전용. 각 프로바이더는 자기가 지원하는 기능만 오버라이드한다.
    기본 구현은 빈 값(None/[])을 반환하므로 미지원 메서드를 구현할 의무 없음.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """프로바이더 식별자 (예: "yfinance", "kis", "dart")."""

    @abstractmethod
    def capabilities(self) -> set[str]:
        """이 프로바이더가 지원하는 기능 목록.

        가능한 값: "price", "quote", "financials", "dividends", "disclosure"
        """

    # ── 가격 (price) ──────────────────────────────

    async def get_daily_bars(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> list[DailyBar]:
        """일봉 OHLCV를 조회한다."""
        return []

    async def get_quote(self, symbol: str) -> Optional[ProviderQuote]:
        """지연 시세를 단건 조회한다 (REST, 캐시/종가 기반)."""
        return None

    # ── 재무 (financials) ─────────────────────────

    async def get_financials(
        self,
        corp_code: str,
        year: int,
        quarter: int | None = None,
    ) -> FinancialData | None:
        """재무제표 요약을 조회한다."""
        return None

    # ── 배당 (dividends) ──────────────────────────

    async def get_dividends(
        self,
        symbol: str,
        year: int | None = None,
    ) -> list[DividendData]:
        """배당 이력을 조회한다."""
        return []

    # ── 공통 ──────────────────────────────────────

    async def supports_symbol(self, symbol: str) -> bool:
        """해당 종목을 지원하는지 확인한다."""
        return True
