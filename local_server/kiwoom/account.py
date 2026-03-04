"""
키움 계좌/잔고/포지션 조회

TR: opw00001 (예수금), opw00018 (계좌평가잔고)
"""
import logging
import time

from kiwoom.com_client import get_client

logger = logging.getLogger(__name__)

_SCREEN_BALANCE = "1001"
_QUERY_INTERVAL = 0.2  # 초당 5건 제한


class KiwoomAccount:
    def get_account_list(self) -> list[str]:
        return get_client().get_account_list()

    def get_balance(self, account_no: str) -> dict:
        """예수금 + 총평가 조회 (TR: opw00001)"""
        client = get_client()
        client.set_input_value("계좌번호", account_no)
        client.set_input_value("비밀번호", "")
        client.set_input_value("비밀번호입력매체구분", "00")
        client.set_input_value("조회구분", "1")
        client.comm_rq_data("예수금상세현황요청", "opw00001", 0, _SCREEN_BALANCE)
        time.sleep(_QUERY_INTERVAL)

        deposit  = client.get_comm_data("opw00001", "예수금상세현황요청", 0, "예수금")
        total_ev = client.get_comm_data("opw00001", "예수금상세현황요청", 0, "총평가금액")

        return {
            "account_no": account_no,
            "deposit":    int(deposit or 0),
            "total_eval": int(total_ev or 0),
        }

    def get_positions(self, account_no: str) -> list[dict]:
        """보유 종목 목록 (TR: opw00018)"""
        client = get_client()
        client.set_input_value("계좌번호", account_no)
        client.set_input_value("비밀번호", "")
        client.set_input_value("비밀번호입력매체구분", "00")
        client.set_input_value("조회구분", "1")
        client.comm_rq_data("계좌평가잔고내역요청", "opw00018", 0, _SCREEN_BALANCE)
        time.sleep(_QUERY_INTERVAL)

        count = client.get_repeat_cnt("opw00018", "계좌평가잔고내역요청")
        positions = []
        for i in range(count):
            def _get(field: str) -> str:
                return client.get_comm_data("opw00018", "계좌평가잔고내역요청", i, field)
            positions.append({
                "stock_code": _get("종목번호").lstrip("A"),
                "stock_name": _get("종목명"),
                "quantity":   int(_get("보유수량") or 0),
                "avg_price":  int(_get("매입가") or 0),
                "eval_price": int(_get("현재가") or 0),
                "profit_rate": float(_get("수익률(%)") or 0),
            })
        return positions
