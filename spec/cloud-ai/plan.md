# Cloud AI 분석 모듈 구현 계획 (cloud-ai)

> 작성일: 2026-03-09 | 상태: 초안

---

## 1. 아키텍처

```
[클라이언트] ──→ GET /api/v1/ai/analysis/{symbol}?type=summary
                    ↓
             [ai.py 라우터] (JWT 인증)
                    ↓
             [AIService.analyze()]
              ├─ key 체크 → 없으면 스텁
              ├─ 캐시 체크 (Redis/메모리)
              ├─ 한도 체크
              ├─ 데이터 수집:
              │   ├─ ContextService.get_symbol_context()  ← (신규 메서드)
              │   ├─ DataProvider.get_quote()
              │   ├─ DataProvider.get_financials()
              │   └─ DataProvider.get_daily_bars()
              ├─ type별 프롬프트 조립
              ├─ Claude API 호출 (anthropic SDK)
              ├─ 응답 파싱
              ├─ 캐시 저장
              └─ AIAnalysisLog DB 저장
```

**의존 관계**:
```
config.py (설정) ──→ redis.py (Redis 연결)
                 ──→ ai.py (DB 모델)
                 ──→ AIService (핵심 로직)
                      ├── ContextService (지표)
                      ├── DataProvider (시세/재무)
                      └── anthropic SDK (Claude 호출)
                 ──→ ai 라우터 ──→ main.py 등록
```

---

## 2. 구현 순서

### Step 1: Config + Redis 인프라

**변경 파일**: `cloud_server/core/config.py`, `cloud_server/core/redis.py` (신규)

**변경 내용**:

1. `config.py` — 설정 추가:
```python
# 기존 CLAUDE_MODEL 기본값 변경
CLAUDE_MODEL: str = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# 신규
AI_DAILY_LIMIT: int = int(os.environ.get("AI_DAILY_LIMIT", "100"))
AI_CACHE_TTL: int = int(os.environ.get("AI_CACHE_TTL", "3600"))
REDIS_URL: str = os.environ.get("REDIS_URL", "")
```

2. `redis.py` — Redis 연결 + fallback:
```python
import json
import logging
from datetime import datetime, timezone

import redis

from cloud_server.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None
_memory_cache: dict[str, tuple[str, float]] = {}  # key → (json_value, expire_at)


def get_redis() -> redis.Redis | None:
    """Redis 연결 반환. 불가 시 None."""
    global _redis_client
    if not settings.REDIS_URL:
        return None
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis_client.ping()
            logger.info("Redis 연결 성공")
        except Exception as e:
            logger.warning("Redis 연결 실패, 메모리 캐시 사용: %s", e)
            _redis_client = None
    return _redis_client


def cache_get(key: str) -> dict | None:
    """캐시 조회 (Redis → 메모리 fallback)."""
    r = get_redis()
    if r:
        try:
            val = r.get(key)
            return json.loads(val) if val else None
        except Exception:
            pass
    # 메모리 fallback
    entry = _memory_cache.get(key)
    if entry:
        val, expire_at = entry
        if datetime.now(timezone.utc).timestamp() < expire_at:
            return json.loads(val)
        del _memory_cache[key]
    return None


def cache_set(key: str, value: dict, ttl: int) -> None:
    """캐시 저장 (Redis → 메모리 fallback)."""
    r = get_redis()
    data = json.dumps(value, ensure_ascii=False)
    if r:
        try:
            r.setex(key, ttl, data)
            return
        except Exception:
            pass
    # 메모리 fallback
    expire_at = datetime.now(timezone.utc).timestamp() + ttl
    _memory_cache[key] = (data, expire_at)


def cache_backend() -> str:
    """현재 캐시 백엔드 이름."""
    return "redis" if get_redis() else "memory"
```

**verify**: `pytest cloud_server/` 기존 38개 통과 (기존 코드 영향 없음)

---

### Step 2: DB 모델 + ContextService 확장

**변경 파일**: `cloud_server/models/ai.py` (신규), `cloud_server/services/context_service.py`

**변경 내용**:

1. `models/ai.py` — AIAnalysisLog 모델:
```python
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from cloud_server.core.database import Base

class AIAnalysisLog(Base):
    __tablename__ = "ai_analysis_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), index=True, nullable=False)
    type = Column(String(20), nullable=False)       # sentiment|summary|risk|technical
    source = Column(String(20), nullable=False)      # claude|stub
    score = Column(Float, nullable=True)
    text = Column(Text, nullable=True)
    token_input = Column(Integer, default=0)
    token_output = Column(Integer, default=0)
    model = Column(String(50), default="")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

2. `context_service.py` — 종목별 지표 메서드 추가:
```python
def get_symbol_context(self, symbol: str) -> dict:
    """종목별 기술적 지표 계산.

    Returns:
        {
            "symbol": str,
            "current_price": float | None,
            "rsi_14": float | None,
            "rsi_21": float | None,
            "macd": float | None,
            "macd_signal": float | None,
            "bollinger_upper": float | None,
            "bollinger_lower": float | None,
            "volatility": float | None,
        }
    """
