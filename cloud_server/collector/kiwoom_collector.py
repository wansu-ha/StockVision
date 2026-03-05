"""
키움 시세 수집기 (서비스 키 사용)

BrokerAdapter를 통해 실시간 시세 구독 및 이벤트 수신.
수신된 시세는 MarketRepository를 통해 MinuteBar로 저장.
"""
import asyncio
import logging
from typing import AsyncIterator, Callable

from sv_core.broker.base import BrokerAdapter
from sv_core.broker.models import QuoteEvent  # C1: 정본 경로로 수정

logger = logging.getLogger(__name__)

# 수집 대상 주요 종목 목록 (운영 시 DB에서 조회)
_MAJOR_SYMBOLS: list[str] = [
    # 코스피 대형주 (예시)
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035420",  # NAVER
    "005380",  # 현대차
    "051910",  # LG화학
    # 코스닥 대형주 (예시)
    "247540",  # 에코프로비엠
    "373220",  # LG에너지솔루션
    # 지수
    "^KS11",   # KOSPI
    "^KQ11",   # KOSDAQ
]


def get_major_symbols() -> list[str]:
    """수집 대상 종목 목록 반환 (향후 DB 조회로 확장)"""
    return _MAJOR_SYMBOLS.copy()


class KiwoomCollector:
    """
    키움 실시간 시세 수집기

    broker.subscribe_quotes(symbols, callback) 로 시세 이벤트 수신.
    콜백으로 수신된 이벤트를 asyncio.Queue를 통해 async generator로 노출.
    """

    def __init__(self, broker: BrokerAdapter):
        self.broker = broker
        self.subscribed_symbols: set[str] = set()
        self._running = False
        self._queue: asyncio.Queue[QuoteEvent] = asyncio.Queue()

    async def subscribe(self, symbols: list[str]) -> None:
        """시세 구독 (C5: subscribe_quotes 콜백 패턴 사용)"""
        await self.broker.subscribe_quotes(symbols, self._on_quote)
        self.subscribed_symbols.update(symbols)
        logger.info(f"시세 구독 완료: {len(symbols)}개 종목")

    def _on_quote(self, event: QuoteEvent) -> None:
        """시세 이벤트 콜백 — 큐에 적재"""
        self._queue.put_nowait(event)

    async def unsubscribe_all(self) -> None:
        """전체 구독 해제"""
        if self.subscribed_symbols:
            symbols = list(self.subscribed_symbols)
            await self.broker.unsubscribe_quotes(symbols)
            self.subscribed_symbols.clear()
            logger.info("전체 구독 해제 완료")

    async def listen(self) -> AsyncIterator[QuoteEvent]:
        """
        실시간 시세 이벤트 스트림.
        중단 시 자동 종료.
        """
        self._running = True
        try:
            while self._running:
                try:
                    event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                    yield event
                except asyncio.TimeoutError:
                    continue
        except Exception as e:
            logger.error(f"시세 수신 오류: {e}")
        finally:
            self._running = False
            logger.info("시세 수신 종료")

    def stop(self) -> None:
        """수신 중단 요청"""
        self._running = False
