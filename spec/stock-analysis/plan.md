> 작성일: 2026-03-12 | 상태: 초안 | Phase D (D3)

# D3 종목별 분석 plan

## 1. 아키텍처

### 컴포넌트 관계

```
[APScheduler 07:00 KST]
  → StockAnalysisService.generate_all_today()
      → DB: Watchlist + TradingRule(is_active=True) 합집합 → 최대 50종목
      → 종목별: cache_get → 히트면 skip
      → 미스: _generate(symbol, today, db)
          → ContextService.get_symbol_context() → 지표
          → StockMaster.name 조회
          → Claude API 호출
          → cache_set + DB upsert

[GET /api/v1/ai/stock-analysis/{symbol}]
  today:  cache_get → DB row → _generate (온디맨드)
  past:   DB row → 없으면 stub (온디맨드 생성 없음)
  → 응답: symbol, name, date, summary, sentiment, source, generated_at

[DetailView]
  useQuery(cloudAI.getStockAnalysis(symbol))
  → StockAnalysisCard (로딩/스텁/정상 3상태)
```

### 캐시 키
```
stock_analysis:{symbol}:{YYYY-MM-DD}
TTL: 24시간 (86400초)
```

---

## 2. 수정 파일 목록

| 파일 | 변경 | 비고 |
|------|------|------|
| `cloud_server/models/stock_briefing.py` | 신규 — StockBriefing 모델 | |
| `cloud_server/core/init_db.py` | StockBriefing import 추가 | 1줄 |
| `cloud_server/core/config.py` | AI_STOCK_LIMIT 추가 | 1줄 |
| `cloud_server/services/stock_analysis_service.py` | 신규 — StockAnalysisService | briefing_service 패턴 |
| `cloud_server/api/ai.py` | /stock-analysis/{symbol} 엔드포인트 추가 | |
| `cloud_server/collector/scheduler.py` | 07:00 KST job + _run_stock_analysis | |
| `frontend/src/services/cloudClient.ts` | StockAnalysis 타입 + getStockAnalysis() | |
| `frontend/src/components/StockAnalysisCard.tsx` | 신규 — AI 분석 카드 컴포넌트 | |
| `frontend/src/components/main/DetailView.tsx` | StockAnalysisCard 삽입 (컨텍스트 섹션 아래) | |

---

## 3. 구현 순서

### Step 1: DB 모델 + init_db

**`cloud_server/models/stock_briefing.py`** (신규):
```python
from datetime import datetime, timezone
from sqlalchemy import Column, Date, DateTime, Integer, String, Text, UniqueConstraint
from cloud_server.core.database import Base

class StockBriefing(Base):
    __tablename__ = "stock_briefings"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    symbol       = Column(String(10), nullable=False, index=True)
    date         = Column(Date, nullable=False, index=True)
    summary      = Column(Text, nullable=False)
    sentiment    = Column(String(30), nullable=False)
    source       = Column(String(10), nullable=False)   # "claude" | "stub"
    token_input  = Column(Integer)
    token_output = Column(Integer)
    model        = Column(String(100))
    generated_at = Column(DateTime(timezone=True), nullable=False,
                          default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_stock_briefing_symbol_date"),
    )
```

**`cloud_server/core/init_db.py`** 수정 (1줄 추가):
```python
from cloud_server.models.stock_briefing import StockBriefing  # noqa: F401
```

> verify: `python -c "from cloud_server.core.init_db import init_db; init_db()"` — stock_briefings 테이블 생성 확인

---

### Step 2: Config 추가

**`cloud_server/core/config.py`** — AI 섹션에 1줄 추가:
```python
AI_STOCK_LIMIT: int = int(os.environ.get("AI_STOCK_LIMIT", "50"))
```

> verify: `python -c "from cloud_server.core.config import settings; print(settings.AI_STOCK_LIMIT)"` → 50

---

### Step 3: StockAnalysisService

**`cloud_server/services/stock_analysis_service.py`** (신규):

briefing_service.py 패턴 동일하게 적용. 핵심 로직:

