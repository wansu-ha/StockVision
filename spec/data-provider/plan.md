# DataProvider 구현 계획서

> 작성일: 2026-03-07 | 상태: 초안 | 범위: spec/data-provider/spec.md Step 1~3

---

## 0. 현황

### 기존 코드 상태

| 항목 | 상태 | 파일 |
|------|------|------|
| StockMaster 모델 | 운영 중 | `cloud_server/models/market.py` |
| DailyBar/MinuteBar 모델 | 운영 중 | `cloud_server/models/market.py` |
| MarketRepository | 운영 중 | `cloud_server/services/market_repository.py` |
| YFinanceService | 운영 중 (지수/환율 6종목) | `cloud_server/services/yfinance_service.py` |
| CollectorScheduler | 운영 중 | `cloud_server/collector/scheduler.py` |
| 종목 검색/상세 API | 운영 중 | `cloud_server/api/stocks.py` |
| 가격 차트 API | 없음 (레거시 backend/:8000에만 존재) | — |
| 재무/배당 데이터 | 없음 | — |
| DART 연동 | 없음 (API 키만 `.env`에 등록) | — |

### 이 계획서의 범위

spec §8 마이그레이션 계획 **Step 1~3 전체**:

- **Step 1~7**: ABC + YFinance + DART + Aggregator + API + 스케줄러
- **Step 8~9**: KIS/키움 프로바이더 (서비스 키 발급 후)
- **Step 10**: 레거시 backend/ 제거 + 프론트엔드 전환

---

## 1. 구현 단계

### Step 1 — DataProvider ABC + 데이터 클래스

**목표**: 프로바이더 인터페이스 정의

**파일:**
- `cloud_server/data/__init__.py` (신규)
- `cloud_server/data/provider.py` (신규)

**구현 내용:**
```
1. cloud_server/data/ 패키지 생성

2. DataProvider ABC (spec §2 그대로)
   - name (abstract property)
   - capabilities() (abstract)
   - get_daily_bars() → list[DailyBar] (기본: [])
   - get_quote() → Optional[ProviderQuote] (기본: None)
   - get_financials() → FinancialData | None (기본: None)
   - get_dividends() → list[DividendData] (기본: [])
   - supports_symbol() → bool (기본: True)

3. 데이터 클래스 4종 (같은 파일)
   - DailyBar (date, OHLCV)
   - ProviderQuote (symbol, price, change, change_pct, volume, timestamp)
   - FinancialData (corp_code, symbol, period, 재무 지표들, extra dict)
   - DividendData (symbol, fiscal_year, 배당 관련 필드들)
```

**검증:**
- [ ] `from cloud_server.data.provider import DataProvider, DailyBar` import 성공
- [ ] DataProvider를 직접 인스턴스화하면 TypeError (ABC)
- [ ] 빈 서브클래스(name+capabilities만 구현)가 인스턴스화 가능

---

### Step 2 — DB 모델 확장

**목표**: StockMaster에 corp_code 추가, 재무/배당 테이블 신설

**파일:**
- `cloud_server/models/market.py` (수정 — corp_code 컬럼 추가)
- `cloud_server/models/fundamental.py` (신규)
- `cloud_server/models/__init__.py` (수정 — 신규 모델 export)

**구현 내용:**
```
1. StockMaster에 corp_code 컬럼 추가
   - corp_code = Column(String(10), nullable=True)  # DART 기업 고유번호
   - Index("idx_stock_corp_code", "corp_code")

2. CompanyFinancial 모델 (spec §6.3)
   - id PK, corp_code, period, 재무 지표들 (revenue~debt_ratio)
   - provider (str), collected_at (datetime)
   - UniqueConstraint("corp_code", "period", "provider")

3. CompanyDividend 모델 (spec §6.3)
   - id PK, symbol, fiscal_year, 배당 지표들
   - provider (str), collected_at (datetime)
   - UniqueConstraint("symbol", "fiscal_year", "provider")

4. DB 마이그레이션 절차
   - 신규 테이블: create_all()이 자동 생성 (fundamental.py를 models/__init__.py에서 import)
   - 기존 테이블 컬럼 추가: create_all()은 기존 테이블에 컬럼을 추가하지 못함
   - SQLite(개발): ALTER TABLE stock_master ADD COLUMN corp_code VARCHAR(10) 수동 실행
     또는 DB 파일 삭제 후 재생성 (개발 데이터 소실 허용)
   - PostgreSQL(운영): Alembic 마이그레이션 스크립트 작성
   - init_db()에서 fundamental 모델 import 추가
```

