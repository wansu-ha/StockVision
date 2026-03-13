"""local_server.broker.kiwoom.order: 키움증권 주문 실행/취소 모듈

KIS와 주요 차이:
- 전부 POST /api/dostk/ordr (KIS: /uapi/.../order-cash)
- api-id로 매수/매도/취소 구분 (KIS: tr_id)
- 계좌번호 불필요 (서버 자동 매핑)
- 거래소 구분: dmst_stex_tp (KRX=한국거래소, NXT=넥스트, SOR=최선주문)
- 주문유형: trde_tp (0=보통/지정가, 3=시장가)
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

import httpx

from sv_core.broker.models import (
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
)

if TYPE_CHECKING:
    from local_server.broker.kiwoom.auth import KiwoomAuth

logger = logging.getLogger(__name__)

# api-id 상수
API_ID_BUY = "kt10000"            # 매수
API_ID_SELL = "kt10001"           # 매도
API_ID_CANCEL = "kt10003"         # 취소
API_ID_OPEN_ORDERS = "ka10075"    # 미체결

# 매수/매도 → api-id 매핑
_SIDE_API_ID: dict[OrderSide, str] = {
    OrderSide.BUY: API_ID_BUY,
    OrderSide.SELL: API_ID_SELL,
}

# 주문 유형 → trde_tp 매핑
_ORDER_TYPE_CODE: dict[OrderType, str] = {
    OrderType.LIMIT: "0",     # 보통(지정가)
    OrderType.MARKET: "3",    # 시장가
}


class KiwoomOrder:
    """키움증권 주문 실행/취소/미체결 조회 클라이언트."""

    def __init__(self, auth: "KiwoomAuth") -> None:
        self._auth = auth

    async def place_order(
        self,
        client_order_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        qty: int,
        limit_price: Optional[Decimal] = None,
    ) -> OrderResult:
        """주문을 실행한다.

        POST /api/dostk/ordr (api-id: kt10000 매수 / kt10001 매도)
        """
        if order_type == OrderType.LIMIT and not limit_price:
            raise ValueError("지정가 주문에는 limit_price가 필요합니다")

        api_id = _SIDE_API_ID[side]
        headers = await self._auth.build_headers(api_id)

        body = {
            "dmst_stex_tp": "KRX",  # 한국거래소 (KOSPI/KOSDAQ 통합)
            "stk_cd": symbol,
            "ord_qty": str(qty),
            "trde_tp": _ORDER_TYPE_CODE[order_type],
            "ord_uv": str(int(limit_price)) if limit_price else "0",
        }

        url = f"{self._auth.base_url}/api/dostk/ordr"

        logger.info(
            "주문 실행: %s %s %s %d주 @ %s (client_id=%s)",
            side.value, order_type.value, symbol, qty, limit_price, client_order_id,
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()

        data = resp.json()
        if data.get("return_code") != 0:
            raise RuntimeError(
                f"주문 실패: {data.get('return_msg', 'unknown error')}"
            )

        order_id = data.get("ord_no", "")

        return OrderResult(
            order_id=order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=qty,
            limit_price=limit_price,
            status=OrderStatus.SUBMITTED,
            submitted_at=datetime.now(),
            raw=data,
        )

    async def cancel_order(self, order_id: str, symbol: str, qty: int) -> OrderResult:
        """주문을 취소한다.

        POST /api/dostk/ordr (api-id: kt10003)
        cncl_qty=0 → 잔량 전부 취소
        """
        headers = await self._auth.build_headers(API_ID_CANCEL)

        body = {
            "dmst_stex_tp": "KRX",
            "orig_ord_no": order_id,
            "stk_cd": symbol,
            "cncl_qty": "0",  # 잔량 전부 취소
        }

        url = f"{self._auth.base_url}/api/dostk/ordr"

        logger.info("주문 취소: order_id=%s symbol=%s", order_id, symbol)
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()

        data = resp.json()
        return OrderResult(
            order_id=order_id,
            client_order_id="",
            symbol=symbol,
            side=OrderSide.BUY,  # 취소는 방향 무관
            order_type=OrderType.MARKET,
            qty=qty,
            limit_price=None,
            status=OrderStatus.CANCELLED,
            raw=data,
        )

    async def get_open_orders(self) -> list[OrderResult]:
        """미체결 주문 목록을 조회한다.

        POST /api/dostk/acnt (api-id: ka10075)
        """
        headers = await self._auth.build_headers(API_ID_OPEN_ORDERS)

        body = {
            "all_stk_tp": "0",
            "trde_tp": "0",
            "stex_tp": "00",
            "stk_cd": "",
        }

        url = f"{self._auth.base_url}/api/dostk/acnt"

        logger.debug("미체결 주문 조회")
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()

        data = resp.json()
        items = data.get("oso", [])

        results: list[OrderResult] = []
        for item in items:
            side_str = item.get("sell_tp", "")
            side = OrderSide.SELL if side_str == "1" else OrderSide.BUY

            trde_tp = item.get("trde_tp", "0")
            order_type = OrderType.MARKET if trde_tp == "3" else OrderType.LIMIT

            price_str = item.get("ord_uv", "0")
            limit_price = Decimal(price_str) if price_str and price_str != "0" else None

            results.append(OrderResult(
                order_id=item.get("ord_no", ""),
                client_order_id="",
                symbol=item.get("stk_cd", ""),
                side=side,
                order_type=order_type,
                qty=int(item.get("ord_qty", 0)),
                limit_price=limit_price,
                status=OrderStatus.SUBMITTED,
                filled_qty=int(item.get("ccld_qty", 0)),
                raw=item,
            ))

        return results
