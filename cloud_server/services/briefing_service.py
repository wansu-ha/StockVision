"""
시장 브리핑 서비스

매일 06:00 KST 자동 생성 (APScheduler), API 요청 시 온디맨드 생성.
캐시(Redis) → DB → Claude API 순서로 폴백.
"""
import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from cloud_server.core.config import settings
from cloud_server.core.database import get_db_session
from cloud_server.core.redis import cache_get, cache_set
from cloud_server.models.briefing import MarketBriefing
from cloud_server.services.context_service import ContextService
from cloud_server.services.yfinance_service import YFinanceService

logger = logging.getLogger(__name__)

_BRIEFING_SYMBOLS = ["^KS11", "^KQ11", "^GSPC", "^IXIC", "USDKRW=X"]

# yfinance 내부 심볼 키 (yfinance_service.py _SYMBOL_MAP 기준)
_KEY_KOSPI  = "^KS11"
_KEY_KOSDAQ = "^KQ11"
_KEY_SP500  = "^GSPC"
_KEY_NASDAQ = "^IXIC"
_KEY_USDKRW = "USDKRW"   # USDKRW=X → USDKRW 매핑됨

_VALID_SENTIMENTS = {"bearish", "slightly_bearish", "neutral", "slightly_bullish", "bullish"}


