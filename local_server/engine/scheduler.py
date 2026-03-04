"""
거래 규칙 평가 스케줄러

- 장 시간(09:00~15:30 KST) 1분 주기 실행
- execution-engine spec 구현 시 evaluator 연결
"""
import asyncio
import logging
from datetime import datetime, time

import pytz

logger = logging.getLogger(__name__)

_KST = pytz.timezone("Asia/Seoul")
_MARKET_OPEN    = time(9, 0)
_MARKET_CLOSE   = time(15, 30)
_CONTEXT_REFRESH = time(15, 35)  # 장 마감 5분 후 컨텍스트 갱신
_EMAIL_REPORT    = time(16, 0)   # 일일 실행 리포트 이메일


def _is_market_hours() -> bool:
    now_kst = datetime.now(_KST).time()
    return _MARKET_OPEN <= now_kst <= _MARKET_CLOSE


def _is_context_refresh_time() -> bool:
    now_kst = datetime.now(_KST).time()
    # 15:35~15:36 사이에 1회 갱신
    return _CONTEXT_REFRESH <= now_kst <= time(15, 36)


def _is_email_report_time() -> bool:
    now_kst = datetime.now(_KST).time()
    # 16:00~16:01 사이에 1회 발송
    return _EMAIL_REPORT <= now_kst <= time(16, 1)


class TradingScheduler:
    def __init__(self, config_manager):
        self._config_manager    = config_manager
        self._running           = False
        self._paused            = False
        self._context_refreshed = False  # 오늘 컨텍스트 갱신 여부
        self._email_reported    = False  # 오늘 이메일 리포트 발송 여부

    async def run(self) -> None:
        self._running = True
        logger.info("전략 스케줄러 시작")
        while self._running:
            if not self._paused and _is_market_hours():
                await self._tick()
            if _is_context_refresh_time() and not self._context_refreshed:
                await self._refresh_context()
            if _is_email_report_time() and not self._email_reported:
                await self._send_email_report()
            # 자정 이후 플래그 리셋 (다음날 갱신 허용)
            if not _is_context_refresh_time():
                self._context_refreshed = False
            if not _is_email_report_time():
                self._email_reported = False
            await asyncio.sleep(60)
        logger.info("전략 스케줄러 종료")

    async def _refresh_context(self) -> None:
        self._context_refreshed = True
        try:
            from storage.config_manager import get_config_manager
            from cloud.context import fetch_and_cache
            jwt = get_config_manager()._jwt
            if jwt:
                await asyncio.get_running_loop().run_in_executor(
                    None, fetch_and_cache, jwt
                )
                logger.info("장 마감 후 컨텍스트 갱신 완료")
            else:
                logger.warning("JWT 없음 — 컨텍스트 갱신 스킵")
        except Exception as e:
            logger.error(f"컨텍스트 갱신 오류: {e}")

    async def _send_email_report(self) -> None:
        self._email_reported = True
        try:
            from storage.config_manager import get_config_manager
            from cloud.email_reporter import send_daily_summary
            jwt = get_config_manager()._jwt
            if jwt:
                await asyncio.get_running_loop().run_in_executor(
                    None, send_daily_summary, jwt
                )
                logger.info("일일 실행 리포트 이메일 발송 완료")
            else:
                logger.warning("JWT 없음 — 이메일 리포트 스킵")
        except Exception as e:
            logger.error(f"이메일 리포트 오류: {e}")

    async def _tick(self) -> None:
        rules = self._config_manager.get_active_rules()
        if not rules:
            return
        logger.debug(f"규칙 평가 시작: {len(rules)}개")
        # execution-engine spec 구현 시 evaluator.evaluate(rule) 호출
        for rule in rules:
            try:
                from engine.evaluator import evaluate_rule
                await evaluate_rule(rule)
            except Exception as e:
                logger.error(f"규칙 평가 오류 (rule_id={rule.get('id')}): {e}")

    def pause(self) -> None:
        self._paused = True
        logger.info("스케줄러 일시정지")

    def resume(self) -> None:
        self._paused = False
        logger.info("스케줄러 재개")

    def stop(self) -> None:
        self._running = False


_scheduler: "TradingScheduler | None" = None


def set_scheduler(s: "TradingScheduler") -> None:
    global _scheduler
    _scheduler = s


def get_scheduler() -> "TradingScheduler | None":
    return _scheduler
