"""local_server.broker.kiwoom.reconciler: 미체결 주문 대사(Reconciliation) 모듈

로컬 상태(메모리)와 키움 서버 상태를 주기적으로 비교하여 불일치를 감지/수정한다.
"""

import asyncio
import logging
from datetime import datetime
from typing import Callable, Optional, TYPE_CHECKING

from sv_core.broker.models import OrderResult, OrderStatus

if TYPE_CHECKING:
    from local_server.broker.kiwoom.order import KiwoomOrder

logger = logging.getLogger(__name__)

# 기본 대사 주기 (초)
DEFAULT_RECONCILE_INTERVAL = 30.0

# 불일치 이벤트 타입
RECONCILE_MISMATCH = "MISMATCH"   # 서버 상태와 로컬 상태 불일치
RECONCILE_ORPHAN = "ORPHAN"       # 로컬에만 있고 서버엔 없는 주문
RECONCILE_GHOST = "GHOST"         # 서버에만 있고 로컬엔 없는 주문


class ReconcileEvent:
    """대사 이벤트"""
    def __init__(
        self,
        event_type: str,
        order_id: str,
        local_status: Optional[OrderStatus],
        server_status: Optional[OrderStatus],
        timestamp: datetime,
    ) -> None:
        self.event_type = event_type
        self.order_id = order_id
        self.local_status = local_status
        self.server_status = server_status
        self.timestamp = timestamp

    def __repr__(self) -> str:
        return (
            f"ReconcileEvent({self.event_type}, {self.order_id}, "
            f"local={self.local_status}, server={self.server_status})"
        )


class Reconciler:
    """미체결 주문 대사 관리자.

    로컬 주문 상태 저장소와 키움 서버 미체결 주문을 주기적으로 비교하여
    불일치 이벤트를 발생시키고, 로컬 상태를 동기화한다.
    """

    def __init__(
        self,
        order_client: "KiwoomOrder",
        interval: float = DEFAULT_RECONCILE_INTERVAL,
    ) -> None:
        """초기화.

        Args:
            order_client: KiwoomOrder 인스턴스
            interval: 대사 주기 (초)
        """
        self._order_client = order_client
        self._interval = interval

        # 로컬 주문 상태 저장소: {order_id: OrderResult}
        self._local_orders: dict[str, OrderResult] = {}

        # 이벤트 콜백
        self._event_callbacks: list[Callable[[ReconcileEvent], None]] = []

        self._task: Optional[asyncio.Task] = None
        self._running = False

    def register_order(self, order: OrderResult) -> None:
        """로컬 주문을 등록한다. (place_order 성공 시 호출)

        Args:
            order: 등록할 주문
        """
        self._local_orders[order.order_id] = order
        logger.debug("주문 등록: %s", order.order_id)

    def update_order(self, order_id: str, new_status: OrderStatus) -> None:
        """로컬 주문 상태를 갱신한다.

        Args:
            order_id: 주문 ID
            new_status: 새 상태
        """
        if order_id in self._local_orders:
            self._local_orders[order_id].status = new_status
            logger.debug("주문 상태 갱신: %s → %s", order_id, new_status.value)

    def remove_order(self, order_id: str) -> None:
        """로컬 주문을 제거한다. (체결/취소 완료 시 호출)

        Args:
            order_id: 제거할 주문 ID
        """
        self._local_orders.pop(order_id, None)

    def on_event(self, callback: Callable[[ReconcileEvent], None]) -> None:
        """대사 이벤트 콜백을 등록한다.

        Args:
            callback: ReconcileEvent를 인자로 받는 함수
        """
        self._event_callbacks.append(callback)

    async def start(self) -> None:
        """대사 태스크를 시작한다."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._reconcile_loop())
        logger.info("Reconciler 시작 (주기: %.0f초)", self._interval)

    async def stop(self) -> None:
        """대사 태스크를 중지한다."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Reconciler 중지")

    async def reconcile_once(self) -> list[ReconcileEvent]:
        """단건 대사를 실행하고 이벤트 목록을 반환한다.

        Returns:
            list[ReconcileEvent]: 발견된 불일치 이벤트
        """
        try:
            server_orders = await self._order_client.get_open_orders()
        except Exception as exc:
            logger.error("대사용 미체결 조회 실패: %s", exc)
            return []

        # 서버 주문을 {order_id: OrderResult}로 변환
        server_map = {o.order_id: o for o in server_orders}

        events: list[ReconcileEvent] = []
        now = datetime.now()

        # 로컬에는 있는데 서버에 없는 주문 (ORPHAN)
        for order_id, local_order in list(self._local_orders.items()):
            if local_order.status in {OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED}:
                # 이미 종결된 주문은 서버 미체결에 없어도 정상
                continue
            if order_id not in server_map:
                events.append(ReconcileEvent(
                    event_type=RECONCILE_ORPHAN,
                    order_id=order_id,
                    local_status=local_order.status,
                    server_status=None,
                    timestamp=now,
                ))
                # 서버에서 사라진 주문 = 체결/취소된 것으로 가정
                self.update_order(order_id, OrderStatus.FILLED)

        # 서버에는 있는데 로컬에 없는 주문 (GHOST)
        for order_id in server_map:
            if order_id not in self._local_orders:
                events.append(ReconcileEvent(
                    event_type=RECONCILE_GHOST,
                    order_id=order_id,
                    local_status=None,
                    server_status=server_map[order_id].status,
                    timestamp=now,
                ))
                # 로컬에 없는 외부 주문 추가
                self._local_orders[order_id] = server_map[order_id]

        # 상태 불일치 (MISMATCH)
        for order_id, local_order in self._local_orders.items():
            if order_id in server_map:
                server_order = server_map[order_id]
                if local_order.status != server_order.status:
                    events.append(ReconcileEvent(
                        event_type=RECONCILE_MISMATCH,
                        order_id=order_id,
                        local_status=local_order.status,
                        server_status=server_order.status,
                        timestamp=now,
                    ))
                    # 서버 상태로 동기화
                    self.update_order(order_id, server_order.status)

        if events:
            logger.warning("대사 불일치 %d건 발견: %s", len(events), events)
            for ev in events:
                self._fire_event(ev)

        return events

    def _fire_event(self, event: ReconcileEvent) -> None:
        """이벤트 콜백들을 호출한다."""
        for cb in self._event_callbacks:
            try:
                cb(event)
            except Exception as exc:
                logger.error("대사 이벤트 콜백 오류: %s", exc, exc_info=True)

    async def _reconcile_loop(self) -> None:
        """대사 루프."""
        while self._running:
            await asyncio.sleep(self._interval)
            if self._running:
                await self.reconcile_once()

    @property
    def local_order_count(self) -> int:
        """로컬 등록된 주문 수를 반환한다."""
        return len(self._local_orders)
