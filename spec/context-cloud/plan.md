# 컨텍스트 클라우드 구현 계획서 (context-cloud)

> 작성일: 2026-03-04 | 상태: 초안 | 범위: 클라우드 서버 + 로컬 서버 캐시 연동

---

## 0. 전제 조건

- 클라우드 서버에서 시장 변수를 계산·제공 (`GET /api/context`)
- 로컬 서버가 장 마감 후 1회 fetch → 로컬 캐시(JSON) 저장
- 전략 평가 엔진은 캐시된 컨텍스트를 참조 (실시간 아님)
- 의존: `spec/data-source/plan.md` (데이터 소스)

---

## 1. 구현 단계

### Step 1 — 클라우드 API: 시장 컨텍스트 계산 + 제공

**목표**: `GET /api/context` → 시장 지표 JSON 반환

파일:
- `backend/app/services/market_context.py` (계산)
- `backend/app/api/context.py` (라우터)
- `backend/app/models/market_context.py` (DB 캐시 — 선택)

```python
# GET /api/context 응답 구조
{
  "date": "2026-03-04",
  "computed_at": "2026-03-04T16:00:00+09:00",
  "market": {
    "kospi_rsi_14": 52.3,
    "kospi_20d_volatility": 0.18,
    "kosdaq_rsi_14": 48.1,
    "market_trend": "neutral"   # "bullish" | "neutral" | "bearish"
  },
  "sectors": {
    "반도체": { "momentum_5d": 0.03, "momentum_20d": -0.01 },
    "2차전지": { "momentum_5d": -0.02, "momentum_20d": 0.05 }
  }
}
```

**계산 주기**: 장 마감 후 1회 (15:30 KST 이후 배치)

**검증:**
- [ ] `GET /api/context` 200 응답 + 올바른 구조
- [ ] RSI, 변동성 계산 단위 테스트
- [ ] 데이터 없을 때 마지막 유효 캐시 반환

### Step 2 — 로컬 서버: 컨텍스트 fetch + 캐시

**목표**: 로컬 서버가 장 마감 후 클라우드에서 컨텍스트 가져와 캐시

파일: `local_server/cloud/context.py`

```python
CONTEXT_CACHE = Path(APPDATA) / "StockVision" / "context_cache.json"

class ContextClient:
    def fetch_and_cache(self, jwt: str):
        """장 마감 후 1회 호출"""
        resp = httpx.get(CLOUD_URL + "/api/context",
                         headers={"Authorization": f"Bearer {jwt}"})
        data = resp.json()
        CONTEXT_CACHE.write_text(json.dumps(data))

    def get_cached(self) -> dict:
        if CONTEXT_CACHE.exists():
            return json.loads(CONTEXT_CACHE.read_text())
        return {}
```

**스케줄**: `scheduler.py`에서 15:35 KST (장 마감 5분 후) 1회 실행

**검증:**
- [ ] 장 마감 후 자동 fetch → 캐시 파일 갱신
- [ ] 클라우드 오류 시 캐시 파일 유지 (이전 데이터)
- [ ] 전략 평가 시 `ContextClient.get_cached()` 정상 반환

### Step 3 — 전략 평가에 컨텍스트 주입

**목표**: 실행 엔진에서 컨텍스트 변수를 조건 평가에 사용

파일: `local_server/engine/evaluator.py`

```python
ctx = ContextClient().get_cached()
# 조건 평가 시 ctx.market.kospi_rsi_14 등 참조 가능
```

**검증:**
- [ ] 컨텍스트 변수를 조건으로 사용하는 규칙 평가 테스트
- [ ] 캐시 없을 때 조건 평가 스킵 (에러 아님) + 경고 로그

---

## 2. 파일 목록

| 파일 | 구분 | 설명 |
|------|------|------|
| `backend/app/services/market_context.py` | 신규 | 시장 지표 계산 |
| `backend/app/api/context.py` | 신규 | `GET /api/context` |
| `local_server/cloud/context.py` | 신규 | fetch + 캐시 |
| `local_server/engine/evaluator.py` | 수정 | 컨텍스트 주입 |

---

## 3. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — context API (클라우드 시장 지표 계산)` |
| 2 | `feat: Step 2 — 로컬 컨텍스트 fetch + 캐시` |
| 3 | `feat: Step 3 — 전략 평가에 컨텍스트 변수 주입` |
