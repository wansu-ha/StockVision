"""StrategyEngine — 전략 엔진 통합.

EngineScheduler가 1분마다 evaluate_all()을 호출하면
활성 규칙을 순회하며 조건 평가 → 주문 실행을 수행한다.
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable, Optional

from local_server.engine.bar_builder import BarBuilder
from local_server.engine.context_cache import ContextCache
from local_server.engine.evaluator import RuleEvaluator
from local_server.engine.executor import ExecutionResult, OrderExecutor
from local_server.engine.limit_checker import LimitChecker
from local_server.engine.price_verifier import PriceVerifier
from local_server.engine.safeguard import KillSwitchLevel, Safeguard
from local_server.engine.scheduler import EngineScheduler
from local_server.engine.signal_manager import SignalManager

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
        self._scheduler = EngineScheduler(self.evaluate_all)

        # 규칙 캐시 (외부에서 set)
        self._rules: list[dict] = []

        # 콜백 (실행 결과 알림, WS 등)
        self._on_execution: Optional[Callable[[ExecutionResult], Any]] = None

    # ── 라이프사이클 ──

    async def start(self) -> None:
        """엔진 시작."""
        self._running = True
        # 시세 구독: 활성 규칙 종목들
        symbols = list({r.get("symbol", "") for r in self._rules if r.get("is_active")})
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

    # ── 메인 루프 ──

    async def evaluate_all(self) -> None:
        """1분마다 호출되는 메인 루프.

        v2: DSL 양방향 평가 + priority 정렬 + ABC 정합.
        """
        if not self._running:
            return

        try:
            now = datetime.now()

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

            # 잔고 조회 (ABC: 파라미터 없음)
            balance = await self._broker.get_balance()
            holding_symbols = {p.symbol for p in balance.positions}

            # 최대 손실 제한 체크 (당일 실현손익 from logs.db)
            if self._safeguard.is_trading_enabled():
                from local_server.storage.log_db import get_log_db
                today_pnl = get_log_db().today_realized_pnl()
                self._safeguard.check_max_loss(today_pnl, balance.cash + balance.total_eval)

            # Kill Switch / 손실 락 포함 최종 거래 가능 여부
            trading_enabled = self._safeguard.is_trading_enabled()

            for rule in active_rules:
                await self._evaluate_rule(rule, balance, holding_symbols, trading_enabled)

        except Exception:
            logger.exception("evaluate_all 오류")

    async def _evaluate_rule(
        self,
        rule: dict,
        balance: Any,
        holding_symbols: set[str],
        trading_enabled: bool,
    ) -> None:
        """개별 규칙 평가 → 매수/매도 각각 실행."""
        rule_id = rule.get("id", 0)
        symbol = rule.get("symbol", "")

        try:
            # 시세 조회
            latest = self._bar_builder.get_latest(symbol)
            if not latest:
                logger.debug("Rule %d (%s): 시세 미수신", rule_id, symbol)
                return

            context = self._context_cache.get()

            # 조건 평가 → (buy_result, sell_result)
            buy_result, sell_result = self._evaluator.evaluate(rule, latest, context)

            # 매수: 조건 충족 + 미보유 + 거래 가능
            if buy_result and symbol not in holding_symbols and trading_enabled:
                logger.info("Rule %d (%s): 매수 조건 충족", rule_id, symbol)
                result = await self._executor.execute(rule, "BUY", latest, balance)
                logger.info("Rule %d BUY: %s — %s", rule_id, result.status.value, result.message)
                if self._on_execution:
                    self._on_execution(result)

            # 매도: 조건 충족 + 보유 중 + 거래 가능
            if sell_result and symbol in holding_symbols and trading_enabled:
                logger.info("Rule %d (%s): 매도 조건 충족", rule_id, symbol)
                result = await self._executor.execute(rule, "SELL", latest, balance)
                logger.info("Rule %d SELL: %s — %s", rule_id, result.status.value, result.message)
                if self._on_execution:
                    self._on_execution(result)

        except Exception:
            logger.exception("Rule %d 평가 오류", rule_id)

    # ── WS 콜백 ──

    def _on_quote(self, event: QuoteEvent) -> None:
        """subscribe_quotes 콜백."""
        self._bar_builder.on_quote(
            symbol=event.symbol,
            price=event.price,
            volume=event.volume,
            timestamp=event.timestamp,
        )
