"""
AI 서비스 (Claude API 연동)

종목별 AI 분석 (감성, 종합, 리스크, 기술적 분석).
키 없음/유효하지 않음/한도 초과 → 스텁(중립값) 반환.

주의: "매수/매도하세요" 등 직접 조언 → 투자자문업 규제 → 금지.
"""
import json
import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from cloud_server.core.config import settings
from cloud_server.core.redis import cache_backend, cache_get, cache_set
from cloud_server.models.ai import AIAnalysisLog
from cloud_server.services.context_service import ContextService

logger = logging.getLogger(__name__)

# 일일 호출 카운터 (모듈 레벨, 서버 재시작 시 리셋)
_daily_count: int = 0
_daily_reset_date: date | None = None

_SYSTEM_SUFFIX = (
    "\n\n[규칙]\n"
    "- 투자 조언이나 매매 추천은 절대 하지 마세요.\n"
    "- 반드시 JSON만 응답하세요: {\"score\": float, \"label\": str, \"text\": str}\n"
    "- score: -1.0(매우 부정) ~ 1.0(매우 긍정), 0.0=중립\n"
    "- label: very_negative, negative, slightly_negative, neutral, "
    "slightly_positive, positive, very_positive 중 하나\n"
    "- text: 한국어로 객관적 분석 (1~3문장)"
)

_SYSTEM_BASE = (
    "당신은 주식 데이터 분석가입니다. "
    "수치와 추세를 객관적으로 분석하세요. "
    "투자 조언이나 매매 추천은 절대 하지 마세요."
)

_TYPE_CONFIG: dict[str, dict] = {
    "sentiment": {
        "system": "주어진 기술적 지표와 현재가를 바탕으로 시장 감성 점수를 분석하세요.",
        "max_tokens": 300,
    },
    "summary": {
        "system": "주어진 기술적 지표, 현재가, 재무 데이터를 바탕으로 종합 분석 리포트를 작성하세요.",
        "max_tokens": 500,
    },
    "risk": {
        "system": "주어진 기술적 지표와 변동성 데이터를 바탕으로 리스크를 평가하세요.",
        "max_tokens": 300,
    },
    "technical": {
        "system": "주어진 기술적 지표와 최근 가격 추이를 바탕으로 기술적 분석을 수행하세요.",
        "max_tokens": 400,
    },
}


def _reset_daily_count_if_needed() -> None:
    """날짜 변경 시 일일 카운터 리셋."""
    global _daily_count, _daily_reset_date
    today = date.today()
    if _daily_reset_date != today:
        _daily_count = 0
        _daily_reset_date = today


def _increment_daily_count() -> None:
    global _daily_count
    _daily_count += 1


def get_daily_usage() -> int:
    _reset_daily_count_if_needed()
    return _daily_count


