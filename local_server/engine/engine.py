"""StrategyEngine — 전략 엔진 통합.

EngineScheduler가 1분마다 evaluate_all()을 호출하면
활성 규칙을 순회하며 조건 평가 → SystemTrader 판단 → 주문 실행을 수행한다.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable, Optional

from local_server.engine.alert_monitor import AlertMonitor
from local_server.engine.bar_builder import BarBuilder
from local_server.engine.context_cache import ContextCache
from local_server.engine.evaluator import RuleEvaluator
from local_server.engine.indicator_provider import IndicatorProvider
from local_server.engine.executor import ExecutionResult, ExecutionStatus, OrderExecutor
from local_server.engine.limit_checker import LimitChecker
from local_server.engine.price_verifier import PriceVerifier
from local_server.engine.safeguard import KillSwitchLevel, Safeguard
from local_server.engine.scheduler import EngineScheduler
from local_server.engine.signal_manager import SignalManager
from local_server.engine.result_store import ResultStatus, record_result
from local_server.engine.system_trader import SystemTrader
from local_server.engine.trader_models import CandidateSignal

if TYPE_CHECKING:
    from sv_core.broker.base import BrokerAdapter
    from sv_core.broker.models import QuoteEvent

logger = logging.getLogger(__name__)


class StrategyEngine:
    """전략 엔진 통합."""

    def __init__(
        self,
        broker: BrokerAdapter,
        config: dict[str, Any] | None = None,
    ) -> None:
        cfg = config or {}
        self._broker = broker
        self._running = False

        # 서브 모듈
        self._evaluator = RuleEvaluator()
        self._signal_manager = SignalManager()
        self._price_verifier = PriceVerifier(broker)
        self._limit_checker = LimitChecker(
            budget_ratio=Decimal(str(cfg.get("budget_ratio", "0.1"))),
            max_positions=int(cfg.get("max_positions", 5)),
        )
        self._safeguard = Safeguard(
            max_loss_pct=Decimal(str(cfg.get("max_loss_pct", "5.0"))),
            max_orders_per_minute=int(cfg.get("max_orders_per_minute", 10)),
        )
        self._executor = OrderExecutor(
            broker=broker,
            signal_manager=self._signal_manager,
            price_verifier=self._price_verifier,
            limit_checker=self._limit_checker,
            safeguard=self._safeguard,
        )
        self._context_cache = ContextCache(
            ttl_seconds=int(cfg.get("context_ttl", 3600)),
        )
        self._bar_builder = BarBuilder()
        self._indicator_provider = IndicatorProvider()
        self._system_trader = SystemTrader(
            max_positions=int(cfg.get("max_positions", 5)),
            budget_ratio=Decimal(str(cfg.get("budget_ratio", "0.1"))),
        )
        self._scheduler = EngineScheduler(self.evaluate_all)

        # 규칙 캐시 (외부에서 set)
        self._rules: list[dict] = []

        # 콜백 (실행 결과 알림, WS 등)
        self._on_execution: Optional[Callable[[ExecutionResult], Any]] = None

        # AlertMonitor (alerts 설정 섹션 전달)
        self._alert_monitor = AlertMonitor(config=cfg.get("alerts"))

        # HealthWatchdog가 참조하는 마지막 evaluate 시각
        self._last_evaluate_ts: Optional[datetime] = None

    # ── 라이프사이클 ──

    async def start(self) -> None:
        """엔진 시작."""
        self._running = True
        # LimitChecker 당일 금액 복원 (재시작 시)
        from local_server.storage.log_db import get_log_db
        self._limit_checker.restore_from_db(get_log_db())
        # 활성 규칙 종목들
        symbols = list({r.get("symbol", "") for r in self._rules if r.get("is_active")})
        # 일봉 지표 계산 (yfinance)
        if symbols:
            await self._indicator_provider.refresh(symbols)
        # 시세 구독
        if symbols:
            await self._broker.subscribe_quotes(symbols, self._on_quote)
        await self._scheduler.start()
        logger.info("StrategyEngine 시작 (규칙 %d개, 종목 %d개)", len(self._rules), len(symbols))

    async def stop(self) -> None:
        """엔진 중지."""
        self._running = False
        await self._scheduler.stop()
        logger.info("StrategyEngine 중지")

    @property
    def is_running(self) -> bool:
        return self._running

    # ── 외부 설정 ──

    def set_rules(self, rules: list[dict]) -> None:
        """규칙 캐시 갱신."""
        self._rules = rules

    def update_context(self, context: dict) -> None:
        """AI 컨텍스트 갱신."""
        self._context_cache.update(context)

    def set_on_execution(self, callback: Callable[[ExecutionResult], Any]) -> None:
        """실행 결과 콜백 등록."""
        self._on_execution = callback

    def set_alert_broadcast(self, callback: Any) -> None:
        """AlertMonitor WS 브로드캐스트 콜백 등록."""
        self._alert_monitor.set_broadcast(callback)

    @property
    def alert_monitor(self) -> AlertMonitor:
        return self._alert_monitor

    # ── 서브 모듈 접근자 ──

    @property
    def safeguard(self) -> Safeguard:
        return self._safeguard

    @property
    def signal_manager(self) -> SignalManager:
        return self._signal_manager

    @property
    def bar_builder(self) -> BarBuilder:
        return self._bar_builder

    @property
    def context_cache(self) -> ContextCache:
        return self._context_cache

    @property
    def indicator_provider(self) -> IndicatorProvider:
        return self._indicator_provider

    # ── 메인 루프 ──

    async def evaluate_all(self) -> None:
        """1분마다 호출되는 메인 루프.

        v3: 후보 수집 → SystemTrader 판단 → 선택된 후보만 실행.
        """
        if not self._running:
            return

        try:
            now = datetime.now()

            # TS-5: 날짜 경계 감지 → 일일 누적 자동 리셋
            self._limit_checker.check_date_boundary()

            # 장 시작 직후 SYNCING (09:00~09:02)
            if now.hour == 9 and now.minute < 2:
                logger.debug("SYNCING 상태 — 평가 보류")
                return

            # 장 마감 이후 (15:30~) 평가 차단
            if now.hour == 15 and now.minute >= 30:
                logger.debug("장 마감 — 평가 중단")
                return

            # 활성 규칙 (priority 내림차순)
            active_rules = sorted(
                [r for r in self._rules if r.get("is_active", False)],
                key=lambda r: r.get("priority", 0),
                reverse=True,
            )
            if not active_rules:
                return

            # 잔고 / 미체결 조회 + 당일 손익 (AlertMonitor에 필요, 무조건 조회)
            balance = await self._broker.get_balance()
            holding_symbols = {p.symbol for p in balance.positions}
            open_orders = await self._broker.get_open_orders()
            from local_server.storage.log_db import get_log_db
            today_pnl = get_log_db().today_realized_pnl()

            # AlertMonitor 경고 평가 (trading_enabled 여부와 무관하게 실행)
            await self._alert_monitor.check_all(balance, open_orders, today_pnl)

            # 최대 손실 제한 체크
            if self._safeguard.is_trading_enabled():
                loss_ok = self._safeguard.check_max_loss(today_pnl, balance.cash + balance.total_eval)
                if not loss_ok:
                    await self._cancel_open_orders()
                    await self._notify_loss_lock(today_pnl)

            # Kill Switch / 손실 락 포함 최종 거래 가능 여부
            trading_enabled = self._safeguard.is_trading_enabled()
            if not trading_enabled:
                return

            # ── 후보 수집 ──
            cycle_id = uuid.uuid4().hex[:12]
            candidates: list[CandidateSignal] = []
            market_data_map: dict[str, dict[str, Any]] = {}

            for rule in active_rules:
                for candidate, market_data in self._collect_candidates(rule, cycle_id):
                    candidates.append(candidate)
                    market_data_map[candidate.signal_id] = market_data

            if not candidates:
                return

            # ── SystemTrader 판단 ──
            batch = self._system_trader.process_cycle(
                cycle_id=cycle_id,
                candidates=candidates,
                current_positions=holding_symbols,
                cash=balance.cash,
                today_executed=self._limit_checker.today_executed,
            )

            logger.info(
                "[Cycle %s] 후보 %d개 → 선택 %d개, 차단 %d개",
                cycle_id, len(candidates), len(batch.selected), len(batch.dropped),
            )

            for candidate, reason in batch.dropped:
                logger.info(
                    "[Cycle %s] 차단: Rule %d (%s %s) — %s",
                    cycle_id, candidate.rule_id, candidate.side, candidate.symbol, reason.value,
                )
                record_result(candidate.rule_id, ResultStatus.BLOCKED, reason.value)
                # 차단 로그 (intent_id로 타임라인 추적)
                from local_server.storage.log_db import get_log_db, LOG_TYPE_ERROR
                await get_log_db().async_write(
                    LOG_TYPE_ERROR,
                    f"{reason.value}: {candidate.symbol} {candidate.side} 거부",
                    symbol=candidate.symbol,
                    meta={"rule_id": candidate.rule_id, "side": candidate.side,
                          "block_reason": reason.value},
                    intent_id=candidate.intent_id,
                )

            # ── 선택된 후보 실행 ──
            for candidate in batch.selected:
                md = market_data_map[candidate.signal_id]
                # PROPOSED 로그 (전략 평가 통과)
                from local_server.storage.log_db import get_log_db, LOG_TYPE_STRATEGY
                await get_log_db().async_write(
                    LOG_TYPE_STRATEGY,
                    f"{candidate.reason}: {candidate.symbol} {candidate.side}",
                    symbol=candidate.symbol,
                    meta={"rule_id": candidate.rule_id, "side": candidate.side,
                          "qty": candidate.desired_qty, "price": candidate.latest_price},
                    intent_id=candidate.intent_id,
                )
                result = await self._executor.execute(
                    candidate.raw_rule, candidate.side, md, balance,
                    intent_id=candidate.intent_id,
                )
                result.cycle_id = cycle_id
                result.signal_id = candidate.signal_id
                logger.info(
                    "[Cycle %s] Rule %d %s: %s — %s",
                    cycle_id, candidate.rule_id, candidate.side,
                    result.status.value, result.message,
                )
                # result_store 기록
                if result.status == ExecutionStatus.SUCCESS:
                    record_result(candidate.rule_id, ResultStatus.SUCCESS, result.message)
                elif result.status == ExecutionStatus.REJECTED:
                    record_result(candidate.rule_id, ResultStatus.BLOCKED, result.message)
                else:
                    record_result(candidate.rule_id, ResultStatus.FAILED, result.message)
                if self._on_execution:
                    self._on_execution(result)

            # 마지막 evaluate 시각 갱신 (HealthWatchdog 하트비트용)
            self._last_evaluate_ts = datetime.now()

        except Exception:
            logger.exception("evaluate_all 오류")

    def _collect_candidates(
        self,
        rule: dict,
        cycle_id: str,
    ) -> list[tuple[CandidateSignal, dict[str, Any]]]:
        """개별 규칙 평가 → CandidateSignal 리스트. 양방향 규칙은 BUY+SELL 동시 생성."""
        rule_id = rule.get("id", 0)
        symbol = rule.get("symbol", "")
        results: list[tuple[CandidateSignal, dict[str, Any]]] = []

        try:
            # 시세 조회
            latest = self._bar_builder.get_latest(symbol)
            if not latest:
                logger.debug("Rule %d (%s): 시세 미수신", rule_id, symbol)
                return results

            # 일봉 기반 기술적 지표 주입
            latest["indicators"] = self._indicator_provider.get(symbol)

            context = self._context_cache.get()

            # 조건 평가 → (buy_result, sell_result)
            buy_result, sell_result = self._evaluator.evaluate(rule, latest, context)

            priority = rule.get("priority", 0)
            execution = rule.get("execution") or {}
            qty = int(execution.get("qty_value", rule.get("qty", 1)))
            price = float(latest.get("price", 0))

            if buy_result:
                signal = CandidateSignal(
                    signal_id=uuid.uuid4().hex[:12],
                    cycle_id=cycle_id,
                    rule_id=rule_id,
                    symbol=symbol,
                    side="BUY",
                    priority=priority,
                    desired_qty=qty,
                    detected_at=datetime.now(),
                    latest_price=price,
                    reason="매수 조건 충족",
                    raw_rule=rule,
                    intent_id=uuid.uuid4().hex[:12],
                )
                results.append((signal, latest))

            if sell_result:
                signal = CandidateSignal(
                    signal_id=uuid.uuid4().hex[:12],
                    cycle_id=cycle_id,
                    rule_id=rule_id,
                    symbol=symbol,
                    side="SELL",
                    priority=priority,
                    desired_qty=qty,
                    detected_at=datetime.now(),
                    latest_price=price,
                    reason="매도 조건 충족",
                    raw_rule=rule,
                    intent_id=uuid.uuid4().hex[:12],
                )
                results.append((signal, latest))

        except Exception:
            logger.exception("Rule %d 후보 수집 오류", rule_id)

        return results

    # ── 손실 제한 처리 ──

    async def _cancel_open_orders(self) -> int:
        """손실 제한 발동 시 미체결 주문을 전량 취소한다."""
        cancelled = 0
        try:
            open_orders = await self._broker.get_open_orders()
            for order in open_orders:
                try:
                    await self._broker.cancel_order(order.order_id)
                    cancelled += 1
                except Exception as e:
                    logger.error("미체결 취소 실패 (order_id=%s): %s", order.order_id, e)
        except Exception as e:
            logger.error("미체결 조회 실패: %s", e)
        return cancelled

    async def _notify_loss_lock(self, today_pnl: float) -> None:
        """손실 제한 발동을 AlertMonitor.fire()를 통해 알린다."""
        msg = f"최대 손실 제한 발동: 당일 실현손익 {today_pnl:,.0f}원"
        logger.warning(msg)
        try:
            await self._alert_monitor.fire(
                alert_type="loss_lock",
                severity="critical",
                title="손실 락 발동",
                message=msg,
                action_label="로그 확인",
                action_route="/logs",
                alert_key="loss_lock",
            )
        except Exception as e:
            logger.error("손실 락 AlertMonitor.fire() 실패: %s", e)

    # ── WS 콜백 ──

    def _on_quote(self, event: QuoteEvent) -> None:
        """subscribe_quotes 콜백."""
        self._bar_builder.on_quote(
            symbol=event.symbol,
            price=event.price,
            volume=event.volume,
            timestamp=event.timestamp,
        )
