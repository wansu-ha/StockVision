# Cloud AI 분석 모듈 명세서 (cloud-ai)

> 작성일: 2026-03-09 | 상태: 구현 완료 | cloud-server F9/F10 구현

---

## 1. 목표

`cloud_server/services/ai_service.py`의 v1 스텁을 실제 Claude API 호출로 교체한다.
`.env`에 `ANTHROPIC_API_KEY`가 있으면 동작, 없거나 유효하지 않으면 기존 스텁(중립값) 반환.

**아키텍처 위치**: 클라우드 서버 내부 모듈 (§4.5 Cloud AI 분석 모듈)
**법적 성격**: 데이터 가공 도구 (RSI 계산과 동일 — 매매 판단/조언 금지)

---

## 2. 현황

### 이미 구현된 것
- `ai_service.py` — AIService 클래스, `get_sentiment()` 스텁 (score: 0.0 반환)
- `context_service.py` — ContextService (RSI, MACD, 볼린저, 변동성 등 지표 계산)
- `DataProvider` — yfinance 시세, DART 재무/배당 데이터 수집
- `config.py` — `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` 환경변수
- `requirements.txt` — `anthropic>=0.25.0` 포함
- `api/context.py` — `GET /api/v1/context` (지표만, AI 분석 미포함)

### 없는 것
- Claude API 실제 호출 코드
- AI 분석 전용 API 엔드포인트
- 분석 결과 DB 모델 (현재 메모리 캐시만)
- 토큰 사용량 추적
- AIService를 호출하는 코드 (라우터 연결 없음)

---

## 3. 요구사항

### 3.1 기능적 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| A1 | 종목 종합 분석 — `type` 파라미터로 분석 유형 선택 | P0 |
| A2 | 분석 유형: `sentiment` (감성 점수), `summary` (종합 요약), `risk` (리스크 평가), `technical` (기술적 분석) | P0 |
| A3 | API 키 미설정 시 graceful fallback — 스텁값 반환, 에러 없음 | P0 |
| A4 | API 키 유효하지 않을 때 — 에러 로깅 + 스텁값 반환 (서버 크래시 금지) | P0 |
| A5 | 분석 결과 캐싱 — Redis (가용 시) / 메모리 (fallback), TTL 기반 | P0 |
| A6 | 토큰 사용량 추적 — 호출당 input/output 토큰 수 기록 | P1 |
| A7 | 일일 호출 한도 — 설정 가능한 일일 최대 호출 수, 초과 시 스텁 반환 | P1 |
| A8 | AI 분석 API 엔드포인트 — 프론트엔드/로컬 서버에서 호출 가능 | P0 |
| A9 | 분석 이력 DB 저장 — 종목별 분석 결과 + 토큰 사용량 이력 | P1 |
| A10 | 어드민 AI 분석 조회 — 이력, 사용량 통계, 에러 로그 | P1 |

### 3.2 비기능적 요구사항

| 항목 | 목표 |
|------|------|
| Claude API 응답 | < 10초 (타임아웃 30초) |
| 캐시 TTL | 1시간 (기본값, 설정 가능) |
| 일일 한도 | 100회 (기본값, 설정 가능) |
| 프롬프트 제약 | "매수/매도하세요" 등 직접 조언 금지 — 데이터 분석만 |
| 모델 | config에서 로드 (`CLAUDE_MODEL`, 하드코딩 금지) |

---

## 4. API 설계

### 4.1 엔드포인트

```
GET /api/v1/ai/analysis/{symbol}?type={type}  → 종목 분석 (type별 분기)
GET /api/v1/ai/status                         → AI 모듈 상태
GET /api/v1/ai/history                        → 분석 이력 (어드민)
```

### 4.2 분석 유형 (`type` 파라미터)

| type | 설명 | Claude 호출 | 입력 데이터 |
|------|------|------------|-----------|
| `sentiment` | 감성 점수 (-1~1) + 근거 | 경량 (max_tokens 작음) | 지표 + 현재가 |
| `summary` | 종합 분석 리포트 | 표준 | 지표 + 현재가 + 재무 |
| `risk` | 리스크 평가 (변동성, 낙폭 가능성) | 표준 | 지표 + 변동성 + 볼린저 |
| `technical` | 기술적 분석 (차트 패턴, 추세) | 표준 | 지표 전체 + 일봉 |

`type` 미지정 시 기본값: `summary`

### 4.3 응답 스키마

