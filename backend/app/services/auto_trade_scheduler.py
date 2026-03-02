"""
자동매매 스케줄러

APScheduler 기반 크론잡으로 스코어링→매수, 일괄 매도를 자동 실행한다.
규칙 활성화/비활성화에 따라 잡을 동적으로 추가/제거한다.
"""

import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.auto_trading import AutoTradingRule
from app.services.scoring_engine import ScoringEngine
from app.services.trading_engine import TradingEngine

logger = logging.getLogger(__name__)


class AutoTradeScheduler:
    """자동매매 스케줄러"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._started = False

    def start(self):
        """스케줄러 시작 및 활성 규칙 잡 등록"""
        if self._started:
            return

        # DB에서 활성 규칙 로드
        db = SessionLocal()
        try:
            rules = db.query(AutoTradingRule).filter(AutoTradingRule.is_active == True).all()
            for rule in rules:
                self._add_jobs_for_rule(rule)
            logger.info(f"자동매매 스케줄러 시작: {len(rules)}개 규칙 로드")
        finally:
            db.close()

        self.scheduler.start()
        self._started = True

    def stop(self):
        """스케줄러 중지"""
        if self._started:
            self.scheduler.shutdown(wait=False)
            self._started = False
            logger.info("자동매매 스케줄러 중지")

    def reload_rules(self):
        """규칙 변경 시 잡 재등록"""
        # 기존 잡 전부 제거
        self.scheduler.remove_all_jobs()

        db = SessionLocal()
        try:
            rules = db.query(AutoTradingRule).filter(AutoTradingRule.is_active == True).all()
            for rule in rules:
                self._add_jobs_for_rule(rule)
            logger.info(f"규칙 리로드: {len(rules)}개 활성")
        finally:
            db.close()

    def _add_jobs_for_rule(self, rule: AutoTradingRule):
        """규칙에 대한 매수/매도 잡 등록"""
        # 매수 잡 (기본: 평일 09:30)
        buy_schedule = rule.schedule_buy or "30 9 * * 1-5"
        try:
            self.scheduler.add_job(
                self._execute_buy,
                CronTrigger.from_crontab(buy_schedule),
                id=f"buy_rule_{rule.id}",
                args=[rule.id],
                replace_existing=True,
                misfire_grace_time=300,
            )
        except Exception as e:
            logger.error(f"매수 잡 등록 실패 (rule {rule.id}): {e}")

        # 매도 잡 (기본: 평일 15:00)
        sell_schedule = rule.schedule_sell or "0 15 * * 1-5"
        try:
            self.scheduler.add_job(
                self._execute_sell,
                CronTrigger.from_crontab(sell_schedule),
                id=f"sell_rule_{rule.id}",
                args=[rule.id],
                replace_existing=True,
                misfire_grace_time=300,
            )
        except Exception as e:
            logger.error(f"매도 잡 등록 실패 (rule {rule.id}): {e}")

    @staticmethod
    def _execute_buy(rule_id: int):
        """매수 잡 실행: 스코어링 → 상위 N종목 매수"""
        db = SessionLocal()
        try:
            rule = db.query(AutoTradingRule).filter(AutoTradingRule.id == rule_id).first()
            if not rule or not rule.is_active or not rule.account_id:
                return

            logger.info(f"[자동매수] 규칙 {rule.id} ({rule.name}) 실행 시작")

            # 스코어링
            scorer = ScoringEngine(db)
            scores = scorer.score_all_stocks()

            # 매수 대상 필터 (스코어 ≥ threshold)
            buy_candidates = [
                s for s in scores if s["total_score"] >= rule.buy_score_threshold
            ]

            if not buy_candidates:
                logger.info(f"[자동매수] 매수 대상 없음 (threshold: {rule.buy_score_threshold})")
                rule.last_executed_at = datetime.utcnow()
                db.commit()
                return

            # 기존 포지션 수 확인
            engine = TradingEngine(db)
            current_positions = engine.get_positions(rule.account_id)
            available_slots = rule.max_position_count - len(current_positions)

            if available_slots <= 0:
                logger.info(f"[자동매수] 보유 종목 한도 도달 ({len(current_positions)}/{rule.max_position_count})")
                rule.last_executed_at = datetime.utcnow()
                db.commit()
                return

            # 상위 N종목 선택
            targets = buy_candidates[:available_slots]
            account = engine.get_account(rule.account_id)
            if not account:
                return

            budget = account.current_balance * rule.budget_ratio
            budget_per_stock = budget / len(targets)

            for score_data in targets:
                # 현재가 조회 (DB에서 최신 가격)
                from app.models.stock import StockPrice
                latest = (
                    db.query(StockPrice)
                    .filter(StockPrice.stock_id == score_data["stock_id"])
                    .order_by(StockPrice.date.desc())
                    .first()
                )
                if not latest:
                    continue

                price = latest.close
                quantity = int(budget_per_stock / (price * 1.00015))  # 수수료 고려
                if quantity <= 0:
                    continue

                result = engine.buy(
                    rule.account_id,
                    score_data["stock_id"],
                    score_data["symbol"],
                    quantity,
                    price,
                )
                if result["success"]:
                    logger.info(
                        f"[자동매수] {score_data['symbol']} {quantity}주 "
                        f"(스코어: {score_data['total_score']})"
                    )

            rule.last_executed_at = datetime.utcnow()
            db.commit()
            logger.info(f"[자동매수] 규칙 {rule.id} 실행 완료")

        except Exception as e:
            logger.error(f"[자동매수] 규칙 {rule_id} 실행 실패: {e}")
        finally:
            db.close()

    @staticmethod
    def _execute_sell(rule_id: int):
        """매도 잡 실행: 보유 전 종목 일괄 매도"""
        db = SessionLocal()
        try:
            rule = db.query(AutoTradingRule).filter(AutoTradingRule.id == rule_id).first()
            if not rule or not rule.is_active or not rule.account_id:
                return

            logger.info(f"[자동매도] 규칙 {rule.id} ({rule.name}) 실행 시작")

            engine = TradingEngine(db)
            positions = engine.get_positions(rule.account_id)

            for pos in positions:
                # 현재가 조회
                from app.models.stock import StockPrice
                latest = (
                    db.query(StockPrice)
                    .filter(StockPrice.stock_id == pos.stock_id)
                    .order_by(StockPrice.date.desc())
                    .first()
                )
                price = latest.close if latest else pos.avg_price

                result = engine.sell(
                    rule.account_id,
                    pos.stock_id,
                    pos.symbol or "",
                    pos.quantity,
                    price,
                )
                if result["success"]:
                    pnl = result["trade"].realized_pnl or 0
                    logger.info(
                        f"[자동매도] {pos.symbol} {pos.quantity}주 "
                        f"(손익: {pnl:,.0f}원)"
                    )

            rule.last_executed_at = datetime.utcnow()
            db.commit()
            logger.info(f"[자동매도] 규칙 {rule.id} 실행 완료")

        except Exception as e:
            logger.error(f"[자동매도] 규칙 {rule_id} 실행 실패: {e}")
        finally:
            db.close()


# 싱글톤
_auto_scheduler: Optional[AutoTradeScheduler] = None


def get_auto_scheduler() -> AutoTradeScheduler:
    global _auto_scheduler
    if _auto_scheduler is None:
        _auto_scheduler = AutoTradeScheduler()
    return _auto_scheduler