```python
class StockAnalysisService:

    def get_analysis(self, symbol: str, target_date: date, db: Session) -> dict:
        """API 핸들러 진입점.
        오늘 날짜: 캐시 → DB → 온디맨드 생성
        과거 날짜: DB → 없으면 stub
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
        """스케줄러 진입점 (07:00 KST)."""
        db = get_db_session()
        try:
            today = date.today()
            symbols = self._get_target_symbols(db)
            if not symbols:
                logger.info("분석 대상 종목 없음, 스킵")
                return
            for symbol in symbols:
                key = f"stock_analysis:{symbol}:{today.isoformat()}"
                if cache_get(key):
                    continue   # 이미 캐시됨
                existing = db.query(StockBriefing).filter_by(symbol=symbol, date=today).first()
                if existing:
                    continue
                try:
                    self._generate(symbol, today, db)
                except Exception as e:
                    logger.error("종목 분석 실패 %s: %s", symbol, e)
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
        """단일 종목 분석 생성."""
        # StockMaster.name 조회
        from cloud_server.models.market import StockMaster
        master = db.query(StockMaster).filter_by(symbol=symbol).first()
        name = master.name if master else None
        # 지표 수집
        ctx = ContextService(db).get_symbol_context(symbol)
        result = self._call_claude_or_stub(symbol, name, ctx, target_date)
        self._upsert(symbol, target_date, result, db)
        cache_set(f"stock_analysis:{symbol}:{target_date.isoformat()}", result, ttl=86400)
        return result

    def _build_prompt(self, symbol: str, name: str | None, ctx: dict) -> tuple[str, str]:
        system = (
            "당신은 주식 데이터 분석가입니다. "
            "제공된 기술적 지표를 바탕으로 종목 상태를 객관적으로 요약하세요. "
            "투자 조언이나 매수/매도 추천은 절대 하지 마세요.\n\n"
            "[출력 형식]\n"
            "반드시 아래 JSON만 응답하세요 (다른 텍스트 없이):\n"
            '{"summary": "2~4문장 분석 요약 (200자 이내, 한국어)", '
            '"sentiment": "bearish|slightly_bearish|neutral|slightly_bullish|bullish"}'
        )
        label = f"{name} ({symbol})" if name else symbol
        def v(val) -> str:
            return str(round(val, 2)) if val is not None else "데이터 없음"
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
        """briefing_service._parse_response와 동일 패턴."""
        # JSON 추출 → sentiment 검증 → 기본값 fallback
        ...  # briefing_service 참조

    def _to_stub(self, symbol: str, target_date: date) -> dict:
        """API 키 없거나 실패 시 반환값. DB 저장 안 함."""
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
        """symbol+date 기준 upsert. stub은 호출하지 않음."""
        # briefing_service._upsert와 동일 패턴
        # result["source"] == "stub"이면 저장 생략
        ...

    def _row_to_dict(self, row: StockBriefing) -> dict:
        """DB 행 → API 응답 dict. name은 None (StockMaster JOIN 없이 저장)."""
        return {
            "symbol": row.symbol,
            "name": None,           # StockMaster 조회 없이 저장 — 조회 시점에 채워도 됨
            "date": row.date.isoformat() if row.date else None,
            "summary": row.summary,
            "sentiment": row.sentiment,
            "source": row.source,
            "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        }
```

> verify: `python -c "from cloud_server.services.stock_analysis_service import StockAnalysisService"` — import 에러 없음

---

### Step 4: API 엔드포인트

**`cloud_server/api/ai.py`** 에 추가:

```python
from cloud_server.services.stock_analysis_service import StockAnalysisService

@router.get("/stock-analysis/{symbol}")
def stock_analysis(
    symbol: str,
    date_str: str | None = Query(None, alias="date", description="YYYY-MM-DD, 기본값: 오늘"),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """종목 AI 분석 조회 (오늘: 생성 포함, 과거: DB only)"""
    target = _parse_date(date_str) or date_.today()
    service = StockAnalysisService()
    result = service.get_analysis(symbol, target, db)
    return {"success": True, "data": result}
```

> verify: 서버 기동 후 `curl http://localhost:4010/api/v1/ai/stock-analysis/005930 -H "Authorization: Bearer {token}"` → 200 + JSON

---

### Step 5: 스케줄러

**`cloud_server/collector/scheduler.py`** 수정:

docstring에 `- 07:00 KST: 종목별 분석 생성` 추가.

`start()` 에 추가:
```python
# 07:00 KST 평일 — 종목별 분석 생성
self.scheduler.add_job(
    self._run_stock_analysis,
    trigger=CronTrigger(hour=7, minute=0, day_of_week="mon-fri", timezone="Asia/Seoul"),
    id="stock_analysis",
    replace_existing=True,
)
```

