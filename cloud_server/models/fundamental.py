"""재무/배당 데이터 모델."""
from datetime import date, datetime

from sqlalchemy import (
    BigInteger, Column, Date, DateTime, Float, Index,
    Integer, String, UniqueConstraint,
)

from cloud_server.core.database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


class CompanyFinancial(Base):
    """기업 재무제표 요약 (DART 등 외부 소스에서 수집)."""

    __tablename__ = "company_financials"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    corp_code        = Column(String(10), nullable=False)  # DART 기업 고유번호
    period           = Column(String(10), nullable=False)  # "2025", "2025Q4"
    revenue          = Column(BigInteger, nullable=True)
    operating_income = Column(BigInteger, nullable=True)
    net_income       = Column(BigInteger, nullable=True)
    total_assets     = Column(BigInteger, nullable=True)
    total_equity     = Column(BigInteger, nullable=True)
    total_debt       = Column(BigInteger, nullable=True)
    eps              = Column(Float, nullable=True)
    per              = Column(Float, nullable=True)
    pbr              = Column(Float, nullable=True)
    roe              = Column(Float, nullable=True)
    debt_ratio       = Column(Float, nullable=True)
    provider         = Column(String(20), nullable=False)  # "dart", "yfinance"
    collected_at     = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("corp_code", "period", "provider", name="uq_financial_corp_period_provider"),
        Index("idx_financial_corp_code", "corp_code"),
    )


class CompanyDividend(Base):
    """기업 배당 데이터."""

    __tablename__ = "company_dividends"

    id                 = Column(Integer, primary_key=True, autoincrement=True)
    symbol             = Column(String(10), nullable=False)
    fiscal_year        = Column(String(4), nullable=False)
    dividend_per_share = Column(Float, nullable=False)
    dividend_yield     = Column(Float, nullable=True)
    ex_date            = Column(Date, nullable=True)
    pay_date           = Column(Date, nullable=True)
    payout_ratio       = Column(Float, nullable=True)
    provider           = Column(String(20), nullable=False)
    collected_at       = Column(DateTime, default=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "fiscal_year", "provider", name="uq_dividend_symbol_year_provider"),
        Index("idx_dividend_symbol", "symbol"),
    )
