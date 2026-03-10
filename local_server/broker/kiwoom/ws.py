"""local_server.broker.kiwoom.ws: 키움증권 WebSocket 실시간 시세 스트림 모듈

키움 REST API WS 프로토콜:
- URL: wss://(mock)api.kiwoom.com:10000/api/dostk/websocket
- 연결 후 LOGIN 메시지로 인증: {trnm: "LOGIN", token: access_token}
- 구독: {trnm: "REG", grp_no, refresh, data: [{item: [종목], type: [코드]}]}
- 해제: {trnm: "REMOVE", ...}
- 서비스 코드: 0B=주식체결, 0D=호가잔량
"""

import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Callable, Optional, TYPE_CHECKING

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    raise ImportError("websockets 패키지가 필요합니다: pip install websockets")

from sv_core.broker.models import QuoteEvent

if TYPE_CHECKING:
    from local_server.broker.kiwoom.auth import KiwoomAuth

logger = logging.getLogger(__name__)

# WebSocket 엔드포인트
WS_URL_REAL = "wss://api.kiwoom.com:10000/api/dostk/websocket"
WS_URL_MOCK = "wss://mockapi.kiwoom.com:10000/api/dostk/websocket"

# 구독 서비스 코드
SVC_STOCK_TRADE = "0B"       # 주식체결
SVC_STOCK_ORDERBOOK = "0D"   # 주식호가잔량


class KiwoomWS:
    """키움증권 WebSocket 실시간 시세 스트림 클라이언트."""

    def __init__(self, auth: "KiwoomAuth", is_mock: bool = False) -> None:
        self._auth = auth
        self._is_mock = is_mock
        self._ws_url = WS_URL_MOCK if is_mock else WS_URL_REAL
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._subscribed: set[str] = set()
        self._callbacks: list[Callable[[QuoteEvent], None]] = []
        self._recv_task: Optional[asyncio.Task] = None
        self._connected = False
        self._group_id = "1"

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None

    async def connect(self) -> None:
        """WebSocket 서버에 연결하고 LOGIN 인증을 수행한다."""
        logger.info("WebSocket 연결 시도: %s", self._ws_url)
        token = await self._auth.get_access_token()
        # 토큰 없이 연결 → LOGIN 메시지로 인증
        self._ws = await websockets.connect(
            self._ws_url,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5,
        )
        # LOGIN 인증
        login_msg = json.dumps({"trnm": "LOGIN", "token": token})
        await self._ws.send(login_msg)
        resp = await asyncio.wait_for(self._ws.recv(), timeout=10)
        logger.info("WebSocket LOGIN 응답: %.200s", resp)
        self._connected = True
        logger.info("WebSocket 연결 성공")
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
        self._callbacks.append(callback)

    async def subscribe(self, symbols: list[str]) -> None:
        """종목 실시간 시세 구독을 시작한다."""
        if not self.is_connected:
            raise RuntimeError("WebSocket에 연결되어 있지 않습니다")

        new_symbols = [s for s in symbols if s not in self._subscribed]
        if not new_symbols:
            return

        msg = {
            "trnm": "REG",
            "grp_no": self._group_id,
            "refresh": "1",
            "data": [{
                "item": new_symbols,
                "type": [SVC_STOCK_TRADE],
            }],
        }
        await self._ws.send(json.dumps(msg))  # type: ignore[union-attr]
        self._subscribed.update(new_symbols)
        logger.info("실시간 구독 시작: %s", new_symbols)

    async def unsubscribe(self, symbols: list[str]) -> None:
        """종목 실시간 시세 구독을 해제한다."""
        if not self.is_connected:
            return

        existing = [s for s in symbols if s in self._subscribed]
        if not existing:
            return

        msg = {
            "trnm": "REMOVE",
            "grp_no": self._group_id,
            "refresh": "1",
            "data": [{
                "item": existing,
                "type": [SVC_STOCK_TRADE],
            }],
        }
        await self._ws.send(json.dumps(msg))  # type: ignore[union-attr]
        self._subscribed -= set(existing)
        logger.info("실시간 구독 해제: %s", existing)

    def get_subscribed_symbols(self) -> set[str]:
        return set(self._subscribed)

    async def _recv_loop(self) -> None:
        """WebSocket 수신 루프."""
        try:
            async for raw_msg in self._ws:  # type: ignore[union-attr]
                self._handle_message(raw_msg)
        except asyncio.CancelledError:
            pass
        except ConnectionClosed as exc:
            logger.warning("WebSocket 연결 끊김: %s", exc)
            self._connected = False
        except Exception as exc:
            logger.error("WebSocket 수신 루프 오류: %s", exc, exc_info=True)
            self._connected = False

    def _handle_message(self, raw_msg: str) -> None:
        """수신 메시지를 파싱하여 QuoteEvent로 변환한다.

        실시간 메시지 형식:
          {"trnm": "REAL", "data": [{"item": "005930", "type": "0B", "values": {...}}]}
        """
        if not raw_msg:
            return

        try:
            data = json.loads(raw_msg)
        except json.JSONDecodeError:
            logger.debug("WebSocket 비JSON 메시지: %.100s", raw_msg)
            return

        if not isinstance(data, dict):
            return

        trnm = data.get("trnm", "")
        if trnm == "REAL":
            for entry in data.get("data", []):
                symbol = entry.get("item", "")
                values = entry.get("values", {})
                if symbol and values:
                    self._handle_quote_data(symbol, values)
                elif values:
                    logger.debug("REAL 메시지에 종목코드 없음: %s", list(values.keys())[:5])
        elif trnm in ("LOGIN", "REG", "REMOVE"):
            logger.debug("WebSocket %s 응답: %.200s", trnm, raw_msg)
        else:
            logger.debug("WebSocket 미처리 메시지: trnm=%s", trnm)

    def _handle_quote_data(self, symbol: str, values: dict) -> None:
        """실시간 시세 값을 QuoteEvent로 변환하여 콜백 호출.

        0B(주식체결) 필드 맵:
          10=현재가, 15=체결량, 20=체결시간,
          27=매도호가1, 28=매수호가1
        """
        try:
            raw_price = values.get("10", "0")
            event = QuoteEvent(
                symbol=symbol,
                price=abs(Decimal(raw_price)) if raw_price else Decimal("0"),
                volume=abs(int(values.get("15", "0") or "0")),
                bid_price=abs(Decimal(values["28"])) if values.get("28") else None,
                ask_price=abs(Decimal(values["27"])) if values.get("27") else None,
                timestamp=datetime.now(),
                raw={"symbol": symbol, **values},
            )
        except (ValueError, KeyError) as exc:
            logger.warning("QuoteEvent 파싱 실패 [%s]: %s", symbol, exc)
            return

        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as exc:
                logger.error("QuoteEvent 콜백 오류: %s", exc, exc_info=True)