**검증:**
- [ ] 서버 시작 시 `company_financials`, `company_dividends` 테이블 생성
- [ ] StockMaster에 corp_code 컬럼 존재 (NULL 허용, 기존 데이터 영향 없음)

---

### Step 3 — YFinanceProvider

**목표**: 기존 YFinanceService를 DataProvider 인터페이스로 래핑

**파일:**
- `cloud_server/data/yfinance_provider.py` (신규)

**구현 내용:**
```
1. YFinanceProvider(DataProvider) 구현
   - name = "yfinance"
   - capabilities() → {"price", "quote", "dividends"}

2. get_daily_bars(symbol, start, end)
   - 심볼 변환: 6자리 숫자 → .KS/.KQ (StockMaster.market 참조)
   - yfinance.download() 호출 (sync) → asyncio.to_thread()로 래핑
   - DataFrame → list[DailyBar] 변환
   - 기존 YFinanceService.fetch_daily() 로직 재사용 (직접 호출 또는 로직 이동)

3. get_quote(symbol)
   - yfinance.Ticker(symbol).fast_info 사용 → asyncio.to_thread()로 래핑
   - ProviderQuote 반환 (15~20분 지연 데이터)

4. get_dividends(symbol, year)
   - yfinance.Ticker(symbol).dividends 사용 → asyncio.to_thread()로 래핑
   - list[DividendData] 반환

5. supports_symbol(symbol)
   - 6자리 숫자(한국) 또는 알파벳(미국) → True
```

**검증:**
- [ ] `YFinanceProvider().get_daily_bars("005930", ...)` → 삼성전자 일봉 반환
- [ ] `YFinanceProvider().get_quote("005930")` → ProviderQuote 반환
- [ ] `YFinanceProvider().get_dividends("005930")` → 배당 이력 반환
- [ ] `YFinanceProvider().capabilities()` → `{"price", "quote", "dividends"}`

---

### Step 4 — DartProvider (corp_code 매핑 + 재무)

**목표**: DART OpenAPI 연동 — 기업 고유번호 매핑, 재무제표, 배당

**파일:**
- `cloud_server/data/dart_provider.py` (신규)

**구현 내용:**
```
1. DartProvider(DataProvider) 구현
   - name = "dart"
   - capabilities() → {"financials", "dividends", "disclosure"}
   - __init__(api_key: str)

2. corp_code 매핑 유틸리티 (같은 파일 내부)
   - fetch_corp_codes() → dict[stock_code, corp_code]
     DART 고유번호 API → ZIP 다운로드 → XML 파싱 → {stock_code: corp_code} dict
   - backfill_corp_codes(db)
     StockMaster에서 corp_code=NULL인 종목 찾아 매핑
   - 이 Step에서 초기 backfill 1회 실행 (Step 6 API가 corp_code에 의존)

3. get_financials(corp_code, year, quarter)
   - DART DS003 API 호출 (단일회사 주요 재무지표)
   - JSON → FinancialData 변환
   - 호출: GET https://opendart.fss.or.kr/api/fnlttSinglAcnt.json
     params: crtfc_key, corp_code, bsns_year, reprt_code

4. get_dividends(symbol, year)
   - symbol → corp_code 변환 (DB 조회)
   - DART DS002 API 호출 (배당에 관한 사항)
   - JSON → list[DividendData] 변환

5. HTTP 호출
   - httpx.AsyncClient 사용 (기존 cloud_server 의존성 확인)
   - 타임아웃 10초
   - Rate limit: 분당 1000건 (현재 규모에서 문제 없음, 제한 로직 불필요)
```

