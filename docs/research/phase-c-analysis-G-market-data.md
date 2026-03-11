> 작성일: 2026-03-12 | Phase C 분석 G: 시세 데이터 아키텍처

# G. 시세 데이터 아키텍처 분석

## G-1. 현재 시세 데이터 흐름

### 클라우드 서버 (yfinance 기반)

**데이터 제공 API:**
| 엔드포인트 | 설명 | 캐싱 |
|-----------|------|------|
| GET `/api/v1/stocks/{symbol}/bars` | 일봉 OHLCV | DB (DailyBar) — 영구 |
| GET `/api/v1/stocks/{symbol}/quote` | 현재가 (지연) | 없음 (매번 yfinance) |
| GET `/api/v1/context` | 시장 컨텍스트 (RSI, 변동성) | 없음 (매번 계산) |
| GET `/api/v1/stocks/{symbol}/financials` | 재무 데이터 | DB (CompanyFinancial) |
| GET `/api/v1/stocks/{symbol}/dividends` | 배당 이력 | DB (CompanyDividend) |

**데이터 수집 흐름:**
```
API 요청 → DB 캐시 확인 → miss → DataAggregator
                                    ├─ DART Provider (재무) [optional]
                                    └─ YFinance Provider (가격/배당) [always]
                                         → DB 저장 (영구 캐시)
```

**스케줄러 (APScheduler):**
| 시각 (KST) | 작업 |
|------------|------|
| 08:00 | 종목 마스터 갱신 (StockMaster) |
| 16:00 | 일봉 저장 (DailyBar) |
| 17:00 | yfinance 보조 수집 (지수, 환율) |
| 18:00 | 데이터 정합성 체크 |

**yfinance 심볼 변환:** 6자리 숫자 → `{symbol}.KS` (KOSPI) 또는 `.KQ` (KOSDAQ)

### 로컬 서버 (증권사 실시간)

**실시간 시세:**
```
Broker WS → on_quote() → BarBuilder (1분 분봉 집계)
                              ↓
                        IndicatorProvider (yfinance 일봉 → RSI/SMA/EMA/MACD/볼린저)
                              ↓
                        Evaluator → SystemTrader → Executor → Broker Order
```

**BarBuilder:** WS 시세 → 1분 분봉 OHLCV 집계 (메모리)
- `_current`: 구성 중인 분봉
- `_completed`: 직전 완성 분봉
- `_latest`: 최신 시세 스냅샷
- `fill_gap()`: WS 끊김 시 REST quote 보충

**IndicatorProvider:** yfinance 60일 일봉 → 기술적 지표
- 캐시: 1일 유효 (메모리)
- 지표: RSI(14/21), SMA(5/10/20/60), EMA(12/20/26), MACD, 볼린저, 평균거래량

### 프론트엔드

- `cloudBars.get(symbol, start?, end?)` → 차트 (PriceChart 5종)
- `cloudQuote.get(symbol)` → 현재가 표시 (15s refetch)
- 로컬 시세 직접 조회 없음 (WS는 엔진 내부에서만 사용)

## G-2. DB 모델

### StockMaster (`cloud_server/models/market.py`)
```
symbol (PK), name, market (KOSPI/KOSDAQ/OVERSEAS), sector, corp_code, is_active, updated_at
```

### DailyBar (`cloud_server/models/market.py`)
```
id, symbol, date, open, high, low, close (Integer 원단위), volume (BigInteger), change_pct, created_at
Unique: (symbol, date)
```

### MinuteBar (`cloud_server/models/market.py`)
```
id, symbol, timestamp (KST 1분단위), open, high, low, close, volume, created_at
Unique: (symbol, timestamp)
```

### Watchlist, CompanyFinancial, CompanyDividend — 각각 존재

## G-3. 캐싱 현황

