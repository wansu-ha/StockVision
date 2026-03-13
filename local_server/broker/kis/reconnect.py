"""local_server.broker.kis.reconnect: WebSocket 자동 재연결 관리 모듈"""

import asyncio
import logging
from typing import Callable, Awaitable, Optional

from local_server.broker.kis.state_machine import ConnectionState, StateMachine

logger = logging.getLogger(__name__)

# 재연결 기본 설정
DEFAULT_INITIAL_DELAY = 1.0    # 첫 재연결 대기 (초)
DEFAULT_MAX_DELAY = 60.0       # 최대 재연결 대기 (초)
DEFAULT_MULTIPLIER = 2.0       # 지수 백오프 배수
DEFAULT_MAX_RETRIES = 10       # 최대 재시도 횟수 (0 = 무제한)

# 재연결 시도 함수 타입
ConnectFn = Callable[[], Awaitable[None]]


class ReconnectManager:
    """지수 백오프 기반 자동 재연결 관리자.

    StateMachine의 ERROR/DISCONNECTED 상태를 감지하여 자동으로 재연결을 시도한다.
    최대 재시도 횟수 초과 시 포기하고 에러를 기록한다.
    """

    def __init__(
        self,
        state_machine: StateMachine,
        connect_fn: ConnectFn,
        initial_delay: float = DEFAULT_INITIAL_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        multiplier: float = DEFAULT_MULTIPLIER,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """초기화.

        Args:
            state_machine: 연결 상태 머신
            connect_fn: 재연결 시 호출할 async 함수
            initial_delay: 첫 재연결 대기 시간 (초)
            max_delay: 최대 대기 시간 (초)
            multiplier: 지수 백오프 배수
            max_retries: 최대 재시도 횟수 (0=무제한)
        """
        self._state_machine = state_machine
        self._connect_fn = connect_fn
        self._initial_delay = initial_delay
        self._max_delay = max_delay
        self._multiplier = multiplier
        self._max_retries = max_retries

        self._retry_count = 0
        self._current_delay = initial_delay
        self._reconnect_task: Optional[asyncio.Task] = None
        self._enabled = True

    def enable(self) -> None:
        """자동 재연결을 활성화한다."""
        self._enabled = True

    def disable(self) -> None:
        """자동 재연결을 비활성화한다. (의도적 연결 해제 시 호출)"""
        self._enabled = False
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()

    def on_state_change(self, old: ConnectionState, new: ConnectionState) -> None:
        """상태 변경 콜백. StateMachine.on_change()에 등록한다.

        ERROR 또는 DISCONNECTED 상태 진입 시 재연결 태스크를 시작한다.

        Args:
            old: 이전 상태
            new: 새 상태
        """
        if not self._enabled:
            return

        if new in {ConnectionState.ERROR, ConnectionState.DISCONNECTED}:
            if self._reconnect_task is None or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """재연결 루프. 성공할 때까지 지수 백오프로 재시도한다."""
        while self._enabled:
            # 최대 재시도 횟수 확인
            if self._max_retries > 0 and self._retry_count >= self._max_retries:
                logger.error(
                    "최대 재시도 횟수 초과 (%d회). 재연결 포기.",
                    self._max_retries,
                )
                return

            logger.info(
                "재연결 시도 %d/%s, %.1f초 후...",
                self._retry_count + 1,
                str(self._max_retries) if self._max_retries > 0 else "∞",
                self._current_delay,
            )
            await asyncio.sleep(self._current_delay)

            try:
                await self._connect_fn()
                # 재연결 성공
                logger.info("재연결 성공 (시도 %d회)", self._retry_count + 1)
                self._reset_backoff()
                return
            except Exception as exc:
                self._retry_count += 1
                logger.warning(
                    "재연결 실패 (시도 %d회): %s",
                    self._retry_count, exc,
                )
                self._current_delay = min(
                    self._current_delay * self._multiplier,
                    self._max_delay,
                )

    def _reset_backoff(self) -> None:
        """재연결 성공 후 백오프 상태를 초기화한다."""
        self._retry_count = 0
        self._current_delay = self._initial_delay

    @property
    def retry_count(self) -> int:
        """현재 재시도 횟수를 반환한다."""
        return self._retry_count

    @property
    def is_running(self) -> bool:
        """재연결 태스크가 실행 중인지 반환한다."""
        return (
            self._reconnect_task is not None
            and not self._reconnect_task.done()
        )
