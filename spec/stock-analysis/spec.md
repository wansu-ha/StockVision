> 작성일: 2026-03-12 | 상태: 초안 | Phase D (D3)

# D3 종목별 분석 spec

## 1. 목표

사용자가 종목 상세 화면을 열었을 때, 해당 종목의 오늘 AI 분석을 즉시 볼 수 있게 한다.

"이 종목 지금 어때?" — RSI, MACD 등 기술적 지표를 바탕으로 2~4문장 요약과 sentiment를 표시한다.
개인화 없음 — 동일 종목은 모든 사용자에게 같은 분석. 운영자 API 키 + 서버 캐싱.

## 2. 요구사항

### 2.1 기능적 요구사항

**생성**
- 매일 **07:00 KST** (장 시작 2시간 전) APScheduler가 전날 watchlist 합집합 종목 일괄 분석
- 분석 대상: 전체 사용자 watchlist 합집합 + **활성 규칙(`is_active=True`) 종목** 합집합 (중복 제거)
- 종목 수 상한: **최대 50종목** (`AI_STOCK_LIMIT` 환경변수, 기본값 50). 초과 시 상위 50개만 처리하고 로그 경고
- 입력 데이터:
  - `ContextService.get_symbol_context(symbol)` → RSI, MACD, 볼린저, 변동성
  - 전날 종가/등락률 (yfinance 또는 DB DailyBar)
- 출력: §5.1의 JSON 구조
- 실패 시: 스텁 반환 (생성 실패로 앱 에러 없음)

**캐싱**
- Redis 키: `stock_analysis:{symbol}:{YYYY-MM-DD}`
- TTL: 24시간
- 캐시 히트 시 Claude 호출 없이 즉시 반환

**저장**
- DB: `stock_briefings` 테이블 (신규) — date+symbol unique
- 기존 `AIAnalysisLog`는 온디맨드 이력용으로 유지 (D3와 분리)

**API**
- `GET /api/v1/ai/stock-analysis/{symbol}` — 오늘 분석 반환 (캐시 우선, 없으면 온디맨드 생성)
- `GET /api/v1/ai/stock-analysis/{symbol}?date=2026-03-11` — 과거 분석 조회 (DB만, 없으면 스텁 반환 — 과거 날짜 온디맨드 생성 없음)
- 인증: JWT 필요

**프론트엔드**
- DetailView의 "시장 컨텍스트" 섹션 아래에 "AI 분석" 섹션 추가
- 로딩 중: 스켈레톤
- 스텁/에러: "분석을 불러오지 못했습니다" (에러 아님, 안내)
- 정상: summary 텍스트 + sentiment 배지 + 생성 시각

### 2.2 비기능적 요구사항

- Claude 호출: 종목 수 × 1회/일 (운영자 API 키, 캐싱으로 재호출 없음)
- 응답 지연 허용: 캐시 미스 시 최대 15초 (온디맨드 생성)
- 캐시 히트 시 200ms 이내
- 스케줄 실패 시 조용히 로그만 남김 (앱 장애 없음)
- 분석 대상 종목이 없으면 스케줄러 job 조용히 종료

## 3. 수용 기준

- [ ] 매일 07:00 KST 스케줄러 job 실행 확인
- [ ] `GET /api/v1/ai/stock-analysis/{symbol}` 응답 200, JSON 구조 정확
- [ ] Redis 캐시 적중 시 두 번째 호출이 Claude 미호출 (source: "cache")
- [ ] Claude API 키 없을 때 스텁 반환 — 앱 에러 없음
- [ ] 분석 대상 종목 없으면 스케줄러 조용히 종료
- [ ] DetailView에 AI 분석 섹션 렌더링 (텍스트 + sentiment)
- [ ] 로딩/스텁/정상 3상태 모두 처리

## 4. 범위

### 포함
- 종목별 summary 분석 1종 (sentiment + 텍스트 2~4문장)
- 서버 07:00 KST 자동 생성 (watchlist+rules 합집합)
- 캐시 + DB 저장
- DetailView AI 분석 섹션

### 미포함
- 이벤트 트리거 (급등/급락 시 즉시 재분석) — 복잡도 과다, v2 검토
- 분석 유형 복수 (`risk`, `technical` 등) — summary만 생성
- 사용자별 개인화 분석 (→ Phase E BYO LLM)
- 관리자 분석 현황 UI

## 5. API / DB 변경

### 5.1 신규 엔드포인트

