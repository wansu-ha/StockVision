> 작성일: 2026-03-12 | 상태: 초안 | Phase D (D2)

# D2 시장 브리핑 구현 계획

## 1. 아키텍처

```
APScheduler (06:00 KST, mon-fri)
  └─ BriefingService.generate_today()
       ├─ YFinanceService.fetch_daily([^KS11, ^KQ11, ^GSPC, ^IXIC, USDKRW=X])
       ├─ ContextService.get_current_context()  ← KOSPI RSI, 추세
       ├─ _build_prompt() + _call_claude()
       ├─ DB 저장 (market_briefings, upsert by date)
       └─ Redis 캐시 (market_briefing:{date}, TTL 24h)

GET /api/v1/ai/briefing
  └─ BriefingService.get_briefing(date, db)
       ├─ Redis 히트 → { ...cached, source: "cache" }
       ├─ DB 조회   → { ...row, source: row.source }
       └─ 없으면    → generate_today() → { ..., source: "claude"|"stub" }

Frontend (MainDashboard)
  └─ useQuery → cloudAI.getBriefing()
       └─ BriefingCard 렌더링 (summary + 지수 3종 + sentiment)
```

### 핵심 설계 결정

1. **DB 세션 분리**: `generate_today()`는 스케줄러에서 DI 없이 호출 → `with get_db_session() as db:` 내부 처리
2. **API 호출 시 온디맨드 생성**: 스케줄 실패 시에도 첫 API 호출에서 즉시 생성 (최대 10초)
3. **`source` 이중 의미**: DB `source`("claude"|"stub") ≠ API 응답 `source`("claude"|"cache"|"stub") — API 레이어에서 덮어씀
4. **AIService 재사용 없음**: 종목별 분석과 시장 브리핑은 입출력 구조가 달라 `BriefingService`를 독립 클래스로 구현

## 2. 수정 파일 목록

### 신규 생성 (3개)

| 파일 | 내용 |
|------|------|
| `cloud_server/models/briefing.py` | `MarketBriefing` SQLAlchemy 모델 |
| `cloud_server/services/briefing_service.py` | `BriefingService` — 생성/조회/캐싱/스텁 |
| `frontend/src/components/BriefingCard.tsx` | 브리핑 카드 컴포넌트 |

### 수정 (5개)

| 파일 | 변경 내용 |
|------|-----------|
| `cloud_server/core/init_db.py` | `MarketBriefing` import 추가 → `create_all()` 테이블 생성 |
| `cloud_server/api/ai.py` | `GET /api/v1/ai/briefing` 엔드포인트 추가 |
| `cloud_server/collector/scheduler.py` | briefing job 추가 (06:00 KST, mon-fri) |
| `frontend/src/services/cloudClient.ts` | `cloudAI.getBriefing(date?)` 추가 |
| `frontend/src/pages/MainDashboard.tsx` | `<BriefingCard />` OpsPanel 아래 삽입 |

## 3. 구현 순서

### Step 1 — DB 모델

**`cloud_server/models/briefing.py` 생성**

```python
class MarketBriefing(Base):
    __tablename__ = "market_briefings"
    id           = Column(Integer, primary_key=True)
    date         = Column(Date, nullable=False, unique=True, index=True)
    summary      = Column(Text, nullable=False)
    sentiment    = Column(String(30), nullable=False)   # bearish~bullish
    indices_json = Column(Text, nullable=False)          # JSON 직렬화
    source       = Column(String(10), nullable=False)    # "claude" | "stub"
    token_input  = Column(Integer)
    token_output = Column(Integer)
    model        = Column(String(100))
    generated_at = Column(DateTime(timezone=True), nullable=False)
```

**`cloud_server/core/init_db.py` 수정**

```python
from cloud_server.models.briefing import MarketBriefing  # noqa: F401
```

> verify: `python -c "from cloud_server.models.briefing import MarketBriefing; print('OK')"`

---

### Step 2 — BriefingService

**`cloud_server/services/briefing_service.py` 생성**

```python
class BriefingService:

    def get_briefing(self, date: date, db: Session) -> dict:
        """API 핸들러 진입점. 캐시 → DB → 즉시 생성 순서."""
        # 1. Redis 캐시
        key = f"market_briefing:{date.isoformat()}"
        cached = cache_get(key)
        if cached:
            return {**cached, "source": "cache"}

        # 2. DB 조회
        row = db.query(MarketBriefing).filter_by(date=date).first()
        if row:
            result = self._row_to_dict(row)
            cache_set(key, result, ttl=86400)
            return result

        # 3. 생성 (캐시 미스 + DB 미존재)
        return self._generate(date, db)

    def generate_today(self) -> None:
        """스케줄러 진입점. DB 세션 내부 생성."""
        with get_db_session() as db:
            today = date.today()
            existing = db.query(MarketBriefing).filter_by(date=today).first()
            if existing:
                return   # 이미 있으면 skip
            self._generate(today, db)

    def _generate(self, target_date: date, db: Session) -> dict:
        """실제 생성 로직. 실패 시 스텁 반환."""
        indices = self._fetch_indices(target_date)
        context = self._fetch_context(db)
        result = self._call_claude_or_stub(indices, context)
        self._upsert(target_date, result, db)
        cache_set(f"market_briefing:{target_date.isoformat()}", result, ttl=86400)
        return result

    def _fetch_indices(self, target_date: date) -> dict:
        """YFinanceService로 지수/환율 수집. 실패 시 None 필드."""
        ...  # YFinanceService().fetch_daily([^KS11, ^KQ11, ^GSPC, ^IXIC, USDKRW=X])

    def _call_claude_or_stub(self, indices: dict, context: dict) -> dict:
        """Claude API 호출 실패 시 스텁 반환."""
        if not settings.ANTHROPIC_API_KEY:
            return self._to_stub(indices)
        ...  # anthropic.Anthropic().messages.create(...)

    def _to_stub(self, indices: dict) -> dict:
        """API 키 없거나 실패 시 반환하는 기본값."""
        return {
            "summary": "시장 브리핑을 불러오지 못했습니다.",
            "sentiment": "neutral",
            "indices": indices,
            "source": "stub",
            ...
        }
```