| 레이어 | 위치 | 유효기간 | 상태 |
|--------|------|---------|------|
| DailyBar DB | 클라우드 PostgreSQL | 영구 | 활성 — /bars 요청 시 miss → yfinance → DB 저장 |
| Redis | 클라우드 | TTL 기반 | **준비됨, 미사용** (코드 있으나 호출부 없음) |
| Memory fallback | 클라우드 | TTL 기반 | **준비됨, 미사용** |
| IndicatorProvider | 로컬 메모리 | 1일 | 활성 — 엔진 시작 시 refresh |
| BarBuilder | 로컬 메모리 | 서버 실행 중 | 활성 — WS 시세 실시간 집계 |
| Context | 클라우드 | **없음** | 매 요청마다 계산 |
| Quote | 클라우드 | **없음** | 매 요청마다 yfinance 호출 |

### yfinance 호출 빈도

| 위치 | 빈도 | 캐싱 |
|------|------|------|
| /bars (클라우드) | on-demand (DB miss 시만) | DB 영구 |
| /quote (클라우드) | **매 요청** | 없음 |
| context_service | DB 부족 시 폴백 | 없음 |
| IndicatorProvider (로컬) | 1일 1회 | 메모리 1일 |
| Scheduler 17:00 | 1일 1회 | DB |

## G-4. 개선 필요 사항

### 즉시 필요
1. **Quote 캐싱**: 현재 매 요청마다 yfinance 호출 → Redis TTL 60s 추가
2. **Context 캐싱**: RSI/EMA는 일봉 기반 → 1일 캐시 가능

### LLM 분석용 (Phase C)
3. **캐싱 활성화**: Redis 레이어 준비됨 → 호출부만 추가하면 됨
4. **LLM 데이터 포맷**: Claude API에 넘길 시세 데이터 구조 설계 필요
5. **용량 예측**: 코스피+코스닥 ~2,500종목 × 10년 일봉 = ~6M rows ≈ 500MB

### 장기
6. **분봉 수집**: MinuteBar 모델 존재하나 실제 수집 로직 미구현 (로컬 BarBuilder는 메모리만)
7. **실시간 시세**: 프론트엔드에 WS 시세 전달 미구현 (현재 cloud quote 폴링만)

## G-5. 데이터 흐름 다이어그램

```
┌─────────────── 프론트엔드 ───────────────┐
│ PriceChart → cloudBars.get()             │
│ DetailView → cloudQuote.get()            │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│ 클라우드 서버 :4010                      │
│                                          │
│ API → DataAggregator                     │
│         ├─ DART Provider (재무)          │
│         └─ YFinance Provider (가격)      │
│                                          │
│ DB: StockMaster, DailyBar, MinuteBar     │
│ Redis: 준비됨, 미사용                    │
│ Scheduler: 08/16/17/18시 수집            │
└──────────────────────────────────────────┘

┌─────────────── 로컬 서버 :4020 ──────────┐
│ Broker WS → BarBuilder (분봉, 메모리)    │
│ yfinance → IndicatorProvider (지표, 1일) │
│ Engine: Quote→Bar→Indicator→Eval→Order   │
└──────────────────────────────────────────┘
```

## G-6. 주요 파일 경로

| 파일 | 역할 |
|------|------|
| `cloud_server/models/market.py` | StockMaster, DailyBar, MinuteBar, Watchlist |
| `cloud_server/api/market_data.py` | /bars, /quote, /financials, /dividends |
| `cloud_server/data/aggregator.py` | DataAggregator (프로바이더 라우팅) |
| `cloud_server/data/yfinance_provider.py` | YFinanceProvider |
| `cloud_server/core/redis.py` | Redis + Memory 캐시 레이어 |
| `cloud_server/collector/scheduler.py` | APScheduler (수집 스케줄) |
| `cloud_server/services/context_service.py` | 시장 컨텍스트 계산 |
| `local_server/engine/bar_builder.py` | WS → 1분 분봉 |
| `local_server/engine/indicator_provider.py` | 기술적 지표 (yfinance) |
| `local_server/engine/engine.py` | 전략 엔진 통합 |
