"""
AI 서비스 (Claude API 연동)

v1: stub (Claude 호출 없음, 중립값 반환)
v2: Claude API 호출 추가 (감성 점수, 뉴스 요약)

주의: LLM은 "데이터 제공" 역할만 (감성 점수, 요약).
"매수하세요" 같은 직접 조언 → 투자자문업 → 금지.
"""
import logging
from datetime import datetime, timezone

from cloud_server.core.config import settings

logger = logging.getLogger(__name__)

# 메모리 캐시 (v1)
_sentiment_cache: dict[str, dict] = {}


class AIService:
    """Claude API 기반 AI 분석 서비스"""

    async def get_sentiment(self, symbol: str, ttl_seconds: int = 3600) -> dict:
        """
        감성 분석 (v1에서는 stub, v2에서 Claude API 호출).

        Returns:
            {"symbol": str, "score": float (-1~1), "source": str, "cached": bool}
        """
        # v1: 캐시에서 확인
        cached = _sentiment_cache.get(symbol)
        if cached:
            cache_age = (
                datetime.now(tz=timezone.utc).timestamp()
                - cached.get("cached_at", 0)
            )
            if cache_age < ttl_seconds:
                return {**cached, "cached": True}

        # v1: stub 반환 (v2에서 Claude API 호출로 교체)
        """
        v2 구현 예시:
        if settings.ANTHROPIC_API_KEY:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            prompt = (
                f"종목 코드 {symbol}에 대해 최근 시장 감성을 -1(매우 부정)에서 1(매우 긍정) 사이의 "
                f"숫자로만 응답하세요. 투자 조언은 제공하지 마세요."
            )
            response = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}],
            )
            score = float(response.content[0].text.strip())
            ...
        """

        result = {
            "symbol": symbol,
            "score": 0.0,  # -1 ~ 1, 0 = 중립
            "source": "stub_v1",
            "cached": False,
            "cached_at": datetime.now(tz=timezone.utc).timestamp(),
        }

        _sentiment_cache[symbol] = result
        return result
