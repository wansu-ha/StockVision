"""AlertMonitor — 장중 실시간 경고 평가.

evaluate_all() 루프에서 1분마다 호출되어 5종 경고를 평가한다.
fire()는 외부에서 경고를 주입하는 공개 인터페이스 (전략 DSL alert() 용).
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

# 허용된 action.route 화이트리스트
ALLOWED_ROUTES = frozenset({"/", "/portfolio", "/logs", "/settings"})

# 경고 심각도
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"


class AlertMonitor:
    """장중 실시간 경고 평가기.

    evaluate_all()에서 check_all()을 호출하면 5종 경고를 평가하고
    조건 충족 시 fire()를 통해 WS 브로드캐스트 + LogDB 기록을 수행한다.
    """

    _cooldown = timedelta(minutes=30)

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._cfg = cfg
        # 쿨다운 상태: alert_key → (마지막 발송 시각, 발송 시 값)
        self._fired: dict[str, tuple[datetime, float | None]] = {}
        # WS 브로드캐스트 콜백 (async)
        self._broadcast: Optional[Callable[[dict], Awaitable[None]]] = None
        logger.info("AlertMonitor initialized")

    def set_broadcast(self, callback: Callable[[dict], Awaitable[None]]) -> None:
        """WS 브로드캐스트 콜백 등록."""
        self._broadcast = callback

    # ── 공개 인터페이스 ──

    async def check_all(
        self,
        balance: Any,
        open_orders: list[Any],
        today_pnl: Any,
    ) -> None:
        """모든 경고 규칙을 평가한다.

        evaluate_all()에서 trading_enabled 체크 앞에 호출된다.
        """
        cfg = self._cfg
        if not cfg.get("master_enabled", True):
            return

        rules = cfg.get("rules", {})

        # 1. 종목 손실 경고
        if rules.get("position_loss", {}).get("enabled", True):
            threshold = float(rules.get("position_loss", {}).get("threshold_pct", -3.0))
            await self._check_position_loss(balance, threshold)

        # 2. 급변동 경고
        if rules.get("volatility", {}).get("enabled", True):
            threshold = float(rules.get("volatility", {}).get("threshold_pct", 5.0))
            await self._check_volatility(balance, threshold)

        # 3. 일일 손실 한도 근접
        if rules.get("daily_loss_proximity", {}).get("enabled", True):
            await self._check_daily_loss_proximity(balance, today_pnl)

        # 4. 미체결 장기 방치
        if rules.get("stale_order", {}).get("enabled", True):
            threshold_min = int(rules.get("stale_order", {}).get("threshold_min", 10))
            await self._check_stale_orders(open_orders, threshold_min)

        # 5. 장 종료 임박 미체결
        if rules.get("market_close_orders", {}).get("enabled", True):
            await self._check_market_close_orders(open_orders)

    async def fire(
        self,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        symbol: str | None = None,
        action_label: str | None = None,
        action_route: str | None = None,
        current_value: float | None = None,
        alert_key: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """경고를 발송한다.

        외부(전략 DSL alert()) 또는 내부 체커에서 호출한다.
        쿨다운이 걸려 있으면 발송하지 않는다.
        """
        key = alert_key or f"{alert_type}:{symbol or 'global'}"
        if not self._should_fire(key, current_value):
            return

        # action.route 화이트리스트 검증
        if action_route and action_route not in ALLOWED_ROUTES:
            logger.warning("alert fire: 허용되지 않은 route 무시 — %s", action_route)
            action_route = None
            action_label = None

        alert_id = str(uuid.uuid4())
        now = datetime.now()

        payload: dict[str, Any] = {
            "id": alert_id,
            "alert_type": alert_type,
            "severity": severity,
            "symbol": symbol,
            "title": title,
            "message": message,
            "ts": now.isoformat(),
        }
        if action_label and action_route:
            payload["action"] = {"label": action_label, "route": action_route}

        # WS 브로드캐스트
        if self._broadcast:
            try:
                await self._broadcast({"type": "alert", "data": payload})
            except Exception as e:
                logger.error("AlertMonitor broadcast 실패: %s", e)

        # LogDB 기록
        try:
            from local_server.storage.log_db import get_log_db, LOG_TYPE_ALERT
            await get_log_db().async_write(
                LOG_TYPE_ALERT,
                message,
                symbol=symbol,
                meta={
                    "alert_id": alert_id,
                    "alert_type": alert_type,
                    "severity": severity,
                    "current_value": current_value,
                    **(meta or {}),
                },
            )
        except Exception as e:
            logger.error("AlertMonitor LogDB 기록 실패: %s", e)

        logger.info(
            "경고 발송 [%s] %s — %s (key=%s)",
            severity.upper(), alert_type, message, key,
        )

    # ── 쿨다운 ──

    def _should_fire(self, key: str, current_value: float | None = None) -> bool:
        """쿨다운 체크. 심각도 상승(값 1.5배 악화) 시 쿨다운 무시."""
        last = self._fired.get(key)
        if last:
            last_ts, last_val = last
            if datetime.now() - last_ts < self._cooldown:
                # 심각도 상승 판단: 절댓값 기준 1.5배 이상 악화
                if (
                    current_value is not None
                    and last_val is not None
                    and abs(current_value) > abs(last_val) * 1.5
                ):
                    pass  # 쿨다운 무시, 재발송
                else:
                    return False
        self._fired[key] = (datetime.now(), current_value)
        return True

    # ── 체커 ──

    async def _check_position_loss(self, balance: Any, threshold_pct: float) -> None:
        """보유종목 평가손익률 ≤ threshold_pct 이면 경고."""
        positions = getattr(balance, "positions", [])
        for pos in positions:
            pnl_pct = getattr(pos, "pnl_pct", None)
            if pnl_pct is None:
                continue
            if float(pnl_pct) <= threshold_pct:
                symbol = getattr(pos, "symbol", "")
                name = getattr(pos, "name", symbol)
                await self.fire(
                    alert_type="position_loss",
                    severity=SEVERITY_WARNING,
                    title="종목 손실 경고",
                    message=f"{name} 평가손익 {pnl_pct:.1f}% (임계값 {threshold_pct:.0f}%)",
                    symbol=symbol,
                    action_label="잔고 확인",
                    action_route="/portfolio",
                    current_value=float(pnl_pct),
                    alert_key=f"position_loss:{symbol}",
                )

    async def _check_volatility(self, balance: Any, threshold_pct: float) -> None:
        """보유종목 전일 대비 ±threshold_pct% 이상 급변동 시 경고."""
        positions = getattr(balance, "positions", [])
        for pos in positions:
            change_pct = getattr(pos, "change_pct", None)  # 전일 대비 등락률
            if change_pct is None:
                continue
            if abs(float(change_pct)) >= threshold_pct:
                symbol = getattr(pos, "symbol", "")
                name = getattr(pos, "name", symbol)
                direction = "급등" if float(change_pct) > 0 else "급락"
                await self.fire(
                    alert_type="volatility",
                    severity=SEVERITY_WARNING,
                    title="급변동 경고",
                    message=f"{name} {direction} {change_pct:+.1f}% (임계값 ±{threshold_pct:.0f}%)",
                    symbol=symbol,
                    action_label="잔고 확인",
                    action_route="/portfolio",
                    current_value=abs(float(change_pct)),
                    alert_key=f"volatility:{symbol}",
                )

    async def _check_daily_loss_proximity(self, balance: Any, today_pnl: Any) -> None:
        """당일 실현손익이 max_loss_pct의 80% 도달 시 경고."""
        try:
            from local_server.config import get_config
            from decimal import Decimal
            max_loss_pct = Decimal(str(get_config().get("max_loss_pct", "5.0")))
            total_equity = getattr(balance, "cash", Decimal(0)) + getattr(balance, "total_eval", Decimal(0))
            if total_equity <= 0:
                return
            pnl = Decimal(str(today_pnl))
            if pnl >= 0:
                return
            loss_pct = abs(pnl) / total_equity * 100
            trigger_pct = max_loss_pct * Decimal("0.8")
            if loss_pct >= trigger_pct:
                await self.fire(
                    alert_type="daily_loss_proximity",
                    severity=SEVERITY_WARNING,
                    title="일일 손실 한도 근접",
                    message=(
                        f"당일 손실 {float(loss_pct):.1f}% — "
                        f"한도({float(max_loss_pct):.0f}%)의 {float(loss_pct/max_loss_pct*100):.0f}% 도달"
                    ),
                    action_label="로그 확인",
                    action_route="/logs",
                    current_value=float(loss_pct),
                    alert_key="daily_loss_proximity",
                )
        except Exception as e:
            logger.debug("daily_loss_proximity 체크 오류: %s", e)

    async def _check_stale_orders(self, open_orders: list[Any], threshold_min: int) -> None:
        """주문 제출 후 threshold_min 분 경과 미체결 주문 경고."""
        now = datetime.now()
        for order in open_orders:
            submitted_at = getattr(order, "submitted_at", None)
            if submitted_at is None:
                continue
            elapsed = now - submitted_at
            if elapsed >= timedelta(minutes=threshold_min):
                order_id = getattr(order, "order_id", "")
                symbol = getattr(order, "symbol", "")
                elapsed_min = int(elapsed.total_seconds() / 60)
                await self.fire(
                    alert_type="stale_order",
                    severity=SEVERITY_WARNING,
                    title="미체결 장기 방치",
                    message=f"주문 {order_id} 미체결 {elapsed_min}분 경과",
                    symbol=symbol,
                    action_label="로그 확인",
                    action_route="/logs",
                    current_value=float(elapsed_min),
                    alert_key=f"stale_order:{order_id}",
                )

    async def _check_market_close_orders(self, open_orders: list[Any]) -> None:
        """15:20 이후 미체결 주문 존재 시 경고."""
        now = datetime.now()
        if not (now.hour == 15 and now.minute >= 20):
            return
        if not open_orders:
            return
        count = len(open_orders)
        await self.fire(
            alert_type="market_close_orders",
            severity=SEVERITY_WARNING,
            title="장 종료 임박 미체결",
            message=f"15:20 이후 미체결 주문 {count}건 존재",
            action_label="로그 확인",
            action_route="/logs",
            current_value=float(count),
            alert_key="market_close_orders",
        )
