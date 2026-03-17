"""local_server.broker.kis.order: 한국투자증권(KIS) 주문 실행/취소 모듈"""

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
    from local_server.broker.kis.auth import KisAuth

logger = logging.getLogger(__name__)

KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"

# K1: 실전 주문 tr_id 매핑
# KIS API 문서 기준: 매수/매도 모두 TTTC0801U 사용 가능.
# SLL_TYPE("01"=매수, "02"=매도) + ORD_DVSN("00"=지정가, "01"=시장가)으로 구분.
# TTTC0802U는 매수 시장가 전용 (KIS 포털 "주식주문(시장가)" 참조).
_ORDER_TR_ID: dict[tuple[OrderSide, OrderType], str] = {
    (OrderSide.BUY, OrderType.MARKET): "TTTC0802U",   # 매수 시장가
    (OrderSide.BUY, OrderType.LIMIT): "TTTC0801U",    # 매수 지정가
    (OrderSide.SELL, OrderType.MARKET): "TTTC0801U",  # 매도 시장가
    (OrderSide.SELL, OrderType.LIMIT): "TTTC0801U",   # 매도 지정가
}

# 모의투자 주문 tr_id 매핑 (V 접두어, 동일 구조)
_MOCK_ORDER_TR_ID: dict[tuple[OrderSide, OrderType], str] = {
    (OrderSide.BUY, OrderType.MARKET): "VTTC0802U",
    (OrderSide.BUY, OrderType.LIMIT): "VTTC0801U",
    (OrderSide.SELL, OrderType.MARKET): "VTTC0801U",
    (OrderSide.SELL, OrderType.LIMIT): "VTTC0801U",
}

# 주문 구분 코드 (ord_dvsn)
_ORD_DVSN: dict[tuple[OrderSide, OrderType], str] = {
    (OrderSide.BUY, OrderType.MARKET): "01",   # 시장가 매수
    (OrderSide.BUY, OrderType.LIMIT): "00",    # 지정가 매수
    (OrderSide.SELL, OrderType.MARKET): "01",  # 시장가 매도
    (OrderSide.SELL, OrderType.LIMIT): "00",   # 지정가 매도
}

# 매매 구분 코드
_SIDE_CODE: dict[OrderSide, str] = {
    OrderSide.BUY: "01",   # 매수
    OrderSide.SELL: "02",  # 매도
}

TR_CANCEL = "TTTC0803U"           # 주문 취소 (실전)
TR_CANCEL_MOCK = "VTTC0803U"      # 주문 취소 (모의)
TR_OPEN_ORDERS = "TTTC8036R"      # 미체결 조회 (실전)
TR_OPEN_ORDERS_MOCK = "VTTC8036R"  # 미체결 조회 (모의)


