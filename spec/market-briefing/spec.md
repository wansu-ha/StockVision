> 작성일: 2026-03-12 | 상태: 구현 완료 | Phase D (D2)

# D2 시장 브리핑 spec

## 1. 목표

매일 장 시작 전, 오늘 한국 시장을 어떻게 봐야 하는지 한 문단으로 정리해서 보여준다.

사용자가 앱을 열었을 때 "오늘 시장 분위기는 이렇다"를 즉시 파악할 수 있게 한다.
개인화 없음 — 모든 사용자에게 동일한 시황 브리핑.

## 2. 요구사항

### 2.1 기능적 요구사항

**생성**
- 매일 **06:00 KST** (장 시작 3시간 전, 미국 시장 마감 후) APScheduler가 자동 생성
- 입력 데이터:
  - 전날 KOSPI / KOSDAQ 종가, 등락률
  - 전날 USD/KRW 환율 (yfinance: `KRW=X`)
  - 전날 S&P 500, NASDAQ 종가 (yfinance: `^GSPC`, `^IXIC`) — 글로벌 시장 컨텍스트
  - `ContextService.get_current_context()` → KOSPI RSI, 변동성, 추세
- 출력: 아래 §5의 JSON 구조
- 실패 시: 스텁 반환 (생성 실패로 인해 앱이 에러 상태가 되면 안 됨)

**캐싱**
- Redis 키: `market_briefing:{YYYY-MM-DD}`
- TTL: 다음날 00:00 KST까지 (or 24시간)
- 캐시 히트 시 Claude 호출 없이 즉시 반환

**저장**
- 생성된 브리핑을 DB에 저장 (`market_briefings` 테이블 — 신규)
- 1일 1행, `date` 컬럼으로 중복 방지 (upsert)

**API**
- `GET /api/v1/ai/briefing` — 오늘 브리핑 반환 (캐시 우선, 없으면 생성)
- `GET /api/v1/ai/briefing?date=2026-03-11` — 과거 브리핑 조회 (DB에서 읽기만)
- 인증: JWT 필요

**프론트엔드**
- 메인 대시보드 OpsPanel 아래 또는 포트폴리오 카드 상단에 브리핑 카드 표시
- 로딩 중: 스켈레톤
- 생성 실패 / 스텁: "브리핑을 불러오지 못했습니다" 표시 (에러 아님, 안내)
- 브리핑 텍스트 + 주요 지수 숫자 병렬 표시

### 2.2 비기능적 요구사항

- Claude 호출 1회/일, 운영자 API 키 사용
- 응답 지연 허용: API 첫 호출 시 최대 10초 (캐시 미스 → Claude 생성)
- 캐시 히트 시 200ms 이내
- 스케줄 실패 시 조용히 로그만 남김 (앱 장애 없음)

## 3. 수용 기준

- [x] 매일 06:00 KST 자동 생성 (스케줄러 job 추가 확인)
- [x] `GET /api/v1/ai/briefing` 응답 200, JSON 구조 정확 _(서버 재시작 필요)_
- [x] Redis 캐시 적중 시 동일 날짜 두 번째 호출이 Claude 미호출 (source: "cache")
- [x] 과거 날짜 조회 시 DB에서 반환 (Claude 미호출)
- [x] Claude API 키 없을 때 스텁 반환 — 앱 에러 없음
- [x] 프론트엔드 브리핑 카드 렌더링 (텍스트 + 지수 3종)
- [x] 로딩/에러/정상 상태 모두 처리

## 4. 범위

### 포함
- 시장 전체 브리핑 (KOSPI/KOSDAQ/환율/글로벌)
- 클라우드 서버 자동 생성 + 캐싱
- 프론트엔드 카드 컴포넌트 (대시보드 표시)

### 미포함
- 개별 종목 분석 (→ D3)
- 텔레그램/이메일 발송 (→ D4)
- 사용자별 관심 섹터 브리핑 (→ Phase E)
- 브리핑 기반 자동매매 신호
- 뉴스 API 연동 (외부 뉴스 소스 — 범위 확장 시 별도 spec)

## 5. API / DB 변경

### 5.1 신규 엔드포인트

