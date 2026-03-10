"""local_server.broker.kiwoom.quote: 키움증권 시세/잔고 조회 모듈

KIS와 주요 차이:
- 전부 POST (KIS: GET)
- api-id 헤더로 API 구분 (KIS: tr_id)
- 계좌번호 불필요 (서버 자동 매핑)
- 응답이 flat JSON (KIS: output 중첩)
- 가격에 부호 접두사 있음 (예: "-188200" → abs() 필요)
"""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

import httpx

from sv_core.broker.models import BalanceResult, Position, QuoteEvent

if TYPE_CHECKING:
    from local_server.broker.kiwoom.auth import KiwoomAuth

logger = logging.getLogger(__name__)

# api-id 상수
API_ID_PRICE = "ka10007"       # 시세표성정보 (현재가)
API_ID_BALANCE = "kt00018"     # 계좌평가잔고내역


def _abs_decimal(value: str) -> Decimal:
    """부호가 붙은 가격 문자열을 양수 Decimal로 변환한다."""
    return abs(Decimal(value)) if value else Decimal("0")


class KiwoomQuote:
    """키움증권 시세 및 잔고 조회 클라이언트."""

    def __init__(self, auth: "KiwoomAuth") -> None:
        self._auth = auth

    async def get_price(self, symbol: str) -> QuoteEvent:
        """종목 현재가를 조회한다.

        POST /api/dostk/mrkcond (api-id: ka10007)
        """
        headers = await self._auth.build_headers(API_ID_PRICE)
        body = {"stk_cd": symbol}
        url = f"{self._auth.base_url}/api/dostk/mrkcond"

        logger.debug("현재가 조회: %s", symbol)
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()

        data = resp.json()
        if data.get("return_code") != 0:
            raise RuntimeError(f"현재가 조회 실패: {data.get('return_msg')}")

        return QuoteEvent(
            symbol=symbol,
            price=_abs_decimal(data.get("cur_prc", "0")),
            volume=int(data.get("trde_qty", "0") or "0"),
            bid_price=_abs_decimal(data.get("buy_1bid", "0")) or None,
            ask_price=_abs_decimal(data.get("sel_1bid", "0")) or None,
            raw=data,
        )

    async def get_balance(self) -> BalanceResult:
        """계좌 잔고 및 보유 포지션을 조회한다.

        POST /api/dostk/acnt (api-id: kt00018)
        키움은 계좌번호를 body에 넣지 않는다 (토큰에서 자동 매핑).
        """
        headers = await self._auth.build_headers(API_ID_BALANCE)
        body = {"qry_tp": "0", "dmst_stex_tp": "00"}
        url = f"{self._auth.base_url}/api/dostk/acnt"

        logger.debug("잔고 조회")
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()

        data = resp.json()
        logger.debug("잔고 raw 응답: %s", data)
        if data.get("return_code") != 0:
            raise RuntimeError(f"잔고 조회 실패: {data.get('return_msg')}")

        # 보유 종목 파싱
        stock_list = data.get("acnt_evlt_remn_indv_tot", [])
        positions = [
            Position(
                symbol=item.get("stk_cd", ""),
                qty=int(item.get("hldg_qty", 0)),
                avg_price=_abs_decimal(item.get("avg_pur_prc", "0")),
                current_price=_abs_decimal(item.get("cur_prc", "0")),
                eval_amount=_abs_decimal(item.get("evlt_amt", "0")),
                unrealized_pnl=Decimal(item.get("evlt_pl", "0") or "0"),
                unrealized_pnl_rate=Decimal(item.get("evlt_pl_rt", "0") or "0"),
            )
            for item in stock_list
            if int(item.get("hldg_qty", 0)) > 0
        ]

        # 예수금: prsm_dpst_aset_amt (추정예수금자산총액)
        cash = _abs_decimal(data.get("prsm_dpst_aset_amt", "0"))
        # 총 평가 = 예수금 + 주식 평가
        stock_eval = _abs_decimal(data.get("tot_evlt_amt", "0"))
        total_eval = cash + stock_eval

        return BalanceResult(
            cash=cash,
            total_eval=total_eval,
            positions=positions,
            raw=data,
        )
