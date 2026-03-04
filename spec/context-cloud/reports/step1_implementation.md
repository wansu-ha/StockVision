# context-cloud 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성/수정 파일 목록

| 파일 | 내용 |
|------|------|
| `backend/app/services/market_context.py` | KOSPI/KOSDAQ RSI(14), 20일 변동성, 시장 추세 계산 (yfinance) |
| `backend/app/api/context.py` | `GET /api/context` — 인증 필요, 당일 1회 캐시 |
| `backend/app/main.py` | context_router 등록 |
| `local_server/cloud/context.py` | 파일 캐시 방식 + JWT 인증 fetch |
| `local_server/engine/scheduler.py` | 15:35 KST 자동 컨텍스트 갱신 + 오늘 갱신 플래그 |
| `local_server/engine/evaluator.py` | `_resolve()` — 중첩 `market` 섹션 fallback 지원 |

## 주요 설계

### 컨텍스트 구조
```json
{
  "date": "2026-03-04",
  "computed_at": "2026-03-04T07:00:00+00:00",
  "market": {
    "kospi_rsi_14": 52.3,
    "kospi_20d_volatility": 0.18,
    "kosdaq_rsi_14": 48.1,
    "market_trend": "neutral"
  }
}
```

### 갱신 흐름
```
scheduler.run() → 15:35 KST 감지
  → _refresh_context()
      → fetch_and_cache(jwt)
          → GET /api/context (JWT 인증)
          → %APPDATA%/StockVision/context_cache.json 저장
```

### 평가 시 변수 resolve 우선순위
1. `price` → kiwoom prices dict
2. 플랫 조회 → `ctx["kospi_rsi_14"]`
3. 중첩 조회 → `ctx["market"]["kospi_rsi_14"]`

## 비고
- 클라우드 오류 시 이전 캐시 유지 (오래된 컨텍스트로 평가 계속)
- `market_trend` 결정 로직: RSI > 60 → bullish, RSI < 40 → bearish, 나머지 → neutral
- sectors 데이터는 현재 빈 dict (data-source spec에서 섹터 데이터 추가 예정)