class AIService:
    """Claude API 기반 AI 분석 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def analyze(self, symbol: str, analysis_type: str, user_id: int) -> dict:
        """종목 분석 (type별 분기).

        흐름:
        1. API 키 체크 → 없으면 스텁
        2. 캐시 체크 → 히트면 반환
        3. 일일 한도 체크 → 초과면 스텁
        4. 데이터 수집 + 프롬프트 조립
        5. Claude API 호출
        6. 응답 파싱 + 캐시/DB 저장
        """
        now = datetime.now(timezone.utc)

        # 1. API 키 체크
        if not settings.ANTHROPIC_API_KEY:
            result = self._stub_result(symbol, analysis_type)
            self._save_log(symbol, analysis_type, result, user_id)
            return result

        # 2. 캐시 체크
        cache_key = f"ai:{symbol}:{analysis_type}"
        cached = cache_get(cache_key)
        if cached:
            cached["cached"] = True
            return cached

        # 3. 일일 한도 체크
        _reset_daily_count_if_needed()
        if _daily_count >= settings.AI_DAILY_LIMIT:
            logger.warning("AI 일일 한도 초과: %d/%d", _daily_count, settings.AI_DAILY_LIMIT)
            result = self._stub_result(symbol, analysis_type)
            self._save_log(symbol, analysis_type, result, user_id)
            return result

        # 4. 데이터 수집
        ctx = ContextService(self.db)
        indicators = ctx.get_symbol_context(symbol)

        # 5. 프롬프트 조립 + Claude 호출
        system_prompt, user_prompt = self._build_prompt(analysis_type, indicators)
        config = _TYPE_CONFIG[analysis_type]
        claude_result = self._call_claude(system_prompt, user_prompt, config["max_tokens"])

        if claude_result is None:
            # Claude 호출 실패 → 스텁
            result = self._stub_result(symbol, analysis_type)
            self._save_log(symbol, analysis_type, result, user_id)
            return result

        # 6. 응답 파싱
        parsed = self._parse_response(claude_result["text"], analysis_type)

        # 사용된 지표 목록
        indicators_used = [
            k for k, v in indicators.items()
            if k != "symbol" and v is not None
        ]

        result = {
            "symbol": symbol,
            "type": analysis_type,
            "result": parsed,
            "indicators_used": indicators_used,
            "source": "claude",
            "cached": False,
            "analyzed_at": now.isoformat(),
            "token_usage": {
                "input": claude_result["input_tokens"],
                "output": claude_result["output_tokens"],
            },
        }

        _increment_daily_count()

        # 캐시 저장
        cache_set(cache_key, result, settings.AI_CACHE_TTL)

        # DB 이력 저장
        self._save_log(symbol, analysis_type, result, user_id)

        return result

    def _build_prompt(self, analysis_type: str, indicators: dict) -> tuple[str, str]:
        """type별 시스템/유저 프롬프트 생성."""
        config = _TYPE_CONFIG[analysis_type]
        system = _SYSTEM_BASE + "\n\n" + config["system"] + _SYSTEM_SUFFIX

        # 지표 데이터를 유저 프롬프트에 포함
        data_lines = []
        for k, v in indicators.items():
            if k == "symbol":
                continue
            if v is not None:
                data_lines.append(f"- {k}: {v}")

        user = f"종목: {indicators.get('symbol', 'unknown')}\n\n"
        if data_lines:
            user += "기술적 지표:\n" + "\n".join(data_lines)
        else:
            user += "기술적 지표: 데이터 없음"

        return system, user

    def _call_claude(self, system: str, user: str, max_tokens: int) -> dict | None:
        """Claude API 호출. 실패 시 None 반환."""
        try:
            import anthropic
            client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                timeout=30.0,
            )
            response = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return {
                "text": response.content[0].text,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        except Exception as e:
            # AuthenticationError, RateLimitError, APIError 등 모두 포괄
            logger.error("Claude API 호출 실패: %s", e)
            return None

    def _parse_response(self, raw: str, analysis_type: str) -> dict:
        """Claude 응답 JSON 파싱. 파싱 실패 시 기본값."""
        try:
            text = raw.strip()
            # JSON 블록 추출 (```json ... ``` 또는 순수 JSON)
            if "{" in text:
                start = text.index("{")
                end = text.rindex("}") + 1 if "}" in text else len(text)
                text = text[start:end]
                # 잘린 JSON 복구 시도 (max_tokens로 잘린 경우)
                if not text.endswith("}"):
                    text += '"}'
            parsed = json.loads(text)
            return {
                "score": float(parsed.get("score", 0.0)),
                "label": str(parsed.get("label", "neutral")),
                "text": str(parsed.get("text", "")),
            }
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            logger.warning("Claude 응답 파싱 실패: %s / raw: %s", e, raw[:200])
            return {"score": 0.0, "label": "neutral", "text": raw[:500]}

    def _stub_result(self, symbol: str, analysis_type: str) -> dict:
        """스텁 응답 생성 (키 없음/한도 초과/에러 시)."""
        return {
            "symbol": symbol,
            "type": analysis_type,
            "result": {"score": 0.0, "label": "neutral", "text": None},
            "indicators_used": [],
            "source": "stub",
            "cached": False,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "token_usage": None,
        }

    def _save_log(self, symbol: str, analysis_type: str, result: dict, user_id: int) -> None:
        """DB 이력 저장."""
        try:
            token_usage = result.get("token_usage") or {}
            log = AIAnalysisLog(
                symbol=symbol,
                type=analysis_type,
                source=result["source"],
                score=result["result"]["score"],
                text=result["result"].get("text"),
                token_input=token_usage.get("input", 0),
                token_output=token_usage.get("output", 0),
                model=settings.CLAUDE_MODEL if result["source"] == "claude" else "",
                user_id=user_id,
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.error("AI 이력 저장 실패: %s", e)
            self.db.rollback()

    def get_status(self) -> dict:
        """AI 모듈 상태 반환."""
        _reset_daily_count_if_needed()
        return {
            "available": bool(settings.ANTHROPIC_API_KEY),
            "model": settings.CLAUDE_MODEL,
            "daily_usage": _daily_count,
            "daily_limit": settings.AI_DAILY_LIMIT,
            "cache_ttl_seconds": settings.AI_CACHE_TTL,
            "cache_backend": cache_backend(),
        }