class BriefingService:
    """시장 브리핑 생성/조회/캐싱"""

    def get_briefing(self, target_date: date, db: Session) -> dict:
        """API 핸들러 진입점. 캐시 → DB → 즉시 생성 순서."""
        key = f"market_briefing:{target_date.isoformat()}"

        # 1. Redis 캐시
        cached = cache_get(key)
        if cached:
            return {**cached, "source": "cache"}

        # 2. DB 조회
        row = db.query(MarketBriefing).filter_by(date=target_date).first()
        if row:
            result = self._row_to_dict(row)
            cache_set(key, result, ttl=86400)
            return result

        # 3. 생성 (캐시 미스 + DB 미존재)
        return self._generate(target_date, db)

    def generate_today(self) -> None:
        """스케줄러 진입점. DB 세션 내부 생성."""
        db = get_db_session()
        try:
            today = date.today()
            existing = db.query(MarketBriefing).filter_by(date=today).first()
            if existing:
                return   # 이미 있으면 skip
            self._generate(today, db)
        finally:
            db.close()

    def _generate(self, target_date: date, db: Session) -> dict:
        """실제 생성 로직. 실패 시 스텁 반환."""
        indices = self._fetch_indices(target_date)
        context = self._fetch_context(db)
        result = self._call_claude_or_stub(indices, context, target_date)
        self._upsert(target_date, result, db)
        cache_set(f"market_briefing:{target_date.isoformat()}", result, ttl=86400)
        return result

    def _fetch_indices(self, target_date: date) -> dict:
        """YFinanceService로 전날(target_date - 1일) 지수/환율 수집. 실패 시 None 필드."""
        data_date = target_date - timedelta(days=1)
        try:
            yf = YFinanceService()
            # 주말/공휴일 여유: 1주일 전부터 수집
            start = data_date - timedelta(days=7)
            raw = yf.fetch_daily(_BRIEFING_SYMBOLS, start, data_date)

            def last_bar(key: str) -> dict | None:
                bars = raw.get(key)
                return bars[-1] if bars else None

            kospi  = last_bar(_KEY_KOSPI)
            kosdaq = last_bar(_KEY_KOSDAQ)
            sp500  = last_bar(_KEY_SP500)
            nasdaq = last_bar(_KEY_NASDAQ)
            usdkrw = last_bar(_KEY_USDKRW)

            return {
                "kospi":   {"close": kospi["close"],  "change_pct": kospi["change_pct"]}  if kospi  else None,
                "kosdaq":  {"close": kosdaq["close"], "change_pct": kosdaq["change_pct"]} if kosdaq else None,
                "sp500":   {"close": sp500["close"],  "change_pct": sp500["change_pct"]}  if sp500  else None,
                "nasdaq":  {"close": nasdaq["close"], "change_pct": nasdaq["change_pct"]} if nasdaq else None,
                "usd_krw": usdkrw["close"] if usdkrw else None,
            }
        except Exception as e:
            logger.error("지수 데이터 수집 실패: %s", e)
            return {"kospi": None, "kosdaq": None, "sp500": None, "nasdaq": None, "usd_krw": None}

    def _fetch_context(self, db: Session) -> dict:
        """ContextService로 시장 컨텍스트 조회 (KOSPI RSI, 추세 등)."""
        try:
            ctx = ContextService(db)
            return ctx.get_current_context()
        except Exception as e:
            logger.warning("시장 컨텍스트 조회 실패: %s", e)
            return {}

    def _build_prompt(self, indices: dict, context: dict) -> tuple[str, str]:
        """시스템/유저 프롬프트 생성."""
        system = (
            "당신은 주식 시장 분석가입니다. "
            "제공된 시장 데이터를 바탕으로 오늘 한국 주식 시장 전망을 요약하세요. "
            "투자 조언이나 매수/매도 추천은 절대 하지 마세요.\n\n"
            "[출력 형식]\n"
            "반드시 아래 JSON만 응답하세요 (다른 텍스트 없이):\n"
            '{"summary": "2~4문장 시황 요약 (200자 이내, 한국어)", '
            '"sentiment": "bearish|slightly_bearish|neutral|slightly_bullish|bullish"}\n\n'
            "[규칙]\n"
            "- 언어: 한국어\n"
            "- 길이: 2~4문장, 200자 이내\n"
            "- 톤: 객관적·중립적\n"
            "- 매수/매도 조언 절대 금지\n"
            "- sentiment는 5단계 중 하나만 선택"
        )

        def fmt_idx(d: dict | None, name: str) -> str:
            if not d:
                return f"{name}: 데이터 없음"
            chg = f"{d['change_pct']:+.2f}%" if d.get("change_pct") is not None else "등락 없음"
            return f"{name}: {d['close']} ({chg})"

        market = context.get("market", {})
        lines = [
            "=== 전날 시장 데이터 ===",
            fmt_idx(indices.get("kospi"),  "KOSPI"),
            fmt_idx(indices.get("kosdaq"), "KOSDAQ"),
            f"USD/KRW: {indices.get('usd_krw') or '데이터 없음'}",
            fmt_idx(indices.get("sp500"),  "S&P 500"),
            fmt_idx(indices.get("nasdaq"), "NASDAQ"),
            "",
            "=== 기술적 상태 ===",
            f"KOSPI RSI: {market.get('kospi_rsi') or '데이터 없음'}",
            f"KOSDAQ RSI: {market.get('kosdaq_rsi') or '데이터 없음'}",
            f"추세: {market.get('market_trend') or '데이터 없음'}",
            f"변동성: {market.get('volatility') or '데이터 없음'}",
        ]
        return system, "\n".join(lines)

    def _call_claude_or_stub(self, indices: dict, context: dict, target_date: date) -> dict:
        """Claude API 호출. 실패 또는 키 없으면 스텁 반환."""
        if not settings.ANTHROPIC_API_KEY:
            return self._to_stub(indices, target_date)

        system, user = self._build_prompt(indices, context)
        now = datetime.now(timezone.utc)
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=30.0)
            response = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=600,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            raw = response.content[0].text
            parsed = self._parse_response(raw)
            return {
                "date": target_date.isoformat(),
                "summary": parsed["summary"],
                "sentiment": parsed["sentiment"],
                "indices": indices,
                "source": "claude",
                "token_input": response.usage.input_tokens,
                "token_output": response.usage.output_tokens,
                "model": settings.CLAUDE_MODEL,
                "generated_at": now.isoformat(),
            }
        except Exception as e:
            logger.error("Claude 브리핑 생성 실패: %s", e)
            return self._to_stub(indices, target_date)

    def _parse_response(self, raw: str) -> dict:
        """Claude JSON 응답 파싱. 실패 시 기본값."""
        try:
            text = raw.strip()
            if "{" in text:
                start = text.index("{")
                end = text.rindex("}") + 1
                text = text[start:end]
            parsed = json.loads(text)
            sentiment = parsed.get("sentiment", "neutral")
            if sentiment not in _VALID_SENTIMENTS:
                sentiment = "neutral"
            return {
                "summary": str(parsed.get("summary", "")),
                "sentiment": sentiment,
            }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("브리핑 응답 파싱 실패: %s / raw: %s", e, raw[:200])
            return {"summary": raw[:300], "sentiment": "neutral"}

    def _to_stub(self, indices: dict, target_date: date) -> dict:
        """API 키 없거나 실패 시 반환하는 기본값."""
        return {
            "date": target_date.isoformat(),
            "summary": "시장 브리핑을 불러오지 못했습니다.",
            "sentiment": "neutral",
            "indices": indices,
            "source": "stub",
            "token_input": None,
            "token_output": None,
            "model": None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _upsert(self, target_date: date, result: dict, db: Session) -> None:
        """DB upsert (date 기준)."""
        try:
            row = db.query(MarketBriefing).filter_by(date=target_date).first()
            indices_json = json.dumps(result.get("indices", {}), ensure_ascii=False)
            generated_at = datetime.fromisoformat(result["generated_at"])
            if row:
                row.summary      = result["summary"]
                row.sentiment    = result["sentiment"]
                row.indices_json = indices_json
                row.source       = result["source"]
                row.token_input  = result.get("token_input")
                row.token_output = result.get("token_output")
                row.model        = result.get("model")
                row.generated_at = generated_at
            else:
                row = MarketBriefing(
                    date=target_date,
                    summary=result["summary"],
                    sentiment=result["sentiment"],
                    indices_json=indices_json,
                    source=result["source"],
                    token_input=result.get("token_input"),
                    token_output=result.get("token_output"),
                    model=result.get("model"),
                    generated_at=generated_at,
                )
                db.add(row)
            db.commit()
        except Exception as e:
            logger.error("브리핑 DB 저장 실패: %s", e)
            db.rollback()

    def _row_to_dict(self, row: MarketBriefing) -> dict:
        """DB 행 → dict 변환."""
        try:
            indices = json.loads(row.indices_json)
        except (json.JSONDecodeError, TypeError):
            indices = {}
        return {
            "date":         row.date.isoformat() if row.date else None,
            "summary":      row.summary,
            "sentiment":    row.sentiment,
            "indices":      indices,
            "source":       row.source,
            "token_input":  row.token_input,
            "token_output": row.token_output,
            "model":        row.model,
            "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        }
