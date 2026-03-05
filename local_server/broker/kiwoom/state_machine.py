"""local_server.broker.kiwoom.state_machine: 브로커 연결 상태 관리 모듈"""

import asyncio
import logging
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """브로커 연결 상태"""
    DISCONNECTED = "DISCONNECTED"      # 미연결
    CONNECTING = "CONNECTING"          # 연결 중
    CONNECTED = "CONNECTED"            # 연결됨 (미인증)
    AUTHENTICATED = "AUTHENTICATED"    # 인증 완료
    SUBSCRIBED = "SUBSCRIBED"          # 시세 구독 중
    ERROR = "ERROR"                    # 오류 상태


# 유효한 상태 전환 정의
# {from_state: {to_state, ...}}
VALID_TRANSITIONS: dict[ConnectionState, set[ConnectionState]] = {
    ConnectionState.DISCONNECTED: {
        ConnectionState.CONNECTING,
    },
    ConnectionState.CONNECTING: {
        ConnectionState.CONNECTED,
        ConnectionState.ERROR,
        ConnectionState.DISCONNECTED,
    },
    ConnectionState.CONNECTED: {
        ConnectionState.AUTHENTICATED,
        ConnectionState.ERROR,
        ConnectionState.DISCONNECTED,
    },
    ConnectionState.AUTHENTICATED: {
        ConnectionState.SUBSCRIBED,
        ConnectionState.ERROR,
        ConnectionState.DISCONNECTED,
    },
    ConnectionState.SUBSCRIBED: {
        ConnectionState.AUTHENTICATED,  # 구독 해제
        ConnectionState.ERROR,
        ConnectionState.DISCONNECTED,
    },
    ConnectionState.ERROR: {
        ConnectionState.DISCONNECTED,
        ConnectionState.CONNECTING,
        ConnectionState.CONNECTED,  # 재연결 시 바로 CONNECTED로 전환 허용
    },
}


class InvalidStateTransitionError(Exception):
    """유효하지 않은 상태 전환 시 발생하는 예외"""
    pass


class StateMachine:
    """브로커 연결 상태 머신.

    상태 전환의 유효성을 검사하고, 상태 변경 시 콜백을 호출한다.
    """

    def __init__(self) -> None:
        self._state = ConnectionState.DISCONNECTED
        self._lock = asyncio.Lock()
        self._on_change_callbacks: list[Callable[[ConnectionState, ConnectionState], None]] = []

    @property
    def state(self) -> ConnectionState:
        """현재 상태를 반환한다."""
        return self._state

    def on_change(self, callback: Callable[[ConnectionState, ConnectionState], None]) -> None:
        """상태 변경 콜백을 등록한다.

        Args:
            callback: (이전 상태, 새 상태)를 인자로 받는 함수
        """
        self._on_change_callbacks.append(callback)

    async def transition(self, new_state: ConnectionState) -> None:
        """상태를 전환한다.

        Args:
            new_state: 전환할 상태

        Raises:
            InvalidStateTransitionError: 유효하지 않은 전환 시
        """
        async with self._lock:
            self._validate(new_state)
            old_state = self._state
            self._state = new_state
            logger.info("상태 전환: %s → %s", old_state.value, new_state.value)

        # 콜백은 락 밖에서 호출 (데드락 방지)
        for cb in self._on_change_callbacks:
            try:
                cb(old_state, new_state)
            except Exception as exc:
                logger.error("상태 변경 콜백 오류: %s", exc, exc_info=True)

    def _validate(self, new_state: ConnectionState) -> None:
        """상태 전환 유효성을 검사한다.

        Args:
            new_state: 전환할 상태

        Raises:
            InvalidStateTransitionError: 유효하지 않은 전환 시
        """
        allowed = VALID_TRANSITIONS.get(self._state, set())
        if new_state not in allowed:
            raise InvalidStateTransitionError(
                f"유효하지 않은 상태 전환: {self._state.value} → {new_state.value} "
                f"(허용: {[s.value for s in allowed]})"
            )

    def is_operational(self) -> bool:
        """운영 가능한 상태인지 반환한다. (주문/시세 가능)"""
        return self._state in {
            ConnectionState.AUTHENTICATED,
            ConnectionState.SUBSCRIBED,
        }

    def reset(self) -> None:
        """상태를 DISCONNECTED로 강제 초기화한다. (비상 복구용)"""
        old = self._state
        self._state = ConnectionState.DISCONNECTED
        logger.warning("상태 머신 강제 초기화: %s → DISCONNECTED", old.value)
