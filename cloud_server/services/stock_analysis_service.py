"""
종목별 AI 분석 서비스

매일 07:00 KST APScheduler가 watchlist+활성규칙 종목 일괄 분석.
API 요청 시 오늘 날짜에 한해 온디맨드 생성 가능.
캐시(Redis) → DB → Claude API 순서.
"""
import json
import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from cloud_server.core.config import settings
from cloud_server.core.database import get_db_session
from cloud_server.core.redis import cache_get, cache_set
from cloud_server.models.stock_briefing import StockBriefing
from cloud_server.services.context_service import ContextService

logger = logging.getLogger(__name__)

_VALID_SENTIMENTS = {"bearish", "slightly_bearish", "neutral", "slightly_bullish", "bullish"}


class StockAnalysisService:
    """종목별 AI 분석 생성/조회/캐싱"""

    def get_analysis(self, symbol: str, target_date: date, db: Session) -> dict:
        """API 핸들러 진입점.
        오늘: 캐시 → DB → 온디맨드 생성
        과거: DB → 없으면 stub (온디맨드 생성 없음)
        """
        key = f"stock_analysis:{symbol}:{target_date.isoformat()}"
        is_today = (target_date == date.today())

        # 1. Redis 캐시 (오늘만)
        if is_today:
            cached = cache_get(key)
            if cached:
                return {**cached, "source": "cache"}

        # 2. DB 조회
        row = db.query(StockBriefing).filter_by(symbol=symbol, date=target_date).first()
        if row:
            result = self._row_to_dict(row)
            if is_today:
                cache_set(key, result, ttl=86400)
            return result

        # 3. 온디맨드 생성 (오늘만)
        if is_today:
            return self._generate(symbol, target_date, db)

        # 과거 날짜 미존재 → stub
        return self._to_stub(symbol, target_date)

    def generate_all_today(self) -> None:
        """스케줄러 진입점 (07:00 KST 평일). 동기 함수 — 호출 측에서 asyncio.to_thread 사용."""
        db = get_db_session()
        try:
            today = date.today()
            symbols = self._get_target_symbols(db)
            if not symbols:
                logger.info("종목별 분석 대상 없음, 스킵")
                return
            logger.info("종목별 분석 시작: %d종목", len(symbols))
            for symbol in symbols:
                key = f"stock_analysis:{symbol}:{today.isoformat()}"
                if cache_get(key):
                    continue
                existing = db.query(StockBriefing).filter_by(symbol=symbol, date=today).first()
                if existing:
                    continue
                try:
                    self._generate(symbol, today, db)
                except Exception as e:
                    logger.error("종목 분석 실패 %s: %s", symbol, e)
            logger.info("종목별 분석 완료")
        finally:
            db.close()

    def _get_target_symbols(self, db: Session) -> list[str]:
        """watchlist 합집합 + is_active=True 규칙 종목 합집합. 최대 AI_STOCK_LIMIT."""
        from cloud_server.models.market import Watchlist
        from cloud_server.models.rule import TradingRule
        watchlist_syms = {row.symbol for row in db.query(Watchlist.symbol).distinct()}
        rule_syms = {
            row.symbol for row in
            db.query(TradingRule.symbol).filter(TradingRule.is_active == True).distinct()  # noqa: E712
        }
        symbols = sorted(watchlist_syms | rule_syms)
        limit = settings.AI_STOCK_LIMIT
        if len(symbols) > limit:
            logger.warning("분석 대상 %d종목 > 상한 %d, 상위 %d개만 처리", len(symbols), limit, limit)
            symbols = symbols[:limit]
        return symbols

    def _generate(self, symbol: str, target_date: date, db: Session) -> dict:
        """단일 종목 분석 생성 → 캐시 + DB 저장."""
        from cloud_server.models.market import StockMaster
        master = db.query(StockMaster).filter_by(symbol=symbol).first()
        name = master.name if master else None
        ctx = ContextService(db).get_symbol_context(symbol)
        result = self._call_claude_or_stub(symbol, name, ctx, target_date)
        if result["source"] != "stub":
            self._upsert(symbol, target_date, result, db)
        cache_set(f"stock_analysis:{symbol}:{target_date.isoformat()}", result, ttl=86400)
        return result

    def _build_prompt(self, symbol: str, name: str | None, ctx: dict) -> tuple[str, str]:
        """시스템/유저 프롬프트 생성."""
        system = (
            "당신은 주식 데이터 분석가입니다. "
            "제공된 기술적 지표를 바탕으로 종목 상태를 객관적으로 요약하세요. "
            "투자 조언이나 매수/매도 추천은 절대 하지 마세요.\n\n"
            "[출력 형식]\n"
            "반드시 아래 JSON만 응답하세요 (다른 텍스트 없이):\n"
            '{"summary": "2~4문장 분석 요약 (200자 이내, 한국어)", '
            '"sentiment": "bearish|slightly_bearish|neutral|slightly_bullish|bullish"}\n\n'
            "[규칙]\n"
            "- 언어: 한국어\n"
            "- 길이: 2~4문장, 200자 이내\n"
            "- 톤: 객관적·중립적\n"
            "- 매수/매도 조언 절대 금지\n"
            "- sentiment는 5단계 중 하나만 선택"
        )
        label = f"{name} ({symbol})" if name else symbol

        def v(val) -> str:
            return str(round(float(val), 2)) if val is not None else "데이터 없음"

        user = "\n".join([
            f"종목: {label}",
            f"현재가: {v(ctx.get('current_price'))}",
            f"RSI(14): {v(ctx.get('rsi_14'))}",
            f"MACD: {v(ctx.get('macd'))} / Signal: {v(ctx.get('macd_signal'))}",
            f"볼린저 상단: {v(ctx.get('bollinger_upper'))} / 하단: {v(ctx.get('bollinger_lower'))}",
            f"변동성: {v(ctx.get('volatility'))}",
        ])
        return system, user

    def _call_claude_or_stub(self, symbol: str, name: str | None, ctx: dict, target_date: date) -> dict:
        """Claude 호출. API 키 없거나 실패 시 stub 반환."""
        if not settings.ANTHROPIC_API_KEY:
            return self._to_stub(symbol, target_date)

        system, user = self._build_prompt(symbol, name, ctx)
        now = datetime.now(timezone.utc)
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=30.0)
            response = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=400,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            raw = response.content[0].text
            parsed = self._parse_response(raw)
            return {
                "symbol": symbol,
                "name": name,
                "date": target_date.isoformat(),
                "summary": parsed["summary"],
                "sentiment": parsed["sentiment"],
                "source": "claude",
                "token_input": response.usage.input_tokens,
                "token_output": response.usage.output_tokens,
                "model": settings.CLAUDE_MODEL,
                "generated_at": now.isoformat(),
            }
        except Exception as e:
            logger.error("Claude 종목 분석 실패 %s: %s", symbol, e)
            return self._to_stub(symbol, target_date)

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
            logger.warning("종목 분석 응답 파싱 실패: %s / raw: %s", e, raw[:200])
            return {"summary": raw[:300], "sentiment": "neutral"}

    def _to_stub(self, symbol: str, target_date: date) -> dict:
        """API 키 없거나 실패 시 반환값. DB 저장 없음."""
        return {
            "symbol": symbol,
            "name": None,
            "date": target_date.isoformat(),
            "summary": None,
            "sentiment": "neutral",
            "source": "stub",
            "token_input": None,
            "token_output": None,
            "model": None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _upsert(self, symbol: str, target_date: date, result: dict, db: Session) -> None:
        """symbol+date 기준 upsert."""
        try:
            row = db.query(StockBriefing).filter_by(symbol=symbol, date=target_date).first()
            generated_at = datetime.fromisoformat(result["generated_at"])
            if row:
                row.summary      = result["summary"]
                row.sentiment    = result["sentiment"]
                row.source       = result["source"]
                row.token_input  = result.get("token_input")
                row.token_output = result.get("token_output")
                row.model        = result.get("model")
                row.generated_at = generated_at
            else:
                row = StockBriefing(
                    symbol=symbol,
                    date=target_date,
                    summary=result["summary"],
                    sentiment=result["sentiment"],
                    source=result["source"],
                    token_input=result.get("token_input"),
                    token_output=result.get("token_output"),
                    model=result.get("model"),
                    generated_at=generated_at,
                )
                db.add(row)
            db.commit()
        except Exception as e:
            logger.error("종목 분석 DB 저장 실패 %s: %s", symbol, e)
            db.rollback()

    def _row_to_dict(self, row: StockBriefing) -> dict:
        """DB 행 → API 응답 dict. name은 None (DB에 저장 안 함)."""
        return {
            "symbol": row.symbol,
            "name": None,
            "date": row.date.isoformat() if row.date else None,
            "summary": row.summary,
            "sentiment": row.sentiment,
            "source": row.source,
            "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        }
