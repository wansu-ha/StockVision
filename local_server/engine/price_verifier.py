"""PriceVerifier — 주문 전 가격 검증.

WS로 수신한 가격과 REST로 재조회한 가격의 괴리를 체크한다.
괴리 > 임계값(기본 1%)이면 주문을 거부한다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sv_core.broker.base import BrokerAdapter

logger = logging.getLogger(__name__)


@dataclass
class VerifyResult:
    """가격 검증 결과."""

    ok: bool
    actual_price: Decimal
    expected_price: Decimal
    diff_pct: Decimal


class PriceVerifier:
    """주문 전 BrokerAdapter.get_quote()로 현재가를 재확인."""

    TOLERANCE_PCT = Decimal("1.0")  # 1% 괴리 허용

    def __init__(self, broker: BrokerAdapter) -> None:
        self._broker = broker

    async def verify(self, symbol: str, expected_price: Decimal) -> VerifyResult:
        """가격 검증.

        Args:
            symbol: 종목 코드
            expected_price: WS에서 수신한 가격

        Returns:
            VerifyResult (ok=True면 통과)
        """
        if expected_price <= 0:
            return VerifyResult(
                ok=False,
                actual_price=Decimal(0),
                expected_price=expected_price,
                diff_pct=Decimal("999"),
            )

        try:
            quote = await self._broker.get_quote(symbol)
            actual_price = quote.price
        except Exception:
            logger.exception("가격 조회 실패: %s", symbol)
            return VerifyResult(
                ok=False,
                actual_price=Decimal(0),
                expected_price=expected_price,
                diff_pct=Decimal("999"),
            )

        diff_pct = abs(actual_price - expected_price) / expected_price * 100
        ok = diff_pct <= self.TOLERANCE_PCT

        if not ok:
            logger.warning(
                "가격 괴리 초과: %s (WS=%s, REST=%s, 괴리=%.2f%%)",
                symbol, expected_price, actual_price, diff_pct,
            )

        return VerifyResult(
            ok=ok,
            actual_price=actual_price,
            expected_price=expected_price,
            diff_pct=diff_pct,
        )
