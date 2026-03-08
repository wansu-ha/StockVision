"""DART OpenAPI DataProvider 구현.

한국 상장사 재무제표, 배당 데이터를 금융감독원 DART에서 조회한다.
가격 데이터는 미지원 (DART에 가격 API 없음).
"""
from __future__ import annotations

import io
import logging
import zipfile
from xml.etree import ElementTree

import httpx

from cloud_server.data.provider import (
    DataProvider,
    DividendData,
    FinancialData,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://opendart.fss.or.kr/api"
_TIMEOUT = 15.0

# reprt_code: 분기 → DART 보고서 코드
_QUARTER_MAP = {
    1: "11013",  # 1분기
    2: "11012",  # 반기
    3: "11014",  # 3분기
    4: "11011",  # 사업보고서 (연간)
    None: "11011",
}


class DartProvider(DataProvider):
    """DART OpenAPI 기반 재무/배당 프로바이더."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    @property
    def name(self) -> str:
        return "dart"

    def capabilities(self) -> set[str]:
        return {"financials", "dividends"}

    async def get_financials(
        self,
        corp_code: str,
        year: int,
        quarter: int | None = None,
    ) -> FinancialData | None:
        reprt_code = _QUARTER_MAP.get(quarter, "11011")
        period = f"{year}Q{quarter}" if quarter else str(year)

        # 단일회사 주요 재무지표
        data = await self._call("fnlttSinglAcntAll", {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": reprt_code,
            "fs_div": "CFS",  # 연결재무제표 우선
        })
        if not data:
            return None

        return self._parse_financials(data, corp_code, period)

    async def get_dividends(
        self,
        symbol: str,
        year: int | None = None,
    ) -> list[DividendData]:
        # symbol → corp_code 변환은 호출부(Aggregator)에서 처리
        # 여기서는 symbol을 corp_code로 간주하지 않고, 외부에서 corp_code를 전달받을 수 없으므로
        # DB 조회가 필요하다. 이 구현은 Aggregator가 corp_code를 주입하는 패턴이 아니므로
        # 배당 조회는 Aggregator 레벨에서 corp_code 변환 후 _get_dividends_by_corp를 호출한다.
        return []

    async def get_dividends_by_corp(
        self,
        corp_code: str,
        symbol: str,
        year: int | None = None,
    ) -> list[DividendData]:
        """corp_code 기반 배당 조회 (Aggregator가 symbol→corp_code 변환 후 호출)."""
        if not year:
            return []
        data = await self._call("alotMatter", {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": "11011",
        })
        if not data:
            return []
        return self._parse_dividends(data, symbol, year)

    # ── corp_code 매핑 ────────────────────────────

    async def fetch_corp_codes(self) -> dict[str, str]:
        """DART 고유번호 ZIP → {stock_code: corp_code} 매핑 dict.

        전체 기업 목록을 다운로드하여 종목코드-기업코드 매핑을 반환한다.
        """
        url = f"{_BASE_URL}/corpCode.xml"
        try:
            resp = await self._client.get(url, params={"crtfc_key": self._api_key})
            resp.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                xml_name = zf.namelist()[0]
                xml_data = zf.read(xml_name)

            root = ElementTree.fromstring(xml_data)
            mapping: dict[str, str] = {}
            for corp in root.findall("list"):
                stock_code = (corp.findtext("stock_code") or "").strip()
                corp_code = (corp.findtext("corp_code") or "").strip()
                if stock_code and corp_code:
                    mapping[stock_code] = corp_code

            logger.info("DART corp_code 매핑 로드: %d건", len(mapping))
            return mapping
        except Exception as e:
            logger.error("DART corp_code 매핑 실패: %s", e)
            return {}

    # ── 내부 구현 ─────────────────────────────────

    async def _call(self, endpoint: str, params: dict) -> list[dict] | None:
        """DART API 호출 공통."""
        url = f"{_BASE_URL}/{endpoint}.json"
        params["crtfc_key"] = self._api_key
        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            body = resp.json()
            status = body.get("status")
            if status != "000":
                # 013: 데이터 없음 (정상)
                if status == "013":
                    return None
                logger.warning("DART API %s 오류: status=%s, message=%s",
                               endpoint, status, body.get("message"))
                return None
            return body.get("list", [])
        except Exception as e:
            logger.warning("DART API %s 호출 실패: %s", endpoint, e)
            return None

    @staticmethod
    def _parse_financials(items: list[dict], corp_code: str, period: str) -> FinancialData | None:
        """DART 재무제표 응답 → FinancialData 변환."""
        def _find(account_nm: str) -> int | None:
            for item in items:
                if account_nm in (item.get("account_nm") or ""):
                    raw = (item.get("thstrm_amount") or "").replace(",", "")
                    if raw and raw != "-":
                        try:
                            return int(raw)
                        except ValueError:
                            pass
            return None

        revenue = _find("매출액") or _find("수익(매출액)")
        operating = _find("영업이익")
        net = _find("당기순이익") or _find("당기순손익")
        assets = _find("자산총계")
        equity = _find("자본총계")
        debt = _find("부채총계")

        # 최소 하나라도 데이터가 있어야 유효
        if all(v is None for v in [revenue, operating, net, assets, equity, debt]):
            return None

        # PER/PBR/ROE 등은 주요재무지표 API에서 별도 조회 필요 → 추후 확장
        return FinancialData(
            corp_code=corp_code,
            symbol="",  # 호출부에서 채움
            period=period,
            revenue=revenue,
            operating_income=operating,
            net_income=net,
            total_assets=assets,
            total_equity=equity,
            total_debt=debt,
            eps=None,
            per=None,
            pbr=None,
            roe=None,
            debt_ratio=round(debt / equity * 100, 2) if debt and equity else None,
            extra={},
        )

    @staticmethod
    def _parse_dividends(items: list[dict], symbol: str, year: int) -> list[DividendData]:
        """DART 배당 응답 → list[DividendData] 변환."""
        result: list[DividendData] = []
        for item in items:
            se_nm = item.get("se") or ""
            if "주당" not in se_nm and "배당" not in se_nm:
                continue

            raw = (item.get("thstrm") or "").replace(",", "").replace("-", "")
            if not raw:
                continue
            try:
                dps = float(raw)
            except ValueError:
                continue

            if dps <= 0:
                continue

            result.append(DividendData(
                symbol=symbol,
                fiscal_year=str(year),
                dividend_per_share=dps,
                dividend_yield=None,
                ex_date=None,
                pay_date=None,
                payout_ratio=None,
            ))
            break  # 첫 번째 유효 항목만

        return result