**분석 응답** (`GET /api/v1/ai/analysis/005930?type=summary`):
```json
{
  "symbol": "005930",
  "type": "summary",
  "result": {
    "score": 0.35,
    "label": "slightly_positive",
    "text": "삼성전자는 최근 반도체 업황 회복 기대감으로..."
  },
  "indicators_used": ["rsi_14", "macd", "bollinger_upper"],
  "source": "claude",
  "cached": false,
  "analyzed_at": "2026-03-09T10:30:00Z",
  "token_usage": {
    "input": 450,
    "output": 280
  }
}
```

**키 미설정 시 응답** (동일 구조, source만 다름):
```json
{
  "symbol": "005930",
  "type": "summary",
  "result": {
    "score": 0.0,
    "label": "neutral",
    "text": null
  },
  "indicators_used": [],
  "source": "stub",
  "cached": false,
  "analyzed_at": "2026-03-09T10:30:00Z",
  "token_usage": null
}
```

**상태 응답** (`GET /api/v1/ai/status`):
```json
{
  "available": true,
  "model": "claude-sonnet-4-20250514",
  "daily_usage": 23,
  "daily_limit": 100,
  "cache_ttl_seconds": 3600,
  "cache_backend": "redis"
}
```

**이력 응답** (`GET /api/v1/ai/history?limit=20`, 어드민 전용):
```json
{
  "items": [
    {
      "id": 1,
      "symbol": "005930",
      "type": "summary",
      "source": "claude",
      "token_input": 450,
      "token_output": 280,
      "created_at": "2026-03-09T10:30:00Z"
    }
  ],
  "total": 142
}
```

### 4.4 인증

- 분석 API: JWT 인증 필수 (`current_user`)
- 상태 API: JWT 인증 필수
- 이력 API: JWT + 어드민 권한 (`is_admin`)

---

## 5. 데이터 흐름

```
사용자 → GET /api/v1/ai/analysis/005930?type=summary
  ↓
[라우터] ai.py
  ↓
[AIService.analyze(symbol, type)]
  ├── ANTHROPIC_API_KEY 체크 → 없으면 스텁 반환
  ├── Redis 캐시 체크 → 히트면 캐시 반환 (Redis 없으면 메모리 캐시)
  ├── 일일 한도 체크 → 초과면 스텁 반환
  ├── type별 데이터 수집:
  │   ├── ContextService → 지표 (RSI, MACD 등)
  │   ├── DataProvider.get_quote() → 현재가
  │   ├── DataProvider.get_financials() → 재무 (summary/risk)
  │   └── DataProvider.get_daily_bars() → 일봉 (technical)
  ├── type별 프롬프트 조립
  ↓
[Claude API 호출]
  ├── 응답 파싱: score + text
  ├── 토큰 사용량 기록
  ↓
[캐시 저장 (Redis/메모리)] + [이력 DB 저장] → 응답 반환
```

### 5.1 캐시 전략

```
                    ┌──────────┐
                    │  Redis   │ ← 1차 (가용 시)
                    │  TTL 자동 │
                    └────┬─────┘
                         │ 불가 시
                    ┌────▼─────┐
                    │ 메모리    │ ← 2차 (fallback)
                    │ dict+TTL │
                    └──────────┘
```

- `REDIS_URL` 설정 시 Redis 사용, 미설정 시 메모리 캐시 fallback
- 캐시 키: `ai:{symbol}:{type}` (예: `ai:005930:summary`)
- TTL: `AI_CACHE_TTL` (기본 3600초)
- Redis 연결은 AI 캐시 외에 향후 rate_limit 등 공용 인프라로 활용

---

## 6. 프롬프트 설계 원칙

- **입력**: 기술적 지표 (RSI, MACD 등) + 현재가 + 재무 데이터 (선택)
- **출력 형식**: JSON (`{"score": float, "summary": str}`)
- **금지 표현**: "매수/매도 추천", "~하세요", "투자하시길" 등 직접 조언
- **허용 표현**: "RSI가 과매수 구간", "변동성이 높은 상태", "실적 개선 추세"
- **시스템 프롬프트**: "당신은 주식 데이터 분석가입니다. 수치와 추세를 객관적으로 분석하세요. 투자 조언이나 매매 추천은 절대 하지 마세요."

---

## 7. 설정

`cloud_server/core/config.py`에 추가:

```python
# AI (기존)
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# AI (신규)
AI_DAILY_LIMIT: int = int(os.environ.get("AI_DAILY_LIMIT", "100"))
AI_CACHE_TTL: int = int(os.environ.get("AI_CACHE_TTL", "3600"))

# Redis (신규 — AI 캐시 + 향후 rate_limit 공용)
REDIS_URL: str = os.environ.get("REDIS_URL", "")
```

