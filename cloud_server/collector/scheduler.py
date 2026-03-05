"""
데이터 수집 스케줄러 (APScheduler)

스케줄:
- 09:00 KST: 키움 WS 시작 (장 시작)
- 16:00 KST: 일봉 저장 (장 마감 후)
- 08:00 KST: 종목 마스터 갱신
- 17:00 KST: yfinance 보조 수집
- 18:00 KST: 데이터 정합성 체크
"""
import asyncio
import logging
from datetime import date, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from cloud_server.collector.kiwoom_collector import KiwoomCollector, get_major_symbols
from cloud_server.core.broker_factory import BrokerFactory
from cloud_server.core.database import get_db_session
from cloud_server.services.market_repository import MarketRepository
from cloud_server.services.yfinance_service import YFinanceService, DEFAULT_SYMBOLS

logger = logging.getLogger(__name__)


# 수집기 상태 (전역)
_collector_status = {
    "status": "stopped",          # running | stopped | error
    "last_quote_time": None,       # 마지막 시세 수신 시각
    "error_count": 0,
    "total_quotes": 0,
    "last_error": None,
}


def get_collector_status() -> dict:
    """현재 수집기 상태 반환"""
    return _collector_status.copy()


class CollectorScheduler:
    """APScheduler 기반 데이터 수집 스케줄러"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self.kiwoom_collector: KiwoomCollector | None = None
        self._listen_task: asyncio.Task | None = None

    def start(self) -> None:
        """스케줄러 시작 (FastAPI startup에서 호출)"""
        # 09:00 KST — 키움 WS 시작
        self.scheduler.add_job(
            self.start_kiwoom_ws,
            trigger=CronTrigger(hour=9, minute=0, timezone="Asia/Seoul"),
            id="kiwoom_ws_start",
            replace_existing=True,
        )

        # 16:00 KST — 일봉 저장
        self.scheduler.add_job(
            self.save_daily_bars,
            trigger=CronTrigger(hour=16, minute=0, timezone="Asia/Seoul"),
            id="daily_bars",
            replace_existing=True,
        )

        # 08:00 KST — 종목 마스터 갱신
        self.scheduler.add_job(
            self.update_stock_master,
            trigger=CronTrigger(hour=8, minute=0, timezone="Asia/Seoul"),
            id="stock_master",
            replace_existing=True,
        )

        # 17:00 KST — yfinance 보조 수집
        self.scheduler.add_job(
            self.collect_yfinance,
            trigger=CronTrigger(hour=17, minute=0, timezone="Asia/Seoul"),
            id="yfinance",
            replace_existing=True,
        )

        # 18:00 KST — 데이터 정합성 체크
        self.scheduler.add_job(
            self.check_data_integrity,
            trigger=CronTrigger(hour=18, minute=0, timezone="Asia/Seoul"),
            id="integrity_check",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("수집 스케줄러 시작됨")

    def stop(self) -> None:
        """스케줄러 중지 (FastAPI shutdown에서 호출)"""
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()

        if self.kiwoom_collector:
            self.kiwoom_collector.stop()

        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

        _collector_status["status"] = "stopped"
        logger.info("수집 스케줄러 중지됨")

    async def start_kiwoom_ws(self) -> None:
        """키움 WS 시작 (서비스 키 로드 → 인증 → 구독 → 리스닝)"""
        global _collector_status
        try:
            db = get_db_session()
            from cloud_server.models.template import KiwoomServiceKey
            from cloud_server.core.encryption import decrypt_value

            service_key_row = db.query(KiwoomServiceKey).filter(
                KiwoomServiceKey.is_active == True  # noqa: E712
            ).first()
            db.close()

            if not service_key_row:
                logger.warning("활성화된 서비스 키가 없습니다. WS 시작 생략.")
                return

            broker = BrokerFactory.create("kiwoom", {
                "api_key": service_key_row.api_key,
                "api_secret": decrypt_value(service_key_row.api_secret),
            })
            await broker.authenticate()

            self.kiwoom_collector = KiwoomCollector(broker)
            symbols = get_major_symbols()
            await self.kiwoom_collector.subscribe(symbols)

            # 백그라운드 리스닝 태스크 시작
            self._listen_task = asyncio.create_task(self._listen_quotes())
            _collector_status["status"] = "running"
            logger.info(f"키움 WS 시작: {len(symbols)}개 종목 구독")

        except Exception as e:
            _collector_status["status"] = "error"
            _collector_status["last_error"] = str(e)
            _collector_status["error_count"] += 1
            logger.error(f"키움 WS 시작 실패: {e}")

    async def _listen_quotes(self) -> None:
        """실시간 시세 수신 및 저장 (백그라운드 태스크)"""
        global _collector_status
        if not self.kiwoom_collector:
            return

        db = get_db_session()
        repo = MarketRepository(db)
        try:
            async for event in self.kiwoom_collector.listen():
                try:
                    repo.save_minute_bar(event)
                    _collector_status["last_quote_time"] = datetime.utcnow().isoformat()
                    _collector_status["total_quotes"] += 1
                except Exception as e:
                    logger.error(f"분봉 저장 실패 {event.symbol}: {e}")
                    _collector_status["error_count"] += 1
        except asyncio.CancelledError:
            logger.info("시세 수신 태스크 취소됨")
        except Exception as e:
            _collector_status["status"] = "error"
            _collector_status["last_error"] = str(e)
            _collector_status["error_count"] += 1
            logger.error(f"시세 수신 오류: {e}")
        finally:
            db.close()

    async def save_daily_bars(self) -> None:
        """일봉 저장 (키움 REST API로 당일 종가 수집)"""
        logger.info("일봉 저장 시작")
        # TODO: BrokerAdapter.get_daily_bars() 사용 (Unit 1 완성 후)
        # 현재는 yfinance 폴백으로 처리
        await self.collect_yfinance()

    async def update_stock_master(self) -> None:
        """종목 마스터 갱신 (키움 API로 상장 종목 조회)"""
        logger.info("종목 마스터 갱신 시작 (stub)")
        # TODO: BrokerAdapter.get_listed_symbols() 사용 (Unit 1 완성 후)

    async def collect_yfinance(self) -> None:
        """yfinance 보조 수집 (한국 지수, 해외 지수, 환율)"""
        logger.info("yfinance 수집 시작")
        try:
            yf_service = YFinanceService()
            data = yf_service.fetch_recent(DEFAULT_SYMBOLS, days=1)

            db = get_db_session()
            repo = MarketRepository(db)
            try:
                for symbol, bars in data.items():
                    for bar in bars:
                        repo.save_daily_bar(symbol, bar["date"], bar)
                logger.info(f"yfinance 수집 완료: {len(data)}개 심볼")
            finally:
                db.close()

        except Exception as e:
            _collector_status["error_count"] += 1
            logger.error(f"yfinance 수집 실패: {e}")

    async def check_data_integrity(self) -> None:
        """결측 거래일 감지 및 재수집"""
        logger.info("데이터 정합성 체크 시작")
        try:
            yesterday = date.today() - timedelta(days=1)
            # 주말이면 건너뜀
            if yesterday.weekday() >= 5:
                logger.info(f"주말 제외: {yesterday}")
                return

            db = get_db_session()
            repo = MarketRepository(db)
            yf_service = YFinanceService()

            try:
                symbols = get_major_symbols()
                missing = []
                for symbol in symbols:
                    if not repo.has_daily_bar(symbol, yesterday):
                        missing.append(symbol)

                if missing:
                    logger.warning(f"누락 일봉: {missing} ({yesterday})")
                    data = yf_service.fetch_daily(missing, yesterday, yesterday)
                    for sym, bars in data.items():
                        for bar in bars:
                            repo.save_daily_bar(sym, bar["date"], bar)
                    logger.info(f"누락 데이터 재수집 완료: {len(missing)}개")
                else:
                    logger.info("데이터 정합성 OK")
            finally:
                db.close()

        except Exception as e:
            _collector_status["error_count"] += 1
            logger.error(f"정합성 체크 실패: {e}")
