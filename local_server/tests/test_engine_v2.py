"""v2 엔진 통합 테스트 — parse_v2 + evaluate_v2 + PositionState 파이프라인.

StrategyEngine 전체를 띄우지 않고, RuleEvaluator.evaluate_v2()를 통해
v2 DSL 파이프라인이 올바르게 동작하는지 검증한다.
"""
from __future__ import annotations

import pytest

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from local_server.engine.evaluator import RuleEvaluator
from local_server.engine.position_state import PositionState
from local_server.engine.condition_tracker import ConditionTracker
from local_server.engine.engine import StrategyEngine
from sv_core.parsing import parse_v2, EvalV2Result


# ── 헬퍼 ──

def _market(price: float = 50000, volume: int = 1000, **indicators_1d) -> dict:
    """테스트용 market_data 생성."""
    ind = {
        "rsi_14": indicators_1d.get("rsi_14", 50),
        "ma_20": indicators_1d.get("ma_20", 50000),
        "ema_20": indicators_1d.get("ema_20", 50000),
        "macd": indicators_1d.get("macd", 0),
        "macd_signal": indicators_1d.get("macd_signal", 0),
        "bb_upper_20": indicators_1d.get("bb_upper_20", 55000),
        "bb_lower_20": indicators_1d.get("bb_lower_20", 45000),
        "avg_volume_20": indicators_1d.get("avg_volume_20", 500),
    }
    return {"price": price, "volume": volume, "indicators": {"1d": ind}}


def _ctx(**overrides) -> dict:
    """테스트용 context (포지션 정보 등)."""
    base = {
        "수익률": 0, "보유수량": 0, "고점 대비": 0,
        "수익률고점": 0, "진입가": 0, "보유일": 0, "보유봉": 0,
    }
    base.update(overrides)
    return base


def _rule(script: str, rule_id: int = 1) -> dict:
    """테스트용 rule dict."""
    return {"id": rule_id, "script": script}


# ── RuleEvaluator.evaluate_v2 기본 ──

class TestEvaluateV2Basic:
    """RuleEvaluator.evaluate_v2() 기본 동작."""

    def test_buy_signal(self):
        ev = RuleEvaluator()
        rule = _rule("RSI(14) < 30 AND 보유수량 == 0 -> 매수 100%")
        result = ev.evaluate_v2(rule, _market(rsi_14=25), _ctx())
        assert result.action is not None
        assert result.action.side == "매수"
        assert result.action.qty_type == "percent"
        assert result.action.qty_value == 100.0

    def test_sell_signal(self):
        ev = RuleEvaluator()
        rule = _rule("수익률 >= 5 -> 매도 전량")
        result = ev.evaluate_v2(rule, _market(), _ctx(수익률=6))
        assert result.action is not None
        assert result.action.side == "매도"
        assert result.action.qty_type == "all"

    def test_no_match(self):
        ev = RuleEvaluator()
        rule = _rule("현재가 > 999999 -> 매수 100%")
        result = ev.evaluate_v2(rule, _market(), _ctx())
        assert result.action is None

    def test_snapshots_always_present(self):
        ev = RuleEvaluator()
        rule = _rule("수익률 >= 10 -> 매도 전량\n현재가 > 40000 -> 매수 100%")
        result = ev.evaluate_v2(rule, _market(), _ctx(수익률=3))
        assert len(result.snapshots) == 2

    def test_invalid_script_returns_no_action(self):
        """파싱 실패 시 action=None 반환 (예외 전파 안 함)."""
        ev = RuleEvaluator()
        rule = _rule("이건 유효하지 않은 스크립트입니다 !!!")
        result = ev.evaluate_v2(rule, _market(), _ctx())
        assert result.action is None


# ── AST 캐시 ──