**검증:**
- [ ] `fetch_corp_codes()` → 2000+ 기업 매핑 dict 반환
- [ ] 초기 backfill 실행 후 StockMaster.corp_code에 값 채워짐
- [ ] `DartProvider(key).get_financials("00126380", 2024)` → 삼성전자 재무 반환
- [ ] `DartProvider(key).get_dividends("005930", 2024)` → 배당 데이터 반환
- [ ] API 키 오류 시 예외 발생 (조용히 삼키지 않음)

---

### Step 5 — DataAggregator

**목표**: 복수 프로바이더 우선순위 라우팅 + 에러 처리

**파일:**
- `cloud_server/data/aggregator.py` (신규)

**구현 내용:**
```
1. DataAggregator 구현 (spec §4 그대로)
   - __init__(providers: list[DataProvider])
   - get_daily_bars(symbol, start, end, preferred) → list[DailyBar]
   - get_quote(symbol, preferred) → ProviderQuote | None
   - get_financials(corp_code, year, quarter) → FinancialData | None
   - get_dividends(symbol, year) → list[DividendData]
   - _resolve_order(symbol, preferred) → list[str]

2. 에러 처리 정책 (spec §4 에러 처리 정책)
   - asyncio.wait_for(call, timeout=10) per provider
   - 실패 시 logger.warning + 다음 프로바이더로 폴백
   - 전체 실패 시 빈 값 반환 + logger.error
   - capabilities 미스매치 → 건너뜀

3. 앱 초기화 함수
   - create_aggregator() → DataAggregator
     .env에서 키 로드, 가용 프로바이더만 등록
     등록 순서: dart (DART_API_KEY 있으면) → yfinance (항상)
     이유: dart에 "price" capability 없으므로 가격 조회에 영향 없고,
           배당은 dart(정본) 우선으로 조회됨 (spec §4 기본 우선순위와 일치)
```

**검증:**
- [ ] 프로바이더 1개 실패 시 다음으로 폴백
- [ ] capabilities 없는 프로바이더에 요청 시 건너뜀
- [ ] 타임아웃(10초) 초과 시 다음 프로바이더로 전환
- [ ] 전체 실패 시 빈 값 반환 + error 로그

---

### Step 6 — REST API

**목표**: 가격/재무/배당 엔드포인트 추가

**파일:**
- `cloud_server/api/market_data.py` (신규)
- `cloud_server/main.py` (수정 — 라우터 등록)

**구현 내용:**
```
1. GET /api/v1/stocks/{symbol}/bars
   - query: start (date), end (date), interval (str, 기본 "daily")
   - DB 캐시 먼저 확인 (MarketRepository.get_daily_bars)
   - 캐시 미스 → aggregator.get_daily_bars() → DB 저장 → 반환
   - 응답: { success, data: [{date, open, high, low, close, volume}], count }

2. GET /api/v1/stocks/{symbol}/quote
   - DB 최신 종가 or aggregator.get_quote()
   - 응답: { success, data: {price, change, change_pct, volume, timestamp} }

3. GET /api/v1/stocks/{symbol}/financials
   - query: year (int), quarter (int, optional)
   - DB 캐시 → aggregator.get_financials()
   - symbol → corp_code 변환 (StockMaster)
   - 응답: { success, data: {period, revenue, ..., per, pbr, roe} }

4. GET /api/v1/stocks/{symbol}/dividends
   - query: year (int, optional)
   - DB 캐시 → aggregator.get_dividends()
   - 응답: { success, data: [{fiscal_year, dividend_per_share, ...}], count }

5. 인증: current_user 의존성 (기존 stocks.py와 동일)
```

**검증:**
- [ ] `/stocks/005930/bars?start=2025-01-01&end=2025-12-31` → 일봉 반환
- [ ] `/stocks/005930/quote` → 현재가(지연) 반환
- [ ] `/stocks/005930/financials?year=2024` → 재무 데이터 반환
- [ ] `/stocks/005930/dividends` → 배당 이력 반환
- [ ] 미인증 요청 → 401

---

### Step 7 — 스케줄러 통합 + corp_code 주기적 갱신

**목표**: 기존 스케줄러를 DataAggregator로 전환, corp_code 주기적 갱신 등록

**파일:**
- `cloud_server/collector/scheduler.py` (수정)

