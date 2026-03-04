"""
조건 평가 엔진

- 컨텍스트(클라우드) + 실시간 가격(키움) 기반 조건 평가
- AND 논리: 모든 조건 충족 시에만 True
"""
import logging
import operator as op

from engine.models import TradingRule, rule_from_dict

logger = logging.getLogger(__name__)

_OPS = {
    ">":  op.gt,
    "<":  op.lt,
    ">=": op.ge,
    "<=": op.le,
    "==": op.eq,
}


class RuleEvaluator:
    def __init__(self, context: dict, prices: dict[str, float]):
        """
        context: 클라우드 시장 컨텍스트 (rsi_14, kospi_change 등)
        prices:  종목별 현재가 {stock_code: float}
        """
        self.ctx    = context
        self.prices = prices

    def evaluate(self, rule: TradingRule) -> bool:
        for cond in rule.conditions:
            val = self._resolve(cond.variable, rule.symbol)
            if val is None:
                logger.debug(f"변수 없음: {cond.variable} — 규칙 스킵")
                return False
            fn = _OPS.get(cond.operator)
            if fn is None:
                logger.warning(f"알 수 없는 연산자: {cond.operator}")
                return False
            if not fn(val, cond.value):
                return False
        return True

    def _resolve(self, variable: str, symbol: str) -> float | None:
        if variable == "price":
            return self.prices.get(symbol)
        # 플랫 조회 먼저
        raw = self.ctx.get(variable)
        # 없으면 중첩 market 섹션 조회 (kospi_rsi_14 등)
        if raw is None:
            raw = self.ctx.get("market", {}).get(variable)
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None


async def evaluate_rule(rule: dict) -> None:
    """scheduler.py에서 호출 — dict 형태 규칙 1개 평가"""
    from cloud.context import get_context
    from engine.signal import get_signal_manager

    try:
        trading_rule = rule_from_dict(rule)
        ctx          = get_context()
        evaluator    = RuleEvaluator(ctx, prices={})

        if evaluator.evaluate(trading_rule):
            await get_signal_manager().process(trading_rule)
    except Exception as e:
        logger.error(f"규칙 평가 오류 (rule_id={rule.get('id')}): {e}")