class TestV2AstCache:
    """AST 캐시가 올바르게 동작하는지 검증."""

    def test_same_script_uses_cache(self):
        ev = RuleEvaluator()
        rule = _rule("현재가 > 40000 -> 매수 100%")
        ev.evaluate_v2(rule, _market(), _ctx())
        assert 1 in ev._v2_ast_cache

        # 같은 script로 다시 호출 — 캐시 히트
        ev.evaluate_v2(rule, _market(), _ctx())
        assert 1 in ev._v2_ast_cache

    def test_changed_script_invalidates_cache(self):
        ev = RuleEvaluator()
        ev.evaluate_v2(_rule("현재가 > 40000 -> 매수 100%"), _market(), _ctx())
        old_hash = ev._v2_ast_cache[1][0]

        ev.evaluate_v2(_rule("현재가 > 50000 -> 매수 100%"), _market(), _ctx())
        new_hash = ev._v2_ast_cache[1][0]
        assert old_hash != new_hash

    def test_invalidate_cache_clears_v2(self):
        ev = RuleEvaluator()
        ev.evaluate_v2(_rule("현재가 > 40000 -> 매수 100%"), _market(), _ctx())
        ev.invalidate_cache(1)
        assert 1 not in ev._v2_ast_cache
        assert 1 not in ev._v2_states


# ── 우선순위 해결 (position context 반영) ──

class TestPriorityWithPosition:
    """포지션 상태에 따른 우선순위 해결."""

    def test_sell_over_buy(self):
        ev = RuleEvaluator()
        script = (
            "현재가 > 40000 AND 보유수량 == 0 -> 매수 100%\n"
            "수익률 >= 3 -> 매도 전량"
        )
        result = ev.evaluate_v2(_rule(script), _market(), _ctx(수익률=5))
        assert result.action is not None
        assert result.action.side == "매도"

    def test_full_sell_over_partial(self):
        ev = RuleEvaluator()
        script = (
            "수익률 >= 3 -> 매도 50%\n"
            "수익률 >= 1 -> 매도 전량"
        )
        result = ev.evaluate_v2(_rule(script), _market(), _ctx(수익률=5))
        assert result.action.side == "매도"
        assert result.action.qty_type == "all"

    def test_buy_only_when_no_sell_triggered(self):
        ev = RuleEvaluator()
        script = (
            "수익률 >= 10 -> 매도 전량\n"
            "RSI(14) < 30 AND 보유수량 == 0 -> 매수 100%"
        )
        result = ev.evaluate_v2(
            _rule(script), _market(rsi_14=25), _ctx(수익률=1),
        )
        assert result.action.side == "매수"


# ── DCA (분할 매수) 시나리오 ──

class TestDCAScenario:
    """DCA: 분할매수 스크립트 + PositionState 연동."""

    def test_dca_with_position_state(self):
        """PositionState에서 context를 생성하여 evaluate_v2에 전달."""
        ev = RuleEvaluator()
        pos = PositionState(symbol="005930")
        pos.record_buy(50000, 10)

        script = (
            "수익률 <= -5 AND 보유수량 > 0 -> 매수 50%\n"
            "수익률 >= 10 -> 매도 전량\n"
            "수익률 <= -10 -> 매도 전량"
        )
        rule = _rule(script)

        # 현재가 47000 → 수익률 = -6%
        current_price = 47000
        ctx = pos.to_context(current_price)
        market = _market(price=current_price)

        result = ev.evaluate_v2(rule, market, ctx)
        assert result.action is not None
        assert result.action.side == "매수"
        assert result.action.qty_type == "percent"
        assert result.action.qty_value == 50.0

    def test_dca_stoploss_triggers_sell(self):
        """손절 조건이 매수보다 우선 (전량매도 > 매수)."""
        ev = RuleEvaluator()
        pos = PositionState(symbol="005930")
        pos.record_buy(50000, 10)

        script = (
            "수익률 <= -5 AND 보유수량 > 0 -> 매수 50%\n"
            "수익률 <= -10 -> 매도 전량"
        )
        # 현재가 44000 → 수익률 = -12%
        current_price = 44000
        ctx = pos.to_context(current_price)

        result = ev.evaluate_v2(_rule(script), _market(price=current_price), ctx)
        assert result.action is not None
        assert result.action.side == "매도"
        assert result.action.qty_type == "all"