**구현 내용:**
```
1. save_daily_bars() 수정
   - 변경 전: self.collect_yfinance() 직접 호출
   - 변경 후: aggregator.get_daily_bars() 사용
   - 수집 대상: StockMaster에서 is_active=True인 종목 (또는 관심종목 우선)

2. corp_code 주기적 갱신 작업 등록
   - 초기 backfill은 Step 4에서 완료됨
   - 스케줄러에는 주 1회 갱신만 등록 (신규 상장 종목 대응)
   - 시점: stock_master 갱신(08:00) 직후, 월요일만

3. 분기별 재무 수집 작업 추가 (선택)
   - 시점: 분기 실적 발표 시즌 (4/5/8/11월)
   - 전 종목 재무 수집은 과도 → 관심종목 위주

4. collect_yfinance() 유지
   - 지수/환율 6종목은 기존 방식 유지 (DataProvider 대상이 아님)
```

**검증:**
- [ ] save_daily_bars()가 DataAggregator 경유로 동작
- [ ] 주기적 corp_code 갱신 스케줄 등록 확인
- [ ] 기존 지수/환율 수집 영향 없음

---

### Step 8 — KISProvider (spec Step 2)

**목표**: KIS REST API를 DataProvider로 래핑 — 정확한 한국 주식 가격

**파일:**
- `cloud_server/data/kis_provider.py` (신규)

**구현 내용:**
```
1. KISProvider(DataProvider) 구현
   - name = "kis"
   - capabilities() → {"price", "quote"}
   - __init__(app_key: str, app_secret: str)

2. get_daily_bars(symbol, start, end)
   - KIS 국내주식기간별시세 API 호출
   - 100거래일 제한 → 기간 분할 요청
   - JSON → list[DailyBar] 변환

3. get_quote(symbol)
   - KIS 현재가 시세 API 호출
   - ProviderQuote 반환

4. supports_symbol(symbol)
   - 6자리 숫자만 지원 (한국 주식)

5. 인증
   - OAuth 토큰 발급/갱신 (기존 local_server/broker/kis/auth.py 로직 참고)
   - 서비스 키 사용 (유저 키 아님)
```

**전제조건:**
- KIS API 서비스 키 발급 필요 (현재 미등록)
- 서비스 키 없으면 Aggregator에서 자동 건너뜀

**검증:**
- [ ] 서비스 키 있을 때: `KISProvider(key, secret).get_daily_bars("005930", ...)` → 일봉 반환
- [ ] 서비스 키 없을 때: Aggregator가 yfinance로 폴백
- [ ] 100거래일 초과 기간 → 분할 요청 정상 동작

---

### Step 9 — KiwoomProvider (spec Step 2)

**목표**: 키움 REST API를 DataProvider로 래핑 — KIS 대안/보조

**파일:**
- `cloud_server/data/kiwoom_provider.py` (신규)

**구현 내용:**
```
1. KiwoomProvider(DataProvider) 구현
   - name = "kiwoom"
   - capabilities() → {"price", "quote"}
   - __init__(app_key: str, app_secret: str)

2. get_daily_bars(symbol, start, end)
   - 키움 일봉 API (POST, api-id 헤더 방식)
   - JSON → list[DailyBar] 변환

3. get_quote(symbol)
   - 키움 현재가 API 호출
   - ProviderQuote 반환

4. supports_symbol(symbol)
   - 6자리 숫자만 지원

5. 인증
   - 키움 OAuth (기존 local_server/broker/kiwoom/auth.py 로직 참고)
   - 5 CPS 제한 주의
```

**전제조건:**
- 키움 API 서비스 키 발급 필요 (현재 미등록)

**검증:**
- [ ] 서비스 키 있을 때: `KiwoomProvider(key, secret).get_daily_bars("005930", ...)` → 일봉 반환
- [ ] Aggregator 우선순위: kis → kiwoom → yfinance 순 폴백

---

### Step 10 — 레거시 제거 (spec Step 3)

**목표**: backend/ 가격 관련 코드 제거, 프론트엔드 클라우드 API 전환