**참고**: 기본 모델을 `claude-opus-4-6` → `claude-sonnet-4-20250514`로 변경 (비용 효율. 데이터 분석에 Opus 불필요)

---

## 8. DB 모델

### 8.1 분석 이력 (`AIAnalysisLog`)

```python
class AIAnalysisLog(Base):
    __tablename__ = "ai_analysis_logs"

    id: int (PK, autoincrement)
    symbol: str (index)
    type: str              # sentiment | summary | risk | technical
    source: str            # claude | stub
    score: float | None    # 감성 점수 (-1~1)
    text: str | None       # 분석 텍스트 (요약)
    token_input: int       # 입력 토큰 수
    token_output: int      # 출력 토큰 수
    model: str             # 사용된 모델명
    user_id: int (FK → users.id)
    created_at: datetime
```

---

## 9. 범위

### 포함
- AIService 실제 구현 (Claude API 호출, type별 분기)
- 분석 유형 4종 (sentiment, summary, risk, technical)
- API 엔드포인트 3개 (analysis, status, history)
- graceful fallback (키 없음 / 유효하지 않음 / 한도 초과)
- Redis 캐시 (가용 시) + 메모리 캐시 (fallback)
- Redis 연결 인프라 (공용, config에 REDIS_URL)
- 토큰 사용량 추적
- 분석 이력 DB 저장 (`AIAnalysisLog`)
- 어드민 이력 조회 API
- 테스트

### 미포함
- 뉴스 크롤링 (외부 데이터 소스 추가 — v2 목표)
- 프론트엔드 UI (별도 Unit 5)
- 어드민 UI (별도 Unit 6, 이 spec의 API를 소비)
- Custom LLM 통합 (로컬 서버, 별도 spec)

---

## 10. 수용 기준

- [x] A1: `GET /api/v1/ai/analysis/{symbol}?type=sentiment` → Claude 호출 → score 반환
- [x] A2: `GET /api/v1/ai/analysis/{symbol}?type=summary` → 종합 분석 리포트 반환
- [x] A2: `type=risk`, `type=technical` → 각 유형별 분석 반환
- [x] A3: `ANTHROPIC_API_KEY` 미설정 → `source: "stub"`, `score: 0.0` 반환 (에러 없음)
- [x] A4: 유효하지 않은 키 → 에러 로깅 + 스텁 반환 (서버 크래시 없음)
- [x] A5: 동일 종목+type TTL 내 재호출 → 캐시 응답 (`cached: true`)
- [x] A5: Redis 가용 시 Redis 캐시, 불가 시 메모리 캐시 fallback
- [x] A6: 호출마다 토큰 사용량 로깅
- [x] A7: 일일 한도 초과 → 스텁 반환
- [x] A8: `GET /api/v1/ai/status` → 키 유효 여부 + 일일 사용량 + 캐시 백엔드 반환
- [x] A9: 분석 결과 `AIAnalysisLog` 테이블에 저장
- [x] A10: `GET /api/v1/ai/history` → 어드민 전용 이력 조회
- [x] 기존 테스트 깨지지 않음 (`pytest cloud_server/` 전체 통과)
- [x] 신규 테스트 추가 (스텁 fallback, 캐시, 한도 초과, 이력 저장)

---

## 11. 수정 파일 (예상)

| 파일 | 변경 |
|------|------|
| `cloud_server/services/ai_service.py` | 스텁 → 실제 구현 (type별 분기, Redis/메모리 캐시) |
| `cloud_server/api/ai.py` | 신규 — AI 분석 라우터 (analysis, status, history) |
| `cloud_server/core/config.py` | AI_DAILY_LIMIT, AI_CACHE_TTL, REDIS_URL 추가, 기본 모델 변경 |
| `cloud_server/core/redis.py` | 신규 — Redis 연결 관리 (get_redis, fallback) |
| `cloud_server/models/ai.py` | 신규 — AIAnalysisLog 모델 |
| `cloud_server/main.py` | 라우터 등록 |
| `cloud_server/tests/test_ai.py` | 신규 — AI 분석 테스트 |

---

## 12. 참고

- 아키텍처: `docs/architecture.md` §4.5 (Cloud AI 분석 모듈)
- 클라우드 서버 spec: `spec/cloud-server/spec.md` F9, F10
- 컨텍스트 서비스: `cloud_server/services/context_service.py`
- 데이터 프로바이더: `cloud_server/data/`
- Custom LLM (별도): `docs/research/llm-feasibility-analysis.md`