# ── v1 호환 (매수:/매도: 형식을 parse_v2로 처리) ──

class TestV1CompatThroughV2:
    """v1 스크립트(매수:/매도:)를 parse_v2 경로로 평가."""

    def test_v1_script_via_evaluate_v2(self):
        ev = RuleEvaluator()
        v1_script = "매수: RSI(14) < 30\n매도: 수익률 >= 5"
        rule = _rule(v1_script)

        # 매수 조건 충족
        result = ev.evaluate_v2(rule, _market(rsi_14=25), _ctx())
        assert result.action is not None
        assert result.action.side == "매수"

    def test_v1_sell_condition(self):
        ev = RuleEvaluator()
        v1_script = "매수: RSI(14) < 30\n매도: 수익률 >= 5"
        rule = _rule(v1_script)

        # 매도 조건 충족
        result = ev.evaluate_v2(rule, _market(rsi_14=50), _ctx(수익률=6))
        assert result.action is not None
        assert result.action.side == "매도"


# ── is_v2_script 판별 ──

class TestIsV2Script:
    """스크립트 형식 판별."""

    def test_arrow_unicode(self):
        assert RuleEvaluator.is_v2_script("RSI(14) < 30 → 매수 100%") is True

    def test_arrow_ascii(self):
        assert RuleEvaluator.is_v2_script("RSI(14) < 30 -> 매수 100%") is True

    def test_v1_format(self):
        assert RuleEvaluator.is_v2_script("매수: RSI(14) < 30\n매도: true") is True

    def test_empty(self):
        assert RuleEvaluator.is_v2_script("") is False

    def test_none(self):
        assert RuleEvaluator.is_v2_script(None) is False


# ── 상수 + 커스텀 함수 ──

class TestConstAndCustomFunc:
    """상수 선언 및 커스텀 함수 통합."""

    def test_const_in_rule(self):
        ev = RuleEvaluator()
        script = "손절 = -3\n수익률 <= 손절 -> 매도 전량"
        result = ev.evaluate_v2(_rule(script), _market(), _ctx(수익률=-5))
        assert result.action is not None
        assert result.action.side == "매도"

    def test_custom_func_v2(self):
        ev = RuleEvaluator()
        script = (
            "과매도() = RSI(14) <= 30\n"
            "과매도() AND 보유수량 == 0 -> 매수 100%"
        )
        result = ev.evaluate_v2(
            _rule(script), _market(rsi_14=25), _ctx(),
        )
        assert result.action is not None
        assert result.action.side == "매수"


# ── spec §4 패턴 파싱 ──

class TestSpecSection4Patterns:
    """spec §4에 정의된 주요 패턴이 parse_v2로 파싱 가능한지 검증."""

    def test_trailing_stop(self):
        """추적 손절: 고점 대비 하락."""
        script = "고점 대비 <= -5 -> 매도 전량"
        ast = parse_v2(script)
        assert len(ast.rules) == 1
        assert ast.rules[0].action.side == "매도"

    def test_rsi_buy_sell(self):
        """RSI 기반 매수/매도."""
        script = (
            "RSI(14) < 30 AND 보유수량 == 0 -> 매수 100%\n"
            "RSI(14) > 70 -> 매도 전량"
        )
        ast = parse_v2(script)
        assert len(ast.rules) == 2

    def test_multi_condition_with_const(self):
        """상수 + 다중 조건.

        Note: 손절 = -5 는 unary expression이므로 파서가 custom_func으로
        분류한다 (ConstDecl은 리터럴만). 동작에는 차이 없음.
        """
        script = (
            "목표 = 10\n"
            "손절 = -5\n"
            "수익률 >= 목표 -> 매도 전량\n"
            "수익률 <= 손절 -> 매도 전량\n"
            "RSI(14) < 30 AND 보유수량 == 0 -> 매수 100%"
        )
        ast = parse_v2(script)
        assert len(ast.consts) + len(ast.custom_funcs) == 2
        assert len(ast.rules) == 3

    def test_partial_sell(self):
        """부분 매도."""
        script = "수익률 >= 5 -> 매도 50%"
        ast = parse_v2(script)
        assert ast.rules[0].action.qty_type == "percent"
        assert ast.rules[0].action.qty_value == 50.0

    def test_pnl_high_trailing(self):
        """수익률고점 기반 추적 손절."""
        script = "수익률고점 >= 10 AND 고점 대비 <= -3 -> 매도 전량"
        ast = parse_v2(script)
        assert len(ast.rules) == 1


