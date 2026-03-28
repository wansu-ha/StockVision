"""IndicatorHistory 링버퍼 단위 테스트."""
from local_server.engine.indicator_history import IndicatorHistory


def test_push_and_get():
    ih = IndicatorHistory()
    ih.push("rsi", 60.0)
    ih.push("rsi", 65.0)
    ih.push("rsi", 70.0)
    # index=0 → 가장 최근값
    assert ih.get("rsi", 0) == 70.0
    assert ih.get("rsi", 1) == 65.0
    assert ih.get("rsi", 2) == 60.0


def test_out_of_range():
    ih = IndicatorHistory()
    ih.push("rsi", 50.0)
    assert ih.get("rsi", 1) is None       # 범위 초과
    assert ih.get("macd", 0) is None      # 없는 키


def test_eviction():
    ih = IndicatorHistory(max_size=3)
    for v in [1.0, 2.0, 3.0, 4.0]:
        ih.push("x", v)
    # 최대 3개 유지 — 가장 오래된 1.0 제거됨
    assert ih.get("x", 0) == 4.0
    assert ih.get("x", 1) == 3.0
    assert ih.get("x", 2) == 2.0
    assert ih.get("x", 3) is None


def test_as_list():
    ih = IndicatorHistory()
    for v in [10.0, 20.0, 30.0]:
        ih.push("vol", v)
    result = ih.as_list("vol")
    assert result == [10.0, 20.0, 30.0]  # 오래된 것 → 최신 순서
    assert ih.as_list("missing") == []