메서드 추가:
```python
async def _run_stock_analysis(self) -> None:
    """종목별 AI 분석 생성 (07:00 KST 평일)
    asyncio.to_thread: generate_all_today()는 동기 함수이고 50종목 × Claude 호출로 장시간 실행.
    to_thread로 백그라운드 스레드에서 순차 실행 → 이벤트 루프 블로킹 방지.
    (종목 간 병렬화 불필요 — 07:00 배치는 수 분 내 완료면 충분)
    """
    import asyncio
    try:
        from cloud_server.services.stock_analysis_service import StockAnalysisService
        await asyncio.to_thread(StockAnalysisService().generate_all_today)
        logger.info("종목별 분석 생성 완료")
    except Exception as e:
        logger.error("종목별 분석 생성 실패: %s", e)
```

> verify: 서버 로그에 "종목별 분석 생성" 스케줄 등록 확인

---

### Step 6: 프론트엔드 클라이언트

**`frontend/src/services/cloudClient.ts`** 에 추가:

```typescript
export interface StockAnalysis {
  symbol: string
  name: string | null
  date: string
  summary: string | null
  sentiment: 'bearish' | 'slightly_bearish' | 'neutral' | 'slightly_bullish' | 'bullish'
  source: 'claude' | 'cache' | 'stub'
  generated_at: string
}

// cloudAI 객체에 추가:
getStockAnalysis: (symbol: string, date?: string) =>
  client.get<{ success: boolean; data: StockAnalysis }>(
    `/api/v1/ai/stock-analysis/${symbol}`,
    date ? { params: { date } } : undefined,
  ).then((r) => r.data.data),
```

> verify: TypeScript 빌드 에러 없음

---

### Step 7: StockAnalysisCard 컴포넌트

**`frontend/src/components/StockAnalysisCard.tsx`** (신규):

BriefingCard.tsx와 동일한 패턴:
- `useQuery({ queryKey: ['stock-analysis', symbol], queryFn: () => cloudAI.getStockAnalysis(symbol), staleTime: 30 * 60 * 1000, retry: 1 })`
- 로딩: 스켈레톤 (2줄)
- 스텁/null summary: "분석을 불러오지 못했습니다" 안내 텍스트
- 정상: summary 텍스트 + sentiment 배지 + generated_at

SENTIMENT_COLOR 맵 (BriefingCard와 동일):
```typescript
const SENTIMENT_COLOR = {
  bearish: 'bg-red-900/40 text-red-400',
  slightly_bearish: 'bg-orange-900/40 text-orange-400',
  neutral: 'bg-gray-800 text-gray-400',
  slightly_bullish: 'bg-emerald-900/40 text-emerald-400',
  bullish: 'bg-green-900/40 text-green-400',
}
```

Props: `{ symbol: string }`

> verify: `npm run build` 에러 없음

---

### Step 8: DetailView 통합

**`frontend/src/components/main/DetailView.tsx`** 수정:

```tsx
import StockAnalysisCard from '../StockAnalysisCard'

// 시장 컨텍스트 섹션 아래에 삽입:
{/* AI 분석 */}
<section className="mb-6">
  <h3 className="text-sm font-medium text-gray-400 mb-3">AI 분석</h3>
  <StockAnalysisCard symbol={stock.symbol} />
</section>
```

> verify: 브라우저에서 DetailView 열어 AI 분석 섹션 렌더링 확인. 스텁 텍스트 또는 분석 텍스트 표시.

---

## 4. 검증 방법 요약

| 단계 | 검증 |
|------|------|
| Step 1 | `init_db()` 실행 → stock_briefings 테이블 존재 |
| Step 2 | `settings.AI_STOCK_LIMIT` == 50 |
| Step 3 | `StockAnalysisService()` import 성공 |
| Step 4 | curl 또는 Swagger로 /stock-analysis/005930 → 200 |
| Step 5 | 서버 로그에 stock_analysis job 등록 확인 |
| Step 6 | `npm run build` 에러 없음 |
| Step 7 | `npm run build` 에러 없음 |
| Step 8 | 브라우저 DetailView → "AI 분석" 섹션 렌더링 |

---

## 5. 주의사항

- `_run_stock_analysis`는 `async def`지만 `StockAnalysisService.generate_all_today()`는 동기 함수 — 현재 패턴 유지 (briefing과 동일)
- `_get_target_symbols`에서 `== True` 비교 → SQLAlchemy lint 경고 발생 가능. `# noqa: E712` 주석 필수
- 캐시 키 일관성: `stock_analysis:{symbol}:{YYYY-MM-DD}` (briefing과 네임스페이스 분리)
- `_to_stub`의 `source`는 `"stub"` (DB 저장 없음 — stub은 저장 안 함)
