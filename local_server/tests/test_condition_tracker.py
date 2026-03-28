"""ConditionTracker 단위 테스트 — spec §3.6."""
from local_server.engine.condition_tracker import ConditionTracker


class TestConditionTracker:
    def test_record_and_get(self):
        ct = ConditionTracker()
        ct.record(rule_id=1, cycle="2026-03-29T10:01:00",
                  conditions=[{"index": 0, "expr": "RSI(14) < 30", "result": True, "details": {"RSI(14)": 25}}],
                  position={"status": "미보유"},
                  action={"side": "매수", "quantity": "100%"})
        snap = ct.get_latest(1)
        assert snap is not None
        assert snap["conditions"][0]["result"] is True

    def test_trigger_history(self):
        ct = ConditionTracker()
        ct.record_trigger(1, "2026-03-29T10:01:00", 0, "매수 100%")
        ct.record_trigger(1, "2026-03-29T10:05:00", 2, "매도 전량")
        hist = ct.get_trigger_history(1)
        assert len(hist) == 2
        assert hist[0]["action"] == "매수 100%"

    def test_get_all(self):
        ct = ConditionTracker()
        ct.record(1, "t1", [], {}, None)
        ct.record(2, "t1", [], {}, None)
        assert len(ct.get_all_latest()) == 2

    def test_latest_includes_triggers(self):
        ct = ConditionTracker()
        ct.record(1, "t1", [], {}, None)
        ct.record_trigger(1, "t1", 0, "매수 100%")
        snap = ct.get_latest(1)
        assert len(snap["triggered_history"]) == 1

    def test_trigger_max_limit(self):
        ct = ConditionTracker(max_triggers=3)
        for i in range(5):
            ct.record_trigger(1, f"t{i}", 0, f"action{i}")
        assert len(ct.get_trigger_history(1)) == 3

    def test_get_nonexistent(self):
        ct = ConditionTracker()
        assert ct.get_latest(999) is None
