"""분봉 IndicatorProvider + evaluator tf 분기 단위 테스트."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from local_server.engine.indicator_provider import IndicatorProvider
from local_server.engine.evaluator import RuleEvaluator


# ═══════════════════════════════════════
# IndicatorProvider 테스트
# ═══════════════════════════════════════

class TestIndicatorProviderDaily:
    """일봉(tf="1d") 동작 유지 검증."""

    def setup_method(self) -> None:
        self.provider = IndicatorProvider()

    def test_no_cache_returns_empty(self) -> None:
        """캐시 없을 때 일봉은 빈 dict 반환."""
        result = self.provider.get("005930", "1d")
        assert result == {}

    def test_daily_cache_returns_indicators(self) -> None:
        """일봉 캐시 존재 시 indicators dict 반환."""
        from datetime import date
        indicators = {"rsi_14": 55.0, "ma_20": 70000.0}
        self.provider._daily_cache["005930"] = {
            "date": date.today(),
            "indicators": indicators,
        }
        result = self.provider.get("005930", "1d")
        assert result == indicators

    def test_default_tf_is_daily(self) -> None:
        """tf 인자 생략 시 일봉 캐시 반환."""
        from datetime import date
        indicators = {"rsi_14": 60.0}
        self.provider._daily_cache["005930"] = {
            "date": date.today(),
            "indicators": indicators,
        }
        assert self.provider.get("005930") == indicators


class TestIndicatorProviderMinute:
    """분봉 캐시 히트/만료/미존재 검증."""

    def setup_method(self) -> None:
        self.provider = IndicatorProvider()

    def test_minute_cache_hit(self) -> None:
        """분봉 캐시 유효 시 indicators dict 반환."""
        indicators = {"rsi_14": 45.0, "ma_5": 50100.0}
        self.provider._minute_cache["005930"] = {
            "5m": {
                "expires": datetime.now() + timedelta(seconds=30),
                "indicators": indicators,
            }
        }
        result = self.provider.get("005930", "5m")
        assert result == indicators

    def test_minute_cache_expired_returns_none(self) -> None:
        """분봉 캐시 만료 시 None 반환."""
        self.provider._minute_cache["005930"] = {
            "5m": {
                "expires": datetime.now() - timedelta(seconds=1),
                "indicators": {"rsi_14": 45.0},
            }
        }
        result = self.provider.get("005930", "5m")
        assert result is None

    def test_minute_cache_expired_cleans_entry(self) -> None:
        """분봉 캐시 만료 후 캐시 항목이 제거된다."""
        self.provider._minute_cache["005930"] = {
            "5m": {
                "expires": datetime.now() - timedelta(seconds=1),
                "indicators": {"rsi_14": 45.0},
            }
        }
        self.provider.get("005930", "5m")
        assert "5m" not in self.provider._minute_cache.get("005930", {})

    def test_minute_no_cache_returns_none(self) -> None:
        """분봉 캐시 미존재 시 None 반환."""
        result = self.provider.get("005930", "1m")
        assert result is None

    def test_different_tfs_independent(self) -> None:
        """다른 TF 캐시가 독립적으로 동작한다."""
        self.provider._minute_cache["005930"] = {
            "5m": {
                "expires": datetime.now() + timedelta(seconds=30),
                "indicators": {"rsi_14": 45.0},
            }
            # "1m" 없음
        }
        assert self.provider.get("005930", "5m") is not None
        assert self.provider.get("005930", "1m") is None


# ═══════════════════════════════════════
# RuleEvaluator tf 분기 테스트
# ═══════════════════════════════════════

class TestEvaluatorTfBranch:
    """make_indicator_func의 tf 분기 검증."""

    def setup_method(self) -> None:
        self.evaluator = RuleEvaluator()

    def _make_rule(self, script: str) -> dict:
        return {"id": 1, "script": script}

    def _make_market_data(self, indicators_by_tf: dict) -> dict:
        return {"price": Decimal("50000"), "volume": 1000, "indicators": indicators_by_tf}

    def test_daily_indicator_no_tf(self) -> None:
        """tf 인자 없으면 일봉(1d) 지표 사용."""
        md = self._make_market_data({
            "1d": {"rsi_14": 55.0},
        })
        rule = self._make_rule("매수: RSI(14) > 50\n매도: false")
        buy, sell = self.evaluator.evaluate(rule, md, {})
        assert buy is True

    def test_minute_indicator_with_tf(self) -> None:
        """tf="5m" 인자 시 분봉 지표 사용."""
        md = self._make_market_data({
            "1d": {"rsi_14": 30.0},   # 일봉: RSI 30
            "5m": {"rsi_14": 65.0},   # 5분봉: RSI 65
        })
        # 5분봉 RSI > 60 → 매수
        rule = self._make_rule('매수: RSI(14, "5m") > 60\n매도: false')
        buy, _ = self.evaluator.evaluate(rule, md, {})
        assert buy is True

    def test_minute_indicator_missing_tf_returns_none(self) -> None:
        """분봉 TF 캐시 없으면 None → 조건 False."""
        md = self._make_market_data({
            "1d": {"rsi_14": 55.0},
            # "5m" 없음
        })
        rule = self._make_rule('매수: RSI(14, "5m") > 50\n매도: false')
        buy, _ = self.evaluator.evaluate(rule, md, {})
        assert buy is False

    def test_daily_fallback_when_only_daily_present(self) -> None:
        """일봉만 있을 때 tf=None → 1d 정상 동작."""
        md = self._make_market_data({
            "1d": {"ma_20": 75000.0},
        })
        rule = self._make_rule("매수: MA(20) > 70000\n매도: false")
        buy, _ = self.evaluator.evaluate(rule, md, {})
        assert buy is True


# ═══════════════════════════════════════
# _extract_rule_tfs 테스트
# ═══════════════════════════════════════

class TestExtractRuleTfs:
    """엔진 TF 추출 헬퍼 검증."""

    def test_no_script(self) -> None:
        from local_server.engine.engine import _extract_rule_tfs
        assert _extract_rule_tfs({}) == []

    def test_no_minute_tf(self) -> None:
        from local_server.engine.engine import _extract_rule_tfs
        rule = {"script": "if RSI(14) > 50: buy"}
        assert _extract_rule_tfs(rule) == []

    def test_single_tf(self) -> None:
        from local_server.engine.engine import _extract_rule_tfs
        rule = {"script": 'if RSI(14, "5m") > 50: buy'}
        assert _extract_rule_tfs(rule) == ["5m"]

    def test_multiple_tfs(self) -> None:
        from local_server.engine.engine import _extract_rule_tfs
        rule = {"script": 'if RSI(14, "5m") > 50 and MA(20, "1m") > 100: buy'}
        result = _extract_rule_tfs(rule)
        assert "5m" in result
        assert "1m" in result

    def test_deduplicates_tfs(self) -> None:
        from local_server.engine.engine import _extract_rule_tfs
        rule = {"script": 'if RSI(14, "5m") > 50 and MA(20, "5m") > 100: buy'}
        assert _extract_rule_tfs(rule) == ["5m"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
