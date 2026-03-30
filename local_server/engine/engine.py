"""StrategyEngine — 전략 엔진 통합.

EngineScheduler가 1분마다 evaluate_all()을 호출하면
활성 규칙을 순회하며 조건 평가 → SystemTrader 판단 → 주문 실행을 수행한다.
"""
from __future__ import annotations

import logging
import re as _re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable, Optional

from local_server.engine.alert_monitor import AlertMonitor
from local_server.engine.ports import (
    BarDataPort, BarStorePort, LogPort, ReferenceDataPort,
    LOG_TYPE_ERROR, LOG_TYPE_STRATEGY,
)
from local_server.engine.bar_builder import BarBuilder
from local_server.engine.condition_tracker import ConditionTracker
from local_server.engine.context_cache import ContextCache
from local_server.engine.evaluator import RuleEvaluator
from local_server.engine.indicator_provider import IndicatorProvider
from local_server.engine.executor import ExecutionResult, ExecutionStatus, OrderExecutor
from local_server.engine.limit_checker import LimitChecker
from local_server.engine.position_state import PositionState
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
        log: LogPort,
        bar_data: BarDataPort,
        bar_store: BarStorePort,
        ref_data: ReferenceDataPort,
        config: dict[str, Any] | None = None,
    ) -> None:
        cfg = config or {}
        self._broker = broker
        self._log = log
        self._ref_data = ref_data
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
            log=log,
        )
        self._context_cache = ContextCache(
            ttl_seconds=int(cfg.get("context_ttl", 3600)),
        )
        self._bar_builder = BarBuilder(bar_store=bar_store)
        self._indicator_provider = IndicatorProvider(bar_data=bar_data)
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
        self._alert_monitor = AlertMonitor(
            config=cfg.get("alerts"),
            log=log,
            max_loss_pct=Decimal(str(cfg.get("max_loss_pct", "5.0"))),
        )

        # v2: 종목별 포지션 상태 / 조건 추적
        self._position_states: dict[str, PositionState] = {}
        self._condition_tracker = ConditionTracker()

        # HealthWatchdog가 참조하는 마지막 evaluate 시각
        self._last_evaluate_ts: Optional[datetime] = None

    # ── 라이프사이클 ──

    async def start(self) -> None:
        """엔진 시작."""
        self._running = True
        # LimitChecker 당일 금액 복원 (재시작 시)
        self._limit_checker.restore_from_db(self._log)
        # 활성 규칙 종목들
        symbols = list({r.get("symbol", "") for r in self._rules if r.get("is_active")})
        # 일봉 지표 계산 (yfinance)
        if symbols:
            market_map = await self._resolve_markets(symbols)
            await self._indicator_provider.refresh(symbols, market_map)
        # 시세 구독
        if symbols:
            await self._broker.subscribe_quotes(symbols, self._on_quote)
        await self._scheduler.start()
        # 포지션 동기화 (시작 시 1회)
        await self._sync_positions()
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

    @property
    def condition_tracker(self) -> ConditionTracker:
        return self._condition_tracker

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

            # 주기적 포지션 동기화 (60초마다)
            import time as _time
            _now_ts = _time.monotonic()
            if _now_ts - self._last_sync_ts >= 60:
                await self._sync_positions()
                self._last_sync_ts = _now_ts

            # 잔고 / 미체결 조회 + 당일 손익 (AlertMonitor에 필요, 무조건 조회)
            balance = await self._broker.get_balance()
            holding_symbols = {p.symbol for p in balance.positions}
            open_orders = await self._broker.get_open_orders()
            today_pnl = self._log.today_realized_pnl()

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

            # ── 분봉 지표 갱신 ──
            active_tfs: dict[str, set[str]] = {}
            for rule in active_rules:
                sym = rule.get("symbol", "")
                for tf in _extract_rule_tfs(rule):
                    active_tfs.setdefault(sym, set()).add(tf)

            for sym, tfs in active_tfs.items():
                for tf in tfs:
                    await self._indicator_provider.refresh_minute(sym, tf)

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
                await self._log.write(
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
                await self._log.write(
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

                # v2 PositionState 갱신 (체결 성공 시)
                if result.status == ExecutionStatus.SUCCESS:
                    self._update_position_state_on_fill(candidate)

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

            # TF별 기술적 지표 주입: {tf: indicators_dict}
            indicators_by_tf: dict[str, dict] = {}
            daily_ind = self._indicator_provider.get(symbol, "1d")
            indicators_by_tf["1d"] = daily_ind
            for tf in _extract_rule_tfs(rule):
                minute_ind = self._indicator_provider.get(symbol, tf)
                if minute_ind is not None:
                    indicators_by_tf[tf] = minute_ind
            latest["indicators"] = indicators_by_tf

            # v2 분기: script에 → / -> / 매수: / 매도: 가 있으면 v2 경로
            script = rule.get("script") or ""
            if RuleEvaluator.is_v2_script(script):
                return self._collect_candidates_v2(rule, cycle_id, latest)

            # ── v1 경로 (기존 코드) ──
            context = self._context_cache.get()
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

    def _collect_candidates_v2(
        self,
        rule: dict,
        cycle_id: str,
        latest: dict[str, Any],
    ) -> list[tuple[CandidateSignal, dict[str, Any]]]:
        """v2 DSL 규칙 평가 → CandidateSignal 리스트."""
        rule_id = rule.get("id", 0)
        symbol = rule.get("symbol", "")
        price = float(latest.get("price", 0))
        results: list[tuple[CandidateSignal, dict[str, Any]]] = []

        try:
            # PositionState: 종목별 (per-symbol)
            ps = self._position_states.get(symbol)
            if ps is None:
                ps = PositionState(symbol=symbol)
                self._position_states[symbol] = ps

            ps.update_cycle(price)

            # context = 포지션 상태 + 실행횟수
            context = ps.to_context(price)
            for idx, cnt in ps.execution_counts.items():
                context[f"실행횟수_{idx}"] = cnt

            # v2 평가
            result = self._evaluator.evaluate_v2(rule, latest, context)

            # ConditionTracker 기록 (매 사이클)
            conditions = [
                {"index": s.rule_index, "result": s.result, "details": s.details}
                for s in result.snapshots
            ]
            action_dict = None
            if result.action:
                action_dict = {
                    "side": result.action.side,
                    "qty_type": result.action.qty_type,
                    "qty_value": result.action.qty_value,
                    "rule_index": result.action.rule_index,
                }
            self._condition_tracker.record(
                rule_id=rule_id, cycle=cycle_id,
                conditions=conditions, position=context, action=action_dict,
            )

            if result.action is None:
                return results

            action = result.action
            side = "BUY" if action.side == "매수" else "SELL"

            # 수량 계산
            qty = self._calc_v2_qty(action, side, ps, price, rule)

            if qty <= 0:
                logger.debug("Rule %d v2: qty=0, 스킵", rule_id)
                return results

            # raw_rule에 execution.qty_value를 오버라이드한 사본 전달
            rule_copy = {**rule, "execution": {
                **(rule.get("execution") or {}),
                "qty_value": qty,
            }}

            signal = CandidateSignal(
                signal_id=uuid.uuid4().hex[:12],
                cycle_id=cycle_id,
                rule_id=rule_id,
                symbol=symbol,
                side=side,
                priority=rule.get("priority", 0),
                desired_qty=qty,
                detected_at=datetime.now(),
                latest_price=price,
                reason=action.expr_text or f"v2 규칙 #{action.rule_index} 충족",
                raw_rule=rule_copy,
                intent_id=uuid.uuid4().hex[:12],
            )
            results.append((signal, latest))

            # ConditionTracker 트리거 기록
            self._condition_tracker.record_trigger(
                rule_id=rule_id,
                at=datetime.now().isoformat(),
                index=action.rule_index,
                action=f"{side} {qty}",
            )

        except Exception:
            logger.exception("Rule %d v2 후보 수집 오류 — v1 폴백 시도", rule_id)
            # v2 실패 시 v1 폴백
            try:
                context = self._context_cache.get()
                buy_result, sell_result = self._evaluator.evaluate(rule, latest, context)
                execution = rule.get("execution") or {}
                qty = int(execution.get("qty_value", rule.get("qty", 1)))
                priority = rule.get("priority", 0)

                if buy_result:
                    results.append((CandidateSignal(
                        signal_id=uuid.uuid4().hex[:12], cycle_id=cycle_id,
                        rule_id=rule_id, symbol=symbol, side="BUY",
                        priority=priority, desired_qty=qty,
                        detected_at=datetime.now(), latest_price=price,
                        reason="매수 조건 충족 (v1 폴백)", raw_rule=rule,
                        intent_id=uuid.uuid4().hex[:12],
                    ), latest))
                if sell_result:
                    results.append((CandidateSignal(
                        signal_id=uuid.uuid4().hex[:12], cycle_id=cycle_id,
                        rule_id=rule_id, symbol=symbol, side="SELL",
                        priority=priority, desired_qty=qty,
                        detected_at=datetime.now(), latest_price=price,
                        reason="매도 조건 충족 (v1 폴백)", raw_rule=rule,
                        intent_id=uuid.uuid4().hex[:12],
                    ), latest))
            except Exception:
                logger.exception("Rule %d v1 폴백도 실패", rule_id)

        return results

    def _calc_v2_qty(
        self,
        action: Any,
        side: str,
        ps: PositionState,
        price: float,
        rule: dict,
    ) -> int:
        """v2 action의 qty_type/qty_value로 실제 수량 계산."""
        if action.qty_type == "percent":
            if side == "BUY":
                # 매수 N% = budget_ratio 기반 일일 예산의 N%
                budget_ratio = float(self._limit_checker._budget_ratio)
                # cash는 아직 모르므로 최소 1주. 실제 예산 제한은 SystemTrader/LimitChecker가 처리.
                qty = max(1, int(action.qty_value / 100))
            else:
                # 매도 N% = 보유수량의 N%
                qty = max(1, int(ps.total_qty * action.qty_value / 100)) if ps.total_qty > 0 else 0
        else:
            # "all" — 전량
            if side == "BUY":
                execution = rule.get("execution") or {}
                qty = int(execution.get("qty_value", rule.get("qty", 1)))
            else:
                qty = ps.total_qty
        return qty

    # ── v2 체결 후 PositionState 갱신 ──

    def _update_position_state_on_fill(self, candidate: CandidateSignal) -> None:
        """체결 성공 시 PositionState에 매수/매도 기록."""
        symbol = candidate.symbol
        ps = self._position_states.get(symbol)
        if ps is None:
            return  # v1 규칙이면 PositionState 없음 — 무시

        price = candidate.latest_price
        qty = candidate.desired_qty

        if candidate.side == "BUY":
            ps.record_buy(price, qty)
        elif candidate.side == "SELL":
            ps.record_sell(qty)

        # raw_rule에서 v2 action의 rule_index를 추출하여 실행횟수 기록
        action_dict = self._condition_tracker.get_latest(candidate.rule_id)
        if action_dict and action_dict.get("action"):
            rule_index = action_dict["action"].get("rule_index", 0)
            ps.record_execution(rule_index)

    # ── 포지션 동기화 ──

    _last_sync_ts: float = 0.0

    async def _sync_positions(self) -> None:
        """브로커 잔고와 PositionState를 동기화한다."""
        if not self._broker or not self._broker.is_connected:
            return
        try:
            balance = await self._broker.get_balance()
        except Exception:
            logger.debug("포지션 동기화: 잔고 조회 실패 (스킵)")
            return

        broker_positions = {p.symbol: p for p in balance.positions}
        for symbol, ps in self._position_states.items():
            bp = broker_positions.get(symbol)
            if bp is None:
                if ps.total_qty > 0:
                    logger.debug("포지션 동기화: %s 잔고에 없음 → 리셋", symbol)
                    ps.record_sell(ps.total_qty)
            elif bp.qty != ps.total_qty or abs(bp.avg_price - ps.entry_price) > 0.01:
                logger.debug(
                    "포지션 동기화: %s qty %d→%d, price %.0f→%.0f",
                    symbol, ps.total_qty, bp.qty, ps.entry_price, bp.avg_price,
                )
                ps.total_qty = bp.qty
                ps.entry_price = bp.avg_price

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

    # ── 시장 구분 조회 ──

    async def _resolve_markets(self, symbols: list[str]) -> dict[str, str]:
        """종목별 시장 구분 반환. StockMasterCache 기반, KIS get_quote 폴백.

        Returns:
            {symbol: "KOSPI"|"KOSDAQ"} — 확인된 종목만 포함 (미확인은 키 없음)
        """
        all_markets = self._ref_data.get_market_map()

        market_map: dict[str, str] = {}
        unknown: list[str] = []
        for sym in symbols:
            market = all_markets.get(sym, "")
            if market in ("KOSPI", "KOSDAQ"):
                market_map[sym] = market
            else:
                unknown.append(sym)

        for sym in unknown:
            market = await self._lookup_market_via_broker(sym)
            if market:
                market_map[sym] = market
                logger.info("KIS 폴백으로 시장 확인 [%s]: %s", sym, market)

        return market_map

    async def _lookup_market_via_broker(self, symbol: str) -> str:
        """브로커 get_quote raw 응답에서 시장 구분 추출 (KIS 전용).

        KIS get_quote 응답의 output.rprs_mrkt_kor_name을 파싱한다.
        KIS 미연결, 키움, Mock 등에서는 조용히 실패하여 빈 문자열 반환.
        """
        try:
            quote = await self._broker.get_quote(symbol)
            raw_output = getattr(quote, "raw", {}).get("output", {})
            market_name = raw_output.get("rprs_mrkt_kor_name", "")
            if "코스닥" in market_name:
                return "KOSDAQ"
            if "코스피" in market_name or "유가증권" in market_name:
                return "KOSPI"
        except Exception:
            pass
        return ""

    # ── WS 콜백 ──

    def _on_quote(self, event: QuoteEvent) -> None:
        """subscribe_quotes 콜백."""
        self._bar_builder.on_quote(
            symbol=event.symbol,
            price=event.price,
            volume=event.volume,
            timestamp=event.timestamp,
        )


# ── 모듈 레벨 헬퍼 ──

_TF_PATTERN = _re.compile(r'"(1m|5m|15m|1h)"')


def _extract_rule_tfs(rule: dict) -> list[str]:
    """규칙 script에서 사용된 분봉 TF 목록을 추출한다.

    DSL script에서 "5m" 형태 문자열을 파싱하여 중복 없이 반환.
    script가 없거나 파싱 실패 시 빈 리스트 반환.
    """
    script = rule.get("script") or ""
    if not script:
        return []
    return list(dict.fromkeys(_TF_PATTERN.findall(script)))