**파일:**
- `frontend/src/services/api.ts` (수정 — 레거시 가격 API 호출 제거)
- `frontend/src/pages/StockDetail.tsx` (수정 — cloud API 전환)
- `backend/app/services/data_ingestion.py` (삭제 대상)
- `backend/app/api/stocks.py` (삭제 대상)

**구현 내용:**
```
1. 프론트엔드 전환
   - StockDetail.tsx: localhost:8000 → cloud_server:4010 API
   - api.ts: 레거시 가격 API 함수 제거
   - cloudClient: /stocks/{symbol}/bars, /quote, /financials, /dividends 호출

2. 레거시 백엔드 가격 코드 제거
   - data_ingestion.py (yfinance 직접 호출 서비스)
   - stocks.py 가격 관련 엔드포인트
   - 관련 import 정리

3. 제거 전 확인
   - 프론트엔드가 cloud API만 사용하는지 검증
   - backend/의 다른 기능(가상 거래, ML 등)에 영향 없는지 확인
```

**전제조건:**
- Step 6 (REST API) 완료 + 프론트엔드에서 정상 동작 확인 후 진행

**검증:**
- [ ] 프론트엔드 StockDetail 페이지에서 차트/재무/배당 정상 표시
- [ ] backend/:8000 가격 API 호출 0건 (네트워크 탭 확인)
- [ ] backend/ 서버 없이 프론트엔드 가격 기능 동작

---

## 2. 의존성 & 순서

```
Step 1 (ABC)
  ↓
Step 2 (DB 모델)   ← Step 1과 병렬 가능하나 순서대로 진행
  ↓
Step 3 (YFinance)  ← Step 1 의존
  ↓
Step 4 (DART)      ← Step 1, Step 2 의존 (corp_code 매핑에 StockMaster 필요)
  ↓
Step 5 (Aggregator) ← Step 3, Step 4 의존
  ↓
Step 6 (API)       ← Step 5 의존
  ↓
Step 7 (스케줄러)   ← Step 5, Step 6 의존
  ↓
Step 8 (KIS)       ← Step 5 의존 + 서비스 키 필요
Step 9 (키움)      ← Step 5 의존 + 서비스 키 필요
  ↓               (8, 9는 병렬 가능, 키 없으면 보류)
Step 10 (레거시)   ← Step 6 완료 + 프론트엔드 검증 후
```

## 3. 파일 변경 요약

| 파일 | 변경 | Step |
|------|------|------|
| `cloud_server/data/__init__.py` | 신규 | 1 |
| `cloud_server/data/provider.py` | 신규 | 1 |
| `cloud_server/data/yfinance_provider.py` | 신규 | 3 |
| `cloud_server/data/dart_provider.py` | 신규 | 4 |
| `cloud_server/data/aggregator.py` | 신규 | 5 |
| `cloud_server/data/kis_provider.py` | 신규 | 8 |
| `cloud_server/data/kiwoom_provider.py` | 신규 | 9 |
| `cloud_server/models/market.py` | 수정 (corp_code) | 2 |
| `cloud_server/models/fundamental.py` | 신규 | 2 |
| `cloud_server/models/__init__.py` | 수정 | 2 |
| `cloud_server/api/market_data.py` | 신규 | 6 |
| `cloud_server/main.py` | 수정 (라우터) | 6 |
| `cloud_server/collector/scheduler.py` | 수정 | 7 |
| `frontend/src/pages/StockDetail.tsx` | 수정 | 10 |
| `frontend/src/services/api.ts` | 수정 | 10 |
| `backend/app/services/data_ingestion.py` | 삭제 | 10 |
| `backend/app/api/stocks.py` | 삭제 | 10 |

**신규 9파일, 수정 6파일, 삭제 2파일**

## 4. 미결 사항

- [ ] httpx 의존성 추가 필요 여부 (DART HTTP 호출용) — requirements.txt 확인
- [ ] 개별 종목 일봉 on-demand 수집 시 rate limit 고려 (yfinance ~2000/h)
- [ ] KIS/키움 서비스 키 미등록 — Step 8~9는 키 발급 후 진행
- [ ] backend/ 레거시 제거 범위 정밀 확인 — 가격 외 기능(가상 거래, ML)과의 의존성