```
GET /api/v1/ai/briefing
  query: date (optional, YYYY-MM-DD, default: today)
  auth: JWT

응답:
{
  "success": true,
  "data": {
    "date": "2026-03-12",
    "summary": "미국 증시가 소폭 하락 마감한 가운데...",  // 2~4문장
    "indices": {
      "kospi":  { "close": 2580.5, "change_pct": -0.3 },
      "kosdaq": { "close":  870.2, "change_pct":  0.8 },
      "usd_krw": 1320.5,
      "sp500":  { "close": 5120.0, "change_pct": -0.5 },
      "nasdaq": { "close": 18200.0, "change_pct": -0.4 }
    },
    "sentiment": "neutral",   // bearish | slightly_bearish | neutral | slightly_bullish | bullish
    "source": "claude",       // "claude" | "cache" | "stub"  ← API 레이어 전용
    // DB source("claude"|"stub")와 별개 — 캐시 히트 시 API 레이어에서 "cache"로 덮어씀
    "generated_at": "2026-03-12T08:30:00+09:00"
  }
}
```

### 5.2 신규 DB 모델 (`cloud_server/models/briefing.py`)

```python
class MarketBriefing(Base):
    __tablename__ = "market_briefings"

    id:           int  (PK)
    date:         date (UNIQUE)          # 1일 1행
    summary:      str  (TEXT)            # 브리핑 본문
    sentiment:    str                    # bearish ~ bullish
    indices_json: str  (TEXT)            # JSON 직렬화
    source:       str                    # "claude" | "stub"
    token_input:  int | None
    token_output: int | None
    model:        str | None
    generated_at: datetime
```

### 5.3 신규 서비스 (`cloud_server/services/briefing_service.py`)

```python
class BriefingService:
    generate_today() -> MarketBriefingDTO   # 스케줄러 호출
    get_briefing(date) -> MarketBriefingDTO # API 핸들러 호출
    _build_prompt(indices, context) -> str  # 프롬프트 조립
    _call_claude(prompt) -> dict            # AI 호출
    _to_stub() -> MarketBriefingDTO         # 실패 시 폴백
```

### 5.4 스케줄러 추가 (`cloud_server/collector/scheduler.py`)

```python
# 06:00 KST (평일) — 시장 브리핑 생성
scheduler.add_job(
    briefing_service.generate_today,
    CronTrigger(hour=6, minute=0, day_of_week="mon-fri", timezone="Asia/Seoul"),
    id="market_briefing",
    replace_existing=True,
)
```

### 5.5 프론트엔드 (`frontend/src/services/cloudClient.ts` 추가)

```typescript
cloudAI.getBriefing(date?: string) → GET /api/v1/ai/briefing?date=...
```

## 6. 프롬프트 설계 의도

### 입력 재료 (프롬프트에 주입)

```
전날 지수: KOSPI {close} ({change_pct}%), KOSDAQ {close} ({change_pct}%)
환율: USD/KRW {usd_krw}
글로벌: S&P500 {change_pct}%, NASDAQ {change_pct}%
기술적 상태: KOSPI RSI {rsi}, 추세 {trend}, 변동성 {volatility}
```

### 출력 요구사항 (프롬프트에 명시)

- **언어**: 한국어
- **길이**: 2~4문장, 200자 이내
- **톤**: 객관적·중립적 (매수/매도 조언 금지)
- **형식**: `{"summary": str, "sentiment": str}` JSON만 응답
- `sentiment` 값: `bearish | slightly_bearish | neutral | slightly_bullish | bullish`

> 실제 system/user 프롬프트 문자열은 `BriefingService._build_prompt()` 구현 시 작성.

## 7. 참고 코드

| 용도 | 경로 |
|------|------|
| AI 분석 서비스 패턴 | `cloud_server/services/ai_service.py` |
| AI 라우터 패턴 | `cloud_server/api/ai.py` |
| 시장 컨텍스트 | `cloud_server/services/context_service.py` |
| yfinance 보조 수집 | `cloud_server/services/yfinance_service.py` |
| APScheduler | `cloud_server/collector/scheduler.py` |
| Redis 캐시 유틸 | `cloud_server/core/redis.py` |
| AI 분석 DB 모델 | `cloud_server/models/ai.py` |
| 프론트 클라이언트 | `frontend/src/services/cloudClient.ts` |