```

- DB의 DailyBar 조회 → RSI, MACD, 볼린저 밴드 계산
- yfinance fallback (DB 데이터 부족 시)
- `_calc_macd()`, `_calc_bollinger()` 내부 메서드 추가

**verify**: `pytest cloud_server/` 전체 통과

---

### Step 3: AIService 실제 구현

**변경 파일**: `cloud_server/services/ai_service.py`

**변경 내용**: 전체 재작성

```python
class AIService:
    def __init__(self, db: Session):
        self.db = db
        self._client: anthropic.Anthropic | None = None
        self._daily_count: int = 0
        self._daily_reset: date = date.today()

    async def analyze(self, symbol: str, type: str, user_id: int) -> dict:
        """종목 분석 (type별 분기).

        흐름:
        1. API 키 체크 → 없으면 스텁
        2. 캐시 체크 → 히트면 반환
        3. 일일 한도 체크 → 초과면 스텁
        4. type별 데이터 수집
        5. type별 프롬프트 조립
        6. Claude API 호출
        7. 응답 파싱
        8. 캐시 저장 + DB 이력 저장
        """

    def _build_prompt(self, type: str, data: dict) -> tuple[str, str]:
        """type별 시스템/유저 프롬프트 생성.
        Returns: (system_prompt, user_prompt)
        """

    def _call_claude(self, system: str, user: str, max_tokens: int) -> dict:
        """Claude API 호출. 실패 시 None 반환."""

    def _parse_response(self, raw: str, type: str) -> dict:
        """Claude 응답 JSON 파싱. 파싱 실패 시 기본값."""

    def _stub_result(self, symbol: str, type: str) -> dict:
        """스텁 응답 생성 (키 없음/한도 초과/에러 시)."""

    def get_status(self) -> dict:
        """AI 모듈 상태 반환."""
```

**type별 프롬프트 설계**:

| type | 시스템 프롬프트 | max_tokens | 입력 |
|------|-------------|-----------|------|
| `sentiment` | "감성 점수(-1~1)와 한 줄 근거를 JSON으로" | 100 | 지표+현재가 |
| `summary` | "종합 분석 리포트를 JSON으로" | 500 | 지표+현재가+재무 |
| `risk` | "리스크 평가를 JSON으로" | 300 | 지표+변동성+볼린저 |
| `technical` | "기술적 분석을 JSON으로" | 400 | 지표 전체+최근 일봉 |

**공통 시스템 프롬프트 접미어**:
```
투자 조언이나 매매 추천은 절대 하지 마세요.
반드시 JSON만 응답하세요: {"score": float, "label": str, "text": str}
```

**에러 처리**:
- `anthropic.AuthenticationError` → 로그 + 스텁 (A4)
- `anthropic.RateLimitError` → 로그 + 스텁
- `anthropic.APIError` → 로그 + 스텁
- JSON 파싱 실패 → 로그 + 기본값 (score=0, text=raw)
- 타임아웃 → 30초, 로그 + 스텁

**verify**: 단위 테스트 (mock anthropic client)

---

### Step 4: API 라우터 + main.py 등록

**변경 파일**: `cloud_server/api/ai.py` (신규), `cloud_server/main.py`

**변경 내용**:

1. `api/ai.py`:
```python
router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

