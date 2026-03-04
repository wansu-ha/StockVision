"""
신호 관리 + 중복 실행 방지

상태 머신: NEW → SENT → FILLED
- 같은 규칙이 이미 SENT 상태면 재전송 스킵
- 당일 이미 체결된 규칙 재실행 방지
"""
import logging
from datetime import date

from engine.models import TradingRule

logger = logging.getLogger(__name__)


class SignalManager:
    def __init__(self):
        self._state: dict[int, str] = {}     # rule_id → "SENT" | "FILLED"
        self._exec_date: dict[int, date] = {}  # rule_id → 마지막 실행일

    def should_execute(self, rule: TradingRule) -> bool:
        if self._state.get(rule.rule_id) == "SENT":
            return False
        if self._exec_date.get(rule.rule_id) == date.today():
            return False
        return True

    async def process(self, rule: TradingRule) -> None:
        if not self.should_execute(rule):
            logger.debug(f"중복 실행 스킵: rule_id={rule.rule_id}")
            return

        self._state[rule.rule_id]     = "SENT"
        self._exec_date[rule.rule_id] = date.today()
        logger.info(f"신호 생성: {rule.side} {rule.symbol} {rule.quantity}주 (rule_id={rule.rule_id})")

        try:
            from storage.config_manager import get_config_manager
            account_no = get_config_manager().get("account_no", "")

            from kiwoom.order import get_order_manager, OrderRequest
            req = OrderRequest(
                account_no=account_no,
                symbol=rule.symbol,
                side=rule.side,
                qty=rule.quantity,
                price=0,
                order_type="03",  # 시장가
            )
            await get_order_manager().enqueue(req)

            from storage.log_db import log_execution
            log_execution(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                side=rule.side,
                stock_code=rule.symbol,
                quantity=rule.quantity,
                status="SENT",
                message="주문 큐 전송 완료",
            )

            from routers.ws import broadcast
            await broadcast({
                "type": "signal_sent",
                "data": {
                    "rule_id":   rule.rule_id,
                    "rule_name": rule.name,
                    "side":      rule.side,
                    "symbol":    rule.symbol,
                    "quantity":  rule.quantity,
                },
            })
        except Exception as e:
            logger.error(f"주문 실패 (rule_id={rule.rule_id}): {e}")
            self._state.pop(rule.rule_id, None)  # 실패 시 재시도 허용

    def mark_filled(self, rule_id: int) -> None:
        self._state[rule_id] = "FILLED"
        logger.info(f"체결 확인: rule_id={rule_id}")


_signal_manager: SignalManager | None = None


def get_signal_manager() -> SignalManager:
    global _signal_manager
    if _signal_manager is None:
        _signal_manager = SignalManager()
    return _signal_manager
