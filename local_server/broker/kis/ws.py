"""local_server.broker.kis.ws: 한국투자증권(KIS) WebSocket 실시간 시세 스트림 모듈"""

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Callable, Optional, TYPE_CHECKING

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, WebSocketException
except ImportError:
    raise ImportError("websockets 패키지가 필요합니다: pip install websockets")

from sv_core.broker.models import QuoteEvent

if TYPE_CHECKING:
    from local_server.broker.kis.auth import KisAuth

logger = logging.getLogger(__name__)

# WebSocket 엔드포인트
WS_URL = "wss://openapi.koreainvestment.com:9443/websocket/tryitout/H0STCNT0"

# KIS WebSocket 트랜젝션 ID
TR_SUBSCRIBE = "H0STCNT0"    # 주식 체결가 구독
TR_UNSUBSCRIBE = "H0STCNT0"  # 구독 해제 (동일 tr_id, tr_type으로 구분)


class KisWS:
    """한국투자증권(KIS) WebSocket 실시간 체결/시세 스트림 클라이언트.

    종목 구독 시 체결 데이터를 QuoteEvent로 변환하여 콜백에 전달한다.
    연결/재연결은 ReconnectManager에서 관리한다.
    """

    def __init__(self, auth: "KisAuth", on_disconnect: Callable | None = None) -> None:
        """초기화.

        Args:
            auth: KisAuth 인스턴스 (접속키 발급에 사용)
            on_disconnect: 연결 끊김 시 호출할 동기 콜백 (선택)
        """
        self._auth = auth
        self._on_disconnect = on_disconnect
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._subscribed: set[str] = set()
        self._callbacks: list[Callable[[QuoteEvent], None]] = []
        self._recv_task: Optional[asyncio.Task] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """WebSocket 연결 상태를 반환한다."""
        return self._connected and self._ws is not None

    async def connect(self) -> None:
        """WebSocket 서버에 연결한다.

        Raises:
            WebSocketException: 연결 실패 시
        """
        logger.info("WebSocket 연결 시도: %s", WS_URL)
        self._ws = await websockets.connect(
            WS_URL,
            ping_interval=30,   # 30초마다 ping
            ping_timeout=10,    # ping 응답 10초 대기
            close_timeout=5,
        )
        self._connected = True
        logger.info("WebSocket 연결 성공")

        # 수신 루프 태스크 시작
        self._recv_task = asyncio.create_task(self._recv_loop())

    async def disconnect(self) -> None:
        """WebSocket 연결을 종료한다."""
        self._connected = False
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
            self._recv_task = None

        if self._ws:
            await self._ws.close()
            self._ws = None

        self._subscribed.clear()
        logger.info("WebSocket 연결 종료")

    def add_callback(self, callback: Callable[[QuoteEvent], None]) -> None:
        """시세 이벤트 콜백을 등록한다.

        Args:
            callback: QuoteEvent를 인자로 받는 동기 함수
        """
        self._callbacks.append(callback)

    async def subscribe(self, symbols: list[str]) -> None:
        """종목 실시간 시세 구독을 시작한다.

        Args:
            symbols: 구독할 종목 코드 목록

        Raises:
            RuntimeError: 미연결 상태
        """
        if not self.is_connected:
            raise RuntimeError("WebSocket에 연결되어 있지 않습니다")

        # 접속키 발급 (체결 통보용)
        approval_key = await self._get_approval_key()

        for symbol in symbols:
            if symbol in self._subscribed:
                continue
            msg = self._build_subscribe_msg(approval_key, symbol, subscribe=True)
            await self._ws.send(json.dumps(msg))  # type: ignore[union-attr]
            self._subscribed.add(symbol)
            logger.info("실시간 구독 시작: %s", symbol)

    async def unsubscribe(self, symbols: list[str]) -> None:
        """종목 실시간 시세 구독을 해제한다.

        Args:
            symbols: 구독 해제할 종목 코드 목록
        """
        if not self.is_connected:
            return

        approval_key = await self._get_approval_key()
        for symbol in symbols:
            if symbol not in self._subscribed:
                continue
            msg = self._build_subscribe_msg(approval_key, symbol, subscribe=False)
            await self._ws.send(json.dumps(msg))  # type: ignore[union-attr]
            self._subscribed.discard(symbol)
            logger.info("실시간 구독 해제: %s", symbol)

    def get_subscribed_symbols(self) -> set[str]:
        """현재 구독 중인 종목 목록을 반환한다."""
        return set(self._subscribed)

    async def _get_approval_key(self) -> str:
        """WebSocket 접속용 approval_key를 발급받는다.

        KIS WebSocket은 access_token과 별도의 approval_key가 필요하다.
        KisAuth.get_approval_key()를 통해 /oauth2/Approval 엔드포인트에서 발급받는다.
        """
        return await self._auth.get_approval_key()

    def _build_subscribe_msg(
        self, approval_key: str, symbol: str, subscribe: bool
    ) -> dict:
        """WebSocket 구독/해제 메시지를 생성한다.

        Args:
            approval_key: WebSocket 접속키
            symbol: 종목 코드
            subscribe: True=구독, False=해제

        Returns:
            dict: WebSocket 전송 메시지
        """
        tr_type = "1" if subscribe else "2"  # 1=구독, 2=해제
        return {
            "header": {
                "approval_key": approval_key,
                "custtype": "P",        # P=개인
                "tr_type": tr_type,
                "content-type": "utf-8",
            },
            "body": {
                "input": {
                    "tr_id": TR_SUBSCRIBE,
                    "tr_key": symbol,
                }
            },
        }

    async def _recv_loop(self) -> None:
        """WebSocket 수신 루프. 메시지를 받아 콜백으로 전달한다."""
        try:
            async for raw_msg in self._ws:  # type: ignore[union-attr]
                self._handle_message(raw_msg)
        except asyncio.CancelledError:
            pass
        except ConnectionClosed as exc:
            logger.warning("WebSocket 연결 끊김: %s", exc)
            self._connected = False
            if self._on_disconnect:
                self._on_disconnect()
        except Exception as exc:
            logger.error("WebSocket 수신 루프 오류: %s", exc, exc_info=True)
            self._connected = False
            if self._on_disconnect:
                self._on_disconnect()

    def _handle_message(self, raw_msg: str) -> None:
        """수신 메시지를 파싱하여 QuoteEvent로 변환 후 콜백을 호출한다.

        KIS 체결 데이터 형식:
        - PINGPONG: 연결 유지 메시지 (무시)
        - 데이터: '^'로 구분된 필드 (JSON 아님)
        """
        if not raw_msg:
            return

        # PINGPONG 메시지 처리
        if raw_msg.startswith("0|") or raw_msg.startswith("1|"):
            self._handle_realtime_data(raw_msg)
            return

        # JSON 메시지 (응답/오류)
        try:
            data = json.loads(raw_msg)
            header = data.get("header", {})
            msg_type = header.get("tr_id", "")
            if msg_type == "PINGPONG":
                return  # PINGPONG 무시
            logger.debug("WebSocket 제어 메시지: %s", data)
        except json.JSONDecodeError:
            logger.debug("WebSocket 비JSON 메시지: %.100s", raw_msg)

    def _handle_realtime_data(self, raw_msg: str) -> None:
        """실시간 체결 데이터를 파싱하여 QuoteEvent를 생성한다.

        형식: "{tr_id}|{종목코드}|{필드수}|{데이터}"
        체결 데이터 주요 필드 (H0STCNT0):
          0: 종목코드, 2: 체결시간, 10: 현재가, 12: 누적거래량, 7: 매도호가, 8: 매수호가
        """
        parts = raw_msg.split("|")
        if len(parts) < 4:
            return

        tr_id = parts[0]
        symbol = parts[1]
        if tr_id != TR_SUBSCRIBE:
            return

        fields = parts[3].split("^")
        try:
            event = QuoteEvent(
                symbol=symbol,
                price=Decimal(fields[10]) if len(fields) > 10 and fields[10] else Decimal("0"),
                volume=int(fields[12]) if len(fields) > 12 and fields[12] else 0,
                bid_price=Decimal(fields[8]) if len(fields) > 8 and fields[8] else None,
                ask_price=Decimal(fields[7]) if len(fields) > 7 and fields[7] else None,
                timestamp=datetime.now(),
                raw={"raw": raw_msg, "fields": fields},
            )
        except (IndexError, ValueError) as exc:
            logger.warning("QuoteEvent 파싱 실패: %s — %s", exc, raw_msg[:100])
            return

        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as exc:
                logger.error("QuoteEvent 콜백 오류: %s", exc, exc_info=True)