> verify: `python -c "from cloud_server.services.briefing_service import BriefingService; print('OK')"`

---

### Step 3 — API 엔드포인트

**`cloud_server/api/ai.py` 수정**

```python
from cloud_server.services.briefing_service import BriefingService

@router.get("/briefing")
def get_briefing(
    date: str = Query(None, description="YYYY-MM-DD, default: today"),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    target = _parse_date(date) or date_.today()
    service = BriefingService()
    result = service.get_briefing(target, db)
    return {"success": True, "data": result}
```

> verify: `curl -H "Authorization: Bearer ..." http://localhost:4010/api/v1/ai/briefing`
> → 200, JSON 구조 확인

---

### Step 4 — 스케줄러

**`cloud_server/collector/scheduler.py` 수정**

```python
from cloud_server.services.briefing_service import BriefingService

# CollectorScheduler.start() 내부
self.scheduler.add_job(
    self._run_briefing,
    trigger=CronTrigger(hour=6, minute=0, day_of_week="mon-fri", timezone="Asia/Seoul"),
    id="market_briefing",
    replace_existing=True,
)

async def _run_briefing(self):
    try:
        BriefingService().generate_today()
        logger.info("시장 브리핑 생성 완료")
    except Exception as e:
        logger.error("시장 브리핑 생성 실패: %s", e)
```

> verify: 서버 시작 시 스케줄러 로그 확인 (`[OK] 수집 스케줄러 시작됨`)

---

### Step 5 — 프론트엔드 서비스

**`frontend/src/services/cloudClient.ts` 수정**

```typescript
export interface MarketBriefing {
  date: string
  summary: string
  sentiment: 'bearish' | 'slightly_bearish' | 'neutral' | 'slightly_bullish' | 'bullish'
  indices: {
    kospi:  { close: number; change_pct: number }
    kosdaq: { close: number; change_pct: number }
    usd_krw: number
    sp500:  { close: number; change_pct: number }
    nasdaq: { close: number; change_pct: number }
  }
  source: 'claude' | 'cache' | 'stub'
  generated_at: string
}

export const cloudAI = {
  getBriefing: (date?: string) =>
    client.get<{ success: boolean; data: MarketBriefing }>(
      '/api/v1/ai/briefing',
      date ? { params: { date } } : undefined,
    ).then(r => r.data.data),
}
```

> verify: TypeScript 타입 에러 없음 (`npm run build`)

---

### Step 6 — BriefingCard 컴포넌트

**`frontend/src/components/BriefingCard.tsx` 생성**

- `useQuery(['marketBriefing'], () => cloudAI.getBriefing(), { staleTime: 30분 })`
- **정상**: summary 텍스트 + sentiment 배지 + 지수 3종 (KOSPI/KOSDAQ/USD-KRW)
- **로딩**: 스켈레톤 (3줄)
- **스텁/에러**: "브리핑을 불러오지 못했습니다" (에러 UI 아님, 안내 텍스트)
- sentiment → 색상 매핑: bearish(빨강) / neutral(회색) / bullish(초록)

> verify: 컴포넌트 렌더링 3개 상태 확인 (브라우저)

---

### Step 7 — MainDashboard 통합

**`frontend/src/pages/MainDashboard.tsx` 수정**

```tsx
import BriefingCard from '../components/BriefingCard'

// OpsPanel 바로 아래 (JSX 내)
<OpsPanel ... />
<BriefingCard />   ← 추가
<ListView ... />
```

> verify: 브라우저에서 대시보드 로드 시 브리핑 카드 표시

---

## 4. 최종 검증

| 항목 | 방법 |
|------|------|
| Python 빌드 | `py_compile` 신규 파일 전체 |
| 프론트 빌드 | `npm run build` |
| API 응답 | `curl .../api/v1/ai/briefing` → 200 + JSON 구조 |
| 캐시 동작 | 두 번째 호출 `source: "cache"` |
| 스텁 동작 | `ANTHROPIC_API_KEY=""` 로 서버 실행 후 확인 |
| 브라우저 렌더링 | Playwright — BriefingCard 표시 확인 |