# ── ConditionTracker 연동 ──

class TestConditionTrackerIntegration:
    """ConditionTracker에 v2 평가 결과를 기록."""

    def test_record_and_retrieve(self):
        ev = RuleEvaluator()
        tracker = ConditionTracker()
        rule = _rule("수익률 >= 5 -> 매도 전량\nRSI(14) < 30 -> 매수 100%")

        result = ev.evaluate_v2(rule, _market(rsi_14=25), _ctx(수익률=3))

        # ConditionTracker에 기록
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
            }

        tracker.record(
            rule_id=1, cycle="test-cycle",
            conditions=conditions, position={}, action=action_dict,
        )

        latest = tracker.get_latest(1)
        assert latest is not None
        assert len(latest["conditions"]) == 2
        assert latest["action"]["side"] == "매수"


# ── 시간 필드 ──

class TestTimeFields:
    """시간 필드(시간, 장시작후, 요일)가 v2 평가에서 사용 가능."""

    def test_time_fields_in_rule(self):
        """장시작후 >= 10 조건이 충족되면 매수 신호 발생."""
        ev = RuleEvaluator()
        rule = _rule("장시작후 >= 10 AND RSI(14) < 30 → 매수 100%")

        from unittest.mock import patch
        from datetime import datetime as _dt

        # 09:30 → 장시작후=30
        fake_now = _dt(2026, 3, 29, 9, 30, 0)
        with patch("local_server.engine.evaluator.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            result = ev.evaluate_v2(rule, _market(rsi_14=25), _ctx())

        assert result.action is not None
        assert result.action.side == "매수"

    def test_time_field_blocks_entry(self):
        """장시작후 < 10이면 진입 차단."""
        ev = RuleEvaluator()
        rule = _rule("장시작후 >= 10 AND RSI(14) < 30 → 매수 100%")

        from unittest.mock import patch
        from datetime import datetime as _dt

        # 09:05 → 장시작후=5
        fake_now = _dt(2026, 3, 29, 9, 5, 0)
        with patch("local_server.engine.evaluator.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            result = ev.evaluate_v2(rule, _market(rsi_14=25), _ctx())

        assert result.action is None


# ── 상태 함수 (횟수/연속) — RuleEvaluator 경유 ──

class TestStateFunctionsThroughEvaluator:
    """횟수/연속 상태 함수가 RuleEvaluator 경유로도 올바르게 동작."""

    def test_count_across_cycles(self):
        ev = RuleEvaluator()
        rule = _rule("횟수(수익률 >= 2, 5) >= 2 -> 매도 전량")

        r1 = ev.evaluate_v2(rule, _market(), _ctx(수익률=3))
        assert r1.action is None  # 1회

        r2 = ev.evaluate_v2(rule, _market(), _ctx(수익률=1))
        assert r2.action is None  # 여전히 1회

        r3 = ev.evaluate_v2(rule, _market(), _ctx(수익률=5))
        assert r3.action is not None  # 2회 → 트리거
        assert r3.action.side == "매도"

    def test_consecutive_through_evaluator(self):
        ev = RuleEvaluator()
        rule = _rule("연속(수익률 >= 1) >= 3 -> 매도 전량")

        assert ev.evaluate_v2(rule, _market(), _ctx(수익률=2)).action is None
        assert ev.evaluate_v2(rule, _market(), _ctx(수익률=2)).action is None
        r3 = ev.evaluate_v2(rule, _market(), _ctx(수익률=2))
        assert r3.action is not None
        assert r3.action.side == "매도"


# ── 체결 루프 통합 테스트 ──


def _make_engine() -> StrategyEngine:
    """mock broker + mock ports로 StrategyEngine 인스턴스 생성."""
    broker = MagicMock()
    mock_log = MagicMock()
    mock_log.write = AsyncMock()
    mock_log.today_realized_pnl = MagicMock(return_value=0.0)
    mock_log.today_executed_amount = MagicMock(return_value=Decimal(0))

    return StrategyEngine(
        broker=broker,
        log=mock_log,
        bar_data=MagicMock(),
        bar_store=MagicMock(),
        ref_data=MagicMock(),
    )


class TestFillLoopIntegration:
    """v2 평가 → 수량 계산 → 체결 → PositionState 갱신 → 다음 사이클 재평가.

    StrategyEngine의 _collect_candidates_v2와 _update_position_state_on_fill을
    직접 호출하여 전체 루프를 검증한다.
    """

    def test_buy_fill_updates_position_state(self):
        """매수 체결 후 PositionState에 보유수량/진입가가 반영된다."""
        engine = _make_engine()
        rule = _rule("RSI(14) < 30 AND 보유수량 == 0 -> 매수 100%")
        market = _market(price=50000, rsi_14=25)

        # 사이클 1: 매수 신호 생성
        results = engine._collect_candidates_v2(rule, "cycle-1", market)
        assert len(results) == 1
        candidate, _ = results[0]
        assert candidate.side == "BUY"

        # 체결 시뮬레이션
        engine._update_position_state_on_fill(candidate)

        # PositionState 검증
        ps = engine._position_states.get("")
        # rule에 symbol이 없으므로 빈 문자열
        assert ps is not None
        assert ps.total_qty > 0
        assert ps.entry_price == 50000

    def test_sell_fill_resets_position_state(self):
        """매도 전량 체결 후 PositionState가 리셋된다."""
        engine = _make_engine()
        rule = _rule(
            "RSI(14) < 30 AND 보유수량 == 0 -> 매수 100%\n"
            "수익률 >= 5 -> 매도 전량"
        )

        # 사전 조건: 포지션 보유 상태
        ps = PositionState(symbol="005930")
        ps.record_buy(50000, 10)
        engine._position_states["005930"] = ps

        rule_with_sym = {**rule, "symbol": "005930"}
        market = _market(price=52600)  # 수익률 = +5.2%

        # 사이클: 매도 신호
        results = engine._collect_candidates_v2(rule_with_sym, "cycle-1", market)
        assert len(results) == 1
        candidate, _ = results[0]
        assert candidate.side == "SELL"
        assert candidate.desired_qty == 10  # 전량

        # 체결
        engine._update_position_state_on_fill(candidate)

        # PositionState 리셋 확인
        assert ps.total_qty == 0
        assert ps.entry_price == 0.0

    def test_full_loop_buy_then_sell(self):
        """매수 → 다음 사이클 재평가 → 매도까지 전체 루프."""
        engine = _make_engine()
        script = (
            "RSI(14) < 30 AND 보유수량 == 0 -> 매수 100%\n"
            "수익률 >= 5 -> 매도 전량"
        )
        rule = {**_rule(script), "symbol": "005930"}

        # --- 사이클 1: 매수 ---
        market_1 = _market(price=50000, rsi_14=25)
        results_1 = engine._collect_candidates_v2(rule, "cycle-1", market_1)
        assert len(results_1) == 1
        buy_candidate, _ = results_1[0]
        assert buy_candidate.side == "BUY"

        # 체결
        engine._update_position_state_on_fill(buy_candidate)
        ps = engine._position_states["005930"]
        assert ps.total_qty > 0

        # --- 사이클 2: 가격 상승, 매도 조건 미충족 ---
        market_2 = _market(price=51000, rsi_14=45)
        results_2 = engine._collect_candidates_v2(rule, "cycle-2", market_2)
        # 수익률 = (51000-50000)/50000*100 = 2% < 5% → 매도 안 됨
        # RSI=45 > 30 → 매수도 안 됨
        assert len(results_2) == 0

        # --- 사이클 3: 가격 더 상승, 매도 조건 충족 ---
        market_3 = _market(price=52600, rsi_14=55)
        results_3 = engine._collect_candidates_v2(rule, "cycle-3", market_3)
        # 수익률 = (52600-50000)/50000*100 = 5.2% >= 5% → 매도
        assert len(results_3) == 1
        sell_candidate, _ = results_3[0]
        assert sell_candidate.side == "SELL"

        # 체결
        engine._update_position_state_on_fill(sell_candidate)
        assert ps.total_qty == 0

    def test_dca_loop_with_position_update(self):
        """DCA: 초기 매수 → 하락 시 추가 매수 → PositionState 누적 확인."""
        engine = _make_engine()
        script = (
            "RSI(14) < 30 AND 보유수량 == 0 -> 매수 100%\n"
            "수익률 <= -5 AND 보유수량 > 0 -> 매수 50%\n"
            "수익률 >= 10 -> 매도 전량"
        )
        rule = {**_rule(script), "symbol": "005930"}

        # --- 사이클 1: 초기 매수 ---
        market_1 = _market(price=50000, rsi_14=25)
        results_1 = engine._collect_candidates_v2(rule, "cycle-1", market_1)
        assert len(results_1) == 1
        assert results_1[0][0].side == "BUY"
        engine._update_position_state_on_fill(results_1[0][0])

        ps = engine._position_states["005930"]
        initial_qty = ps.total_qty
        assert initial_qty > 0
        assert ps.entry_price == 50000

        # --- 사이클 2: 하락 → DCA 매수 ---
        market_2 = _market(price=47000, rsi_14=40)
        results_2 = engine._collect_candidates_v2(rule, "cycle-2", market_2)
        # 수익률 = (47000-50000)/50000*100 = -6% <= -5% → 추가 매수
        assert len(results_2) == 1
        assert results_2[0][0].side == "BUY"
        engine._update_position_state_on_fill(results_2[0][0])

        # 수량 증가, 평단 하락 확인
        assert ps.total_qty > initial_qty
        assert ps.entry_price < 50000  # VWAP로 평단 하락

    def test_condition_tracker_records_through_loop(self):
        """체결 루프 동안 ConditionTracker에 매 사이클 기록이 남는다."""
        engine = _make_engine()
        rule = {**_rule("RSI(14) < 30 AND 보유수량 == 0 -> 매수 100%"), "symbol": "005930"}

        market = _market(price=50000, rsi_14=25)
        engine._collect_candidates_v2(rule, "cycle-1", market)

        tracker = engine._condition_tracker
        latest = tracker.get_latest(1)
        assert latest is not None
        assert len(latest["conditions"]) == 1
        assert latest["conditions"][0]["result"] is True

    def test_execution_count_increments(self):
        """체결 시 실행횟수가 PositionState에 기록된다."""
        engine = _make_engine()
        rule = {**_rule("RSI(14) < 30 AND 보유수량 == 0 -> 매수 100%"), "symbol": "005930"}

        market = _market(price=50000, rsi_14=25)
        results = engine._collect_candidates_v2(rule, "cycle-1", market)
        assert len(results) == 1

        engine._update_position_state_on_fill(results[0][0])

        ps = engine._position_states["005930"]
        # rule_index 0에 대한 실행횟수가 기록되어야 함
        assert sum(ps.execution_counts.values()) > 0