@router.get("/analysis/{symbol}")
async def analyze(
    symbol: str,
    type: str = Query("summary", regex="^(sentiment|summary|risk|technical)$"),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """종목 AI 분석"""
    service = AIService(db)
    result = await service.analyze(symbol, type, user.id)
    return {"success": True, "data": result}

@router.get("/status")
async def status(user=Depends(current_user)):
    """AI 모듈 상태"""
    ...

@router.get("/history")
async def history(
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """분석 이력 조회 (어드민 전용)"""
    if not user.is_admin:
        raise HTTPException(403, "어드민 권한 필요")
    ...
```

2. `main.py` — 라우터 등록:
```python
from cloud_server.api.ai import router as ai_router
app.include_router(ai_router)
```

**verify**: `pytest cloud_server/` 전체 통과

---

### Step 5: 테스트

**변경 파일**: `cloud_server/tests/test_ai.py` (신규)

**테스트 목록**:

1. **스텁 fallback (키 미설정)**:
   - `ANTHROPIC_API_KEY=""` → `source: "stub"`, `score: 0.0` 반환
   - 서버 에러 없음 (200 OK)

2. **스텁 fallback (유효하지 않은 키)**:
   - mock anthropic → `AuthenticationError` raise
   - `source: "stub"` 반환 + 에러 로깅

3. **캐시 동작**:
   - 첫 호출 → `cached: false`
   - 동일 symbol+type 재호출 → `cached: true`

4. **일일 한도**:
   - `AI_DAILY_LIMIT=2` 설정
   - 3번째 호출 → `source: "stub"` 반환

5. **type별 분기**:
   - `type=sentiment` → score만 반환
   - `type=summary` → score + text 반환
   - 잘못된 type → 422 에러

6. **이력 저장**:
   - 분석 호출 후 `AIAnalysisLog` 레코드 존재 확인
   - `token_input`, `token_output` 값 확인

7. **이력 조회 (어드민)**:
   - 어드민 → 200 + 이력 반환
   - 일반 유저 → 403

8. **상태 API**:
   - `GET /api/v1/ai/status` → available, model, daily_usage 반환

**테스트 전략**: Claude API는 mock (실제 호출 금지). `unittest.mock.patch`로 anthropic client mock.

**verify**: `pytest cloud_server/tests/test_ai.py -v` 전체 통과

---

### Step 6: Alembic 마이그레이션 + init_db 갱신

**변경 파일**: `cloud_server/core/init_db.py`, `cloud_server/alembic/env.py`

**변경 내용**:

1. `init_db.py` — AIAnalysisLog import 추가 (Base.metadata에 등록)
2. `alembic/env.py` — AIAnalysisLog import 추가
3. `alembic revision --autogenerate -m "add ai_analysis_logs table"` 실행

**verify**: `alembic upgrade head` → ai_analysis_logs 테이블 생성

---

## 3. 수정 파일 목록

| 파일 | 변경 수준 | Step |
|------|----------|------|
| `cloud_server/core/config.py` | 수정 (설정 3개 추가, CLAUDE_MODEL 기본값 변경) | 1 |
| `cloud_server/core/redis.py` | 신규 (Redis 연결 + cache_get/set) | 1 |
| `cloud_server/models/ai.py` | 신규 (AIAnalysisLog) | 2 |
| `cloud_server/services/context_service.py` | 수정 (get_symbol_context 추가) | 2 |
| `cloud_server/services/ai_service.py` | 전체 재작성 | 3 |
| `cloud_server/api/ai.py` | 신규 (라우터 3개 엔드포인트) | 4 |
| `cloud_server/main.py` | 수정 (라우터 등록 1줄) | 4 |
| `cloud_server/tests/test_ai.py` | 신규 (테스트 8+개) | 5 |
| `cloud_server/core/init_db.py` | 수정 (import 1줄) | 6 |
| `cloud_server/alembic/env.py` | 수정 (import 1줄) | 6 |

---

## 4. 검증 체크리스트

- [ ] Step 1: `REDIS_URL` 설정 시 Redis 연결, 미설정 시 메모리 캐시 fallback
- [ ] Step 1: 기존 테스트 38개 깨지지 않음
- [ ] Step 2: `AIAnalysisLog` 모델 생성, `get_symbol_context()` 지표 반환
- [ ] Step 3: `ANTHROPIC_API_KEY` 있으면 Claude 호출, 없으면 스텁
- [ ] Step 3: 유효하지 않은 키 → 에러 로깅 + 스텁 (크래시 없음)
- [ ] Step 3: type별 프롬프트 분기 (sentiment/summary/risk/technical)
- [ ] Step 3: 캐시 TTL 동작 (Redis/메모리)
- [ ] Step 3: 일일 한도 초과 → 스텁
- [ ] Step 4: `GET /api/v1/ai/analysis/{symbol}?type=summary` → 200
- [ ] Step 4: `GET /api/v1/ai/status` → available, model, daily_usage
- [ ] Step 4: `GET /api/v1/ai/history` → 어드민만 접근 가능
- [ ] Step 5: 테스트 8개+ 전체 통과
- [ ] Step 6: `alembic revision --autogenerate` → ai_analysis_logs 마이그레이션 생성
- [ ] 전체: `pytest cloud_server/` 전체 통과 (기존 38 + 신규)

---

## 5. 참고

- spec: `spec/cloud-ai/spec.md`
- 아키텍처: `docs/architecture.md` §4.5
- 기존 context API: `cloud_server/api/context.py`
- DataProvider: `cloud_server/data/provider.py`
- 기존 AI 스텁: `cloud_server/services/ai_service.py`
- 기존 main.py 라우터 등록 패턴: `cloud_server/main.py` L117-127
- 기존 테스트 conftest: `cloud_server/tests/conftest.py`

---

**마지막 갱신**: 2026-03-09
