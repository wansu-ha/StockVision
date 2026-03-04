"""
키움 주문 실행 + 큐 관리

- FIFO 큐: 초당 5건 제한 (200ms 간격)
- 모의투자/실계좌 자동 구분
"""
import asyncio
import logging
import time
from dataclasses import dataclass

from kiwoom.com_client import get_client

logger = logging.getLogger(__name__)

_SCREEN_ORDER  = "2001"
_ORDER_INTERVAL = 0.2  # 200ms (초당 5건)


@dataclass
class OrderRequest:
    account_no: str
    symbol:     str
    side:       str   # "BUY" | "SELL"
    qty:        int
    price:      int   # 0 = 시장가
    order_type: str   # "00"=지정가, "03"=시장가


class KiwoomOrder:
    def __init__(self):
        self._queue: asyncio.Queue[OrderRequest] = asyncio.Queue()
        self._running = False

    def start(self) -> None:
        self._running = True
        asyncio.create_task(self._worker())

    def stop(self) -> None:
        self._running = False

    async def enqueue(self, req: OrderRequest) -> None:
        await self._queue.put(req)

    async def _worker(self) -> None:
        while self._running:
            try:
                req = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                self._send(req)
                await asyncio.sleep(_ORDER_INTERVAL)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"주문 오류: {e}")

    def _send(self, req: OrderRequest) -> None:
        client = get_client()
        order_type = 1 if req.side == "BUY" else 2
        result = client.send_order(
            rq_name="주문요청",
            screen_no=_SCREEN_ORDER,
            account_no=req.account_no,
            order_type=order_type,
            code=req.symbol,
            qty=req.qty,
            price=req.price,
            hoga_type=req.order_type,
            org_order_no="",
        )
        if result == 0:
            logger.info(f"주문 전송 성공: {req.side} {req.symbol} {req.qty}주")
        else:
            logger.error(f"주문 전송 실패: code={result}")


_order_manager: KiwoomOrder | None = None


def get_order_manager() -> KiwoomOrder:
    global _order_manager
    if _order_manager is None:
        _order_manager = KiwoomOrder()
    return _order_manager
