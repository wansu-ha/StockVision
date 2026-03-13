"""local_server.broker.kis.quote: 한국투자증권(KIS) 시세/잔고 조회 모듈"""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

import httpx

from sv_core.broker.models import BalanceResult, Position, QuoteEvent

if TYPE_CHECKING:
    from local_server.broker.kis.auth import KisAuth

logger = logging.getLogger(__name__)

# KIS REST API 기본 URL
KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"

# 모의/실전 구분 트랜젝션 ID
TR_PRICE_REAL = "FHKST01010100"   # 실전 현재가 조회
TR_BALANCE_REAL = "TTTC8434R"     # 실전 잔고 조회


class KisQuote:
    """한국투자증권(KIS) 시세 및 잔고 조회 클라이언트.

    모든 HTTP 요청은 RateLimiter를 통해 호출해야 한다.
    (KisAdapter에서 조합 시 rate_limiter.acquire() 후 호출)
    """

    def __init__(self, auth: "KisAuth", account_no: str, is_mock: bool = False) -> None:
        """초기화.

        Args:
            auth: KisAuth 인스턴스
            account_no: 계좌번호 (예: "50123456-01")
            is_mock: 모의투자 여부
        """
        self._auth = auth
        self._account_no = account_no
        self._is_mock = is_mock

    async def get_price(self, symbol: str) -> QuoteEvent:
        """종목 현재가를 조회한다.

        Args:
            symbol: 종목 코드 (예: "005930")

        Returns:
            QuoteEvent: 현재가 정보

        Raises:
            httpx.HTTPStatusError: API 오류 시
        """
        headers = await self._auth.build_headers()
        headers["tr_id"] = TR_PRICE_REAL
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 주식 시장 구분
            "FID_INPUT_ISCD": symbol,
        }

        url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"

        logger.debug("현재가 조회: %s", symbol)
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()

        data = resp.json()
        output = data.get("output", {})

        return QuoteEvent(
            symbol=symbol,
            price=Decimal(output.get("stck_prpr", "0")),   # 주식 현재가
            volume=int(output.get("acml_vol", "0")),         # 누적 거래량
            bid_price=Decimal(output.get("bidp", "0")) if output.get("bidp") else None,
            ask_price=Decimal(output.get("askp", "0")) if output.get("askp") else None,
            raw=data,
        )

    async def get_balance(self) -> BalanceResult:
        """계좌 잔고 및 보유 포지션을 조회한다.

        Returns:
            BalanceResult: 잔고 및 포지션 정보

        Raises:
            httpx.HTTPStatusError: API 오류 시
        """
        headers = await self._auth.build_headers()
        headers["tr_id"] = TR_BALANCE_REAL
        params = {
            "CANO": self._account_no[:8],         # 계좌번호 앞 8자리
            "ACNT_PRDT_CD": self._account_no[-2:],  # 계좌 상품 코드 (뒤 2자리)
            "AFHR_FLPR_YN": "N",                  # 시간외 단일가 여부
            "OFL_YN": "",                          # 오프라인 여부
            "INQR_DVSN": "02",                    # 조회 구분: 02 = 종목별
            "UNPR_DVSN": "01",                    # 단가 구분
            "FUND_STTL_ICLD_YN": "N",             # 펀드 결제분 포함 여부
            "FNCG_AMT_AUTO_RDPT_YN": "N",         # 융자금액 자동 상환 여부
            "PRCS_DVSN": "00",                    # 처리 구분: 전체
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        url = f"{KIS_BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance"

        logger.debug("잔고 조회: 계좌 %s", self._account_no)
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()

        data = resp.json()
        output1 = data.get("output1", [])  # 종목별 보유 현황
        output2 = data.get("output2", [{}])[0]  # 계좌 잔고 합계

        positions = [
            Position(
                symbol=item.get("pdno", ""),
                qty=int(item.get("hldg_qty", 0)),
                avg_price=Decimal(item.get("pchs_avg_pric", "0")),
                current_price=Decimal(item.get("prpr", "0")),
                eval_amount=Decimal(item.get("evlu_amt", "0")),
                unrealized_pnl=Decimal(item.get("evlu_pfls_amt", "0")),
                unrealized_pnl_rate=Decimal(item.get("evlu_pfls_rt", "0")),
            )
            for item in output1
            if int(item.get("hldg_qty", 0)) > 0  # 보유 수량 있는 종목만
        ]

        cash = Decimal(output2.get("dnca_tot_amt", "0"))        # 예수금 총액
        total_eval = Decimal(output2.get("tot_evlu_amt", "0"))   # 총 평가 금액

        return BalanceResult(
            cash=cash,
            total_eval=total_eval,
            positions=positions,
            raw=data,
        )
