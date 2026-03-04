"""
키움 OpenAPI+ COM 클라이언트

Windows + 영웅문 HTS 설치 필수.
사용자 ID/PW는 HTS에서 직접 입력 — 서버는 저장하지 않음.
"""
import asyncio
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class KiwoomCOMClient:
    def __init__(self):
        self._ocx = None
        self._event_handlers: list[Callable] = []
        self._request_event = asyncio.Event()

    def _init_ocx(self) -> bool:
        try:
            import win32com.client
            self._ocx = win32com.client.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")
            return True
        except ImportError:
            logger.error("pywin32 미설치 — 키움 COM API 사용 불가 (Windows 전용)")
            return False
        except Exception as e:
            logger.error(f"COM 초기화 실패: {e}")
            return False

    def connect(self) -> bool:
        """이미 로그인된 HTS에 COM 세션 연결"""
        if not self._ocx and not self._init_ocx():
            return False
        try:
            result = self._ocx.CommConnect()
            if result == 0:
                logger.info("키움 COM 연결 성공")
                return True
            logger.error(f"키움 COM 연결 실패: code={result}")
            return False
        except Exception as e:
            logger.error(f"CommConnect 오류: {e}")
            return False

    def is_connected(self) -> bool:
        if not self._ocx:
            return False
        try:
            return self._ocx.GetConnectState() == 1
        except Exception:
            return False

    def get_login_info(self, tag: str) -> str:
        """tag: USER_NAME | USER_ID | ACCNO | GetServerGubun 등"""
        if not self._ocx:
            return ""
        try:
            return self._ocx.GetLoginInfo(tag)
        except Exception:
            return ""

    def get_account_list(self) -> list[str]:
        """보유 계좌 번호 목록"""
        raw = self.get_login_info("ACCNO")
        return [a for a in raw.split(";") if a.strip()]

    # ── TR 데이터 요청 ────────────────────────────────────────

    def set_input_value(self, id_: str, value: str) -> None:
        if self._ocx:
            self._ocx.SetInputValue(id_, value)

    def comm_rq_data(self, rq_name: str, tr_code: str,
                     prev_next: int, screen_no: str) -> int:
        if not self._ocx:
            return -1
        return self._ocx.CommRqData(rq_name, tr_code, prev_next, screen_no)

    def get_comm_data(self, tr_code: str, rq_name: str,
                      index: int, item_name: str) -> str:
        if not self._ocx:
            return ""
        return self._ocx.GetCommData(tr_code, rq_name, index, item_name).strip()

    def get_repeat_cnt(self, tr_code: str, rq_name: str) -> int:
        if not self._ocx:
            return 0
        return self._ocx.GetRepeatCnt(tr_code, rq_name)

    # ── 주문 ─────────────────────────────────────────────────

    def send_order(self, rq_name: str, screen_no: str, account_no: str,
                   order_type: int, code: str, qty: int,
                   price: int, hoga_type: str, org_order_no: str) -> int:
        """
        order_type: 1=매수, 2=매도
        hoga_type: "00"=지정가, "03"=시장가
        """
        if not self._ocx:
            return -1
        return self._ocx.SendOrder(
            rq_name, screen_no, account_no,
            order_type, code, qty, price, hoga_type, org_order_no
        )

    # ── 이벤트 핸들러 (체결 통보) ──────────────────────────────

    def on_receive_chejan_data(self, gubun: str, item_cnt: int,
                               fid_list: str) -> None:
        """
        gubun: "0"=주문체결, "1"=잔고
        체결 이벤트 → logs.db 저장 + WS 브로드캐스트
        """
        if gubun != "0":
            return
        try:
            order_no   = self._get_chejan("주문번호")
            stock_code = self._get_chejan("종목코드").lstrip("A")
            side       = "BUY" if self._get_chejan("주문구분") in ("매수", "+매수") else "SELL"
            qty        = int(self._get_chejan("체결수량") or 0)
            price      = int(self._get_chejan("체결가") or 0)

            logger.info(f"체결 통보: {side} {stock_code} {qty}주 @{price:,}원")

            # 트레이 알림
            try:
                from tray import get_tray
                label = "매수" if side == "BUY" else "매도"
                get_tray().notify("체결 완료", f"{label} {stock_code} {qty}주 @{price:,}원")
            except Exception:
                pass

            from storage.log_db import log_fill, log_execution
            log_fill(order_no=order_no, filled_price=float(price), filled_qty=qty)
            log_execution(
                rule_id=0, rule_name="manual", side=side,
                stock_code=stock_code, quantity=qty,
                status="FILLED", message=f"체결가={price:,}"
            )

            asyncio.create_task(self._broadcast_execution(
                order_no=order_no, stock_code=stock_code,
                side=side, qty=qty, price=price
            ))
        except Exception as e:
            logger.error(f"체결 처리 오류: {e}")

    def _get_chejan(self, fid_name: str) -> str:
        if not self._ocx:
            return ""
        from kiwoom.fid_map import CHEJAN_FID
        fid = CHEJAN_FID.get(fid_name, "")
        return self._ocx.GetChejanData(fid).strip()

    async def _broadcast_execution(self, **kwargs) -> None:
        from routers.ws import broadcast
        await broadcast({"type": "execution_result", "data": kwargs})


_client: KiwoomCOMClient | None = None


def get_client() -> KiwoomCOMClient:
    global _client
    if _client is None:
        _client = KiwoomCOMClient()
    return _client