class KisOrder:
    """한국투자증권(KIS) 주문 실행/취소/미체결 조회 클라이언트."""

    def __init__(
        self,
        auth: "KisAuth",
        account_no: str,
        is_mock: bool = False,
    ) -> None:
        """초기화.

        Args:
            auth: KisAuth 인스턴스
            account_no: 계좌번호
            is_mock: 모의투자 여부
        """
        self._auth = auth
        self._account_no = account_no
        self._is_mock = is_mock

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

        Args:
            client_order_id: 클라이언트 주문 ID (멱등성 키)
            symbol: 종목 코드
            side: 매수/매도
            order_type: 시장가/지정가
            qty: 주문 수량
            limit_price: 지정가 (시장가면 0 또는 None)

        Returns:
            OrderResult: 주문 결과

        Raises:
            ValueError: 지정가 주문인데 limit_price가 없는 경우
            httpx.HTTPStatusError: API 오류 시
        """
        if order_type == OrderType.LIMIT and not limit_price:
            raise ValueError("지정가 주문에는 limit_price가 필요합니다")

        tr_map = _MOCK_ORDER_TR_ID if self._is_mock else _ORDER_TR_ID
        tr_id = tr_map[(side, order_type)]
        ord_dvsn = _ORD_DVSN[(side, order_type)]

        headers = await self._auth.build_headers()
        headers["tr_id"] = tr_id

        body = {
            "CANO": self._account_no[:8],
            "ACNT_PRDT_CD": self._account_no[-2:],
            "PDNO": symbol,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(int(limit_price)) if limit_price else "0",
            "SLL_TYPE": _SIDE_CODE[side],
        }

        url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"

        logger.info(
            "주문 실행: %s %s %s %d주 @ %s (client_id=%s)",
            side.value, order_type.value, symbol, qty, limit_price, client_order_id,
        )
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()

        data = resp.json()
        output = data.get("output", {})
        order_id = output.get("ODNO", "")  # 주문 번호

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

        Args:
            order_id: 브로커 주문 ID
            symbol: 종목 코드 (취소 요청 시 필요)
            qty: 취소할 수량

        Returns:
            OrderResult: 취소된 주문 정보

        Raises:
            httpx.HTTPStatusError: API 오류 시
        """
        headers = await self._auth.build_headers()
        headers["tr_id"] = TR_CANCEL_MOCK if self._is_mock else TR_CANCEL

        body = {
            "CANO": self._account_no[:8],
            "ACNT_PRDT_CD": self._account_no[-2:],
            "KRX_FWDG_ORD_ORGNO": "",  # 한국거래소 전송 주문 조직 번호
            "ORGN_ODNO": order_id,      # 원주문 번호
            "ORD_DVSN": "00",           # 취소 구분
            "RVSE_CNCL_DVSN_CD": "02", # 정정취소구분: 02 = 취소
            "ORD_QTY": str(qty),
            "ORD_UNPR": "0",
            "QTY_ALL_ORD_YN": "Y",      # 잔량 전부 취소
        }

        url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/trading/order-rvsecncl"

        logger.info("주문 취소: order_id=%s symbol=%s qty=%d", order_id, symbol, qty)
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()

        data = resp.json()
        return OrderResult(
            order_id=order_id,
            client_order_id="",
            symbol=symbol,
            side=OrderSide.BUY,  # 취소는 방향 무관, 원주문 방향 불명
            order_type=OrderType.MARKET,
            qty=qty,
            limit_price=None,
            status=OrderStatus.CANCELLED,
            raw=data,
        )

    async def get_open_orders(self) -> list[OrderResult]:
        """미체결 주문 목록을 조회한다.

        Returns:
            list[OrderResult]: 미체결 주문 목록

        Raises:
            httpx.HTTPStatusError: API 오류 시
        """
        headers = await self._auth.build_headers()
        headers["tr_id"] = TR_OPEN_ORDERS_MOCK if self._is_mock else TR_OPEN_ORDERS

        params = {
            "CANO": self._account_no[:8],
            "ACNT_PRDT_CD": self._account_no[-2:],
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
            "SLL_BUY_DVSN_CD": "00",  # 매도/매수 구분: 00 = 전체
            "INQR_DVSN_3": "00",      # 조회 구분
            "INQR_DVSN_1": "",
        }

        url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"

        logger.debug("미체결 주문 조회")
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()

        data = resp.json()
        output = data.get("output", [])

        results: list[OrderResult] = []
        for item in output:
            side_code = item.get("sll_buy_dvsn_cd", "01")
            side = OrderSide.SELL if side_code == "02" else OrderSide.BUY

            ord_dvsn = item.get("ord_dvsn_cd", "01")
            order_type = OrderType.MARKET if ord_dvsn == "01" else OrderType.LIMIT

            limit_price_str = item.get("ord_unpr", "0")
            limit_price = Decimal(limit_price_str) if limit_price_str != "0" else None

            results.append(OrderResult(
                order_id=item.get("odno", ""),
                client_order_id="",
                symbol=item.get("pdno", ""),
                side=side,
                order_type=order_type,
                qty=int(item.get("ord_qty", 0)),
                limit_price=limit_price,
                status=OrderStatus.SUBMITTED,
                filled_qty=int(item.get("tot_ccld_qty", 0)),
                raw=item,
            ))

        return results