```
GET /api/v1/ai/stock-analysis/{symbol}
  query: date (optional, YYYY-MM-DD, default: today)
  auth: JWT

응답:
{
  "success": true,
  "data": {
    "symbol": "005930",
    "name": "삼성전자",   // StockMaster.name JOIN, 없으면 null
    "date": "2026-03-12",
    "summary": "RSI 58로 중립권에 위치하며...",  // 2~4문장
    "sentiment": "neutral",    // bearish | slightly_bearish | neutral | slightly_bullish | bullish
    "source": "claude",        // "claude" | "cache" | "stub"
    "generated_at": "2026-03-12T07:05:00+09:00"
  }
}
```

### 5.2 신규 DB 모델 (`cloud_server/models/stock_briefing.py`)

```python
class StockBriefing(Base):
    __tablename__ = "stock_briefings"

    id:           int  (PK)
    symbol:       str  (index)
    date:         date (index)
    summary:      str  (TEXT)
    sentiment:    str              # bearish ~ bullish
    source:       str              # "claude" | "stub"
    token_input:  int | None
    token_output: int | None
    model:        str | None
    generated_at: datetime

    __table_args__: UniqueConstraint("symbol", "date")  # 1종목 1일 1행
```

### 5.3 신규 서비스 (`cloud_server/services/stock_analysis_service.py`)

```python
class StockAnalysisService:
    get_analysis(symbol, target_date, db) -> dict  # API 핸들러 (캐시→DB→생성, 오늘만. 과거=DB only)
    generate_all_today() -> None                   # 스케줄러 진입점
    _get_target_symbols(db) -> list[str]           # watchlist + is_active=True 규칙 합집합 (최대 AI_STOCK_LIMIT)
    _generate(symbol, target_date, db) -> dict     # 단일 종목 생성
    _build_prompt(symbol, name, context) -> tuple[str,str]  # name = StockMaster.name
    _call_claude_or_stub(symbol, name, context, target_date) -> dict
    _to_stub(symbol, target_date) -> dict
```

### 5.3b 설정 추가 (`cloud_server/core/config.py`)

```python
AI_STOCK_LIMIT: int = int(os.environ.get("AI_STOCK_LIMIT", "50"))
```

### 5.4 스케줄러 추가 (`cloud_server/collector/scheduler.py`)

```python
# 07:00 KST (평일) — 종목별 분석 생성
scheduler.add_job(
    self._run_stock_analysis,
    CronTrigger(hour=7, minute=0, day_of_week="mon-fri", timezone="Asia/Seoul"),
    id="stock_analysis",
    replace_existing=True,
)
```

### 5.5 프론트엔드 클라이언트 (`frontend/src/services/cloudClient.ts` 추가)

```typescript
cloudAI.getStockAnalysis(symbol: string, date?: string)
  → GET /api/v1/ai/stock-analysis/{symbol}?date=...
```

## 6. 프롬프트 설계 의도

### 입력 재료 (프롬프트에 주입)

```
종목: {name} ({symbol})
전날 종가: {close} ({change_pct}%)
RSI(14): {rsi_14}
MACD: {macd} / Signal: {macd_signal}
볼린저 상단: {bollinger_upper} / 하단: {bollinger_lower}
변동성: {volatility}
```

### 출력 요구사항 (프롬프트에 명시)

- **언어**: 한국어
- **길이**: 2~4문장, 200자 이내
- **톤**: 객관적·중립적 (매수/매도 조언 금지)
- **형식**: `{"summary": str, "sentiment": str}` JSON만 응답
- `sentiment` 값: `bearish | slightly_bearish | neutral | slightly_bullish | bullish`

> 실제 system/user 프롬프트 문자열은 `StockAnalysisService._build_prompt()` 구현 시 작성.

## 7. 참고

| 용도 | 경로 |
|------|------|
| 시장 브리핑 서비스 패턴 | `cloud_server/services/briefing_service.py` |
| 기존 AI 분석 서비스 | `cloud_server/services/ai_service.py` |
| 시장 컨텍스트 (지표 계산) | `cloud_server/services/context_service.py` |
| Watchlist 모델 | `cloud_server/models/market.py` |
| TradingRule 모델 | `cloud_server/models/rule.py` |
| Redis 캐시 유틸 | `cloud_server/core/redis.py` |
| 스케줄러 패턴 | `cloud_server/collector/scheduler.py` |
| DetailView (프론트 통합 위치) | `frontend/src/components/main/DetailView.tsx` |
| 프론트 클라이언트 | `frontend/src/services/cloudClient.ts` |
