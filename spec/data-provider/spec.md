# DataProvider 명세서

> 작성일: 2026-03-07 | 상태: 구현 완료

---

## 1. 개요

### 배경

Phase 1-2 레거시 백엔드(`backend/`)는 yfinance를 on-demand로 호출하여 개별 종목 가격 차트를 제공한다.
Phase 3 클라우드 서버(`cloud_server/`)는 종목 **메타데이터**(공공데이터포털)와 **지수/환율**(yfinance 6종목)만 수집하며,
개별 종목 가격 데이터는 수집하지 않는다.

이 갭을 메우고, 레거시 백엔드를 점진적으로 흡수하기 위해
**DataProvider** 추상화를 도입한다.

### 목표

- 확장 가능한 시장 데이터 수집 인터페이스 정의 (ABC)
- 가격(OHLCV) + 재무제표 + 배당 등 구조화된 수치 데이터를 통합 관리
- yfinance, KIS, 키움, DART 등 복수 데이터 소스 지원
- BrokerAdapter(주문 실행)와 명확히 분리
- 레거시 `backend/` 가격 데이터 기능을 클라우드 서버로 이관

### BrokerAdapter와의 관계

| | DataProvider | BrokerAdapter |
|--|-------------|---------------|
| **역할** | 시장 데이터 수집 (가격, 재무, 배당 등) | 실시간 시세 + 주문 실행 |
| **메서드** | `get_daily_bars`, `get_quote`, `get_financials`, `get_dividends` | `place_order`, `subscribe_quotes`, `get_balance` |
| **호출 주체** | 클라우드 서버 (스케줄러/API) | 로컬 서버 (전략 엔진) |
| **키** | 서비스 키 또는 키 불필요 | 유저 키 |

```
DataProvider (ABC)              BrokerAdapter (ABC)
  읽기 전용, 구조화된 수치 데이터    실시간 + 주문
  ├─ YFinanceProvider            ├─ KiwoomAdapter
  ├─ KISProvider ─────────┐      ├─ KISAdapter ──────┐
  ├─ KiwoomProvider ──┐   │      └─ ...              │
  │                   │   │                           │
  │                   └───┴── 같은 증권사 API 사용 ───┘
  │                           (구현 공유 가능)
  └─ DartProvider (재무/공시 전용)
```

- KIS/키움: DataProvider + BrokerAdapter 양쪽 역할
- yfinance: 가격 + 배당 (주문 불가)
- DART: 재무/배당/공시 전용 (가격 없음)

---

## 2. DataProvider ABC

```python
# cloud_server/data/provider.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional


@dataclass
class DailyBar:
    """일봉 데이터 한 건."""
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class ProviderQuote:
    """현재가 스냅샷 (REST 단건 조회용)."""
    symbol: str
    price: float
    change: float        # 전일 대비
    change_pct: float    # 전일 대비 (%)
    volume: int
    timestamp: str       # ISO 8601


@dataclass
class FinancialData:
    """재무 데이터."""
    corp_code: str            # DART 기업 고유번호
    symbol: str               # 대표 종목 코드
    period: str               # "2025Q4", "2025"
    revenue: int | None       # 매출액
    operating_income: int | None  # 영업이익
    net_income: int | None    # 당기순이익
    total_assets: int | None  # 총자산
    total_equity: int | None  # 자본총계
    total_debt: int | None    # 부채총계
    eps: float | None         # 주당순이익
    per: float | None
    pbr: float | None
    roe: float | None
    debt_ratio: float | None  # 부채비율
    extra: dict = field(default_factory=dict)  # 소스별 추가 필드


@dataclass
class DividendData:
    """배당 데이터."""
    symbol: str
    fiscal_year: str          # "2025"
    dividend_per_share: float # 주당 배당금
    dividend_yield: float | None
    ex_date: date | None      # 배당락일
    pay_date: date | None     # 지급일
    payout_ratio: float | None


class DataProvider(ABC):
    """시장 데이터 제공자 추상 기반 클래스.

    읽기 전용. 각 프로바이더는 자기가 지원하는 기능만 오버라이드한다.
    기본 구현은 빈 값(None/[])을 반환하므로 미지원 메서드를 구현할 의무 없음.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """프로바이더 식별자 (예: "yfinance", "kis", "dart")."""

    @abstractmethod
    def capabilities(self) -> set[str]:
        """이 프로바이더가 지원하는 기능 목록.

        가능한 값: "price", "quote", "financials", "dividends", "disclosure"
        Aggregator가 적절한 프로바이더를 선택하는 데 사용.
        """

    # ── 가격 (price) ──────────────────────────────

    async def get_daily_bars(
        self,
        symbol: str,
        start: date,
        end: date,
    ) -> list[DailyBar]:
        """일봉 OHLCV를 조회한다."""
        return []

    async def get_quote(self, symbol: str) -> Optional[ProviderQuote]:
        """지연 시세를 단건 조회한다 (REST, 캐시/종가 기반).

        실시간 시세 중계가 아님. 종목 상세/AI 분석 입력용.
        """
        return None

    # ── 재무 (financials) ─────────────────────────

    async def get_financials(
        self,
        corp_code: str,
        year: int,
        quarter: int | None = None,
    ) -> FinancialData | None:
        """재무제표 요약을 조회한다.

        Args:
            corp_code: DART 기업 고유번호 (예: "00126380")
            year: 사업연도
            quarter: 분기 (1~4). None이면 연간.
        """
        return None

    # ── 배당 (dividends) ──────────────────────────

    async def get_dividends(
        self,
        symbol: str,
        year: int | None = None,
    ) -> list[DividendData]:
        """배당 이력을 조회한다."""
        return []

    # ── 공통 ──────────────────────────────────────

    async def supports_symbol(self, symbol: str) -> bool:
        """해당 종목을 지원하는지 확인한다."""
        return True
```

### 설계 원칙

1. **capabilities 패턴**: 필수 메서드 없음. 모든 메서드에 기본 구현(빈 값). 각 프로바이더는 `capabilities()`로 지원 범위 선언, 해당 메서드만 오버라이드
2. **읽기 전용**: 쓰기(주문)는 BrokerAdapter에서 처리
3. **async**: 네트워크 I/O 기반이므로 async 필수
4. **종목 vs 기업**: 가격은 `symbol`(종목 코드), 재무는 `corp_code`(기업 고유번호)로 구분
5. **심볼 포맷**: 내부 통일 코드(6자리, 예: "005930"). 프로바이더 내부에서 변환

### 데이터 주체

```
종목 (symbol)              기업 (corp_code)
  가격 OHLCV                 재무제표
  현재가/호가                 배당 (기업 단위)
  거래량                     공시
                            지분 변동

StockMaster.corp_code → 종목 ↔ 기업 매핑
```

- 한 기업에 여러 종목 가능 (보통주 005930 + 우선주 005935)
- DART `고유번호` API가 corp_code ↔ stock_code 매핑 제공

---

## 3. 프로바이더 구현

### 3.1 YFinanceProvider

| 항목 | 값 |
|------|---|
| 소스 | Yahoo Finance (yfinance 라이브러리) |
| 비용 | 무료 |
| 지원 | 한국 (.KS/.KQ) + 미국 + 글로벌 |
| capabilities | `{"price", "quote", "dividends"}` |
| Rate Limit | ~2000 호출/시간 (비공식) |

**역할**: 과거 가격 데이터 + 배당. 레거시 `backend/` 대체.

**소스 성격**: 한국 주식에서는 **편의/폴백 소스**. KIS/키움 서비스 키 미등록 시 임시 1차 소스로 사용하되, 키 확보 후 보조로 전환. 한국 주식 재무 데이터는 폴백으로도 사용 금지 (대형주만 부분 지원, 신뢰도 부족). 글로벌 지수/환율/해외 주식에서는 1차 소스로 사용 가능. 정본 정책: `docs/research/source-of-truth-policy.md` 참조.

```python
class YFinanceProvider(DataProvider):
    name = "yfinance"
    def capabilities(self): return {"price", "quote", "dividends"}

    async def get_daily_bars(self, symbol, start, end): ...
    async def get_quote(self, symbol): ...
    async def get_dividends(self, symbol, year=None): ...
    # get_financials → 미구현 (한국 재무 폴백 금지, DART가 유일한 정본)
```

**심볼 변환 규칙**:
- 6자리 숫자 → KOSPI: `.KS`, KOSDAQ: `.KQ` (StockMaster의 market 필드로 판단)
- 알파벳 → 미국 주식, 그대로 전달
- `^` 접두어 → 지수 (기존 yfinance_service.py와 동일)

### 3.2 KISProvider

| 항목 | 값 |
|------|---|
| 소스 | 한국투자증권 REST API |
| 비용 | 무료 (API 신청 필요) |
| 지원 | 한국 주식 |
| capabilities | `{"price", "quote"}` |
| Rate Limit | ~20 req/sec |

**역할**: 정확한 한국 주식 당일/과거 데이터. 서비스 키로 클라우드에서 수집.

```python
class KISProvider(DataProvider):
    name = "kis"
    def capabilities(self): return {"price", "quote"}

    def __init__(self, app_key: str, app_secret: str): ...
    async def get_daily_bars(self, symbol, start, end): ...
    async def get_quote(self, symbol): ...
    async def supports_symbol(self, symbol):
        return symbol.isdigit() and len(symbol) == 6
```

### 3.3 KiwoomProvider

| 항목 | 값 |
|------|---|
| 소스 | 키움증권 REST API |
| 비용 | 무료 (API 신청 필요) |
| 지원 | 한국 주식 |
| capabilities | `{"price", "quote"}` |
| Rate Limit | 5 req/sec (POST만) |

**역할**: KIS 대안/보조. 서비스 키로 클라우드에서 수집.

```python
class KiwoomProvider(DataProvider):
    name = "kiwoom"
    def capabilities(self): return {"price", "quote"}

    def __init__(self, app_key: str, app_secret: str): ...
    async def get_daily_bars(self, symbol, start, end): ...
    async def get_quote(self, symbol): ...
    async def supports_symbol(self, symbol):
        return symbol.isdigit() and len(symbol) == 6
```

### 3.4 DartProvider

| 항목 | 값 |
|------|---|
| 소스 | DART OpenAPI (금융감독원 전자공시) |
| 비용 | 무료 (API 키 발급, `.env` DART_API_KEY) |
| 지원 | 한국 상장사 |
| capabilities | `{"financials", "dividends", "disclosure"}` |
| Rate Limit | 분당 1000건 |

**역할**: 한국 재무 데이터의 정본. 재무제표, 배당, 공시 전담.

```python
class DartProvider(DataProvider):
    name = "dart"
    def capabilities(self): return {"financials", "dividends", "disclosure"}

    def __init__(self, api_key: str): ...

    async def get_financials(self, corp_code, year, quarter=None):
        # DS003: 단일회사 주요 재무지표 API
        # → FinancialData 반환
        ...

    async def get_dividends(self, symbol, year=None):
        # DS002: 배당에 관한 사항 API
        # symbol → corp_code 변환 (StockMaster.corp_code)
        # → list[DividendData] 반환
        ...

    # get_daily_bars, get_quote → 미구현 (가격 데이터 없음)
```

**DART API 사용 범위**:

| API 그룹 | 용도 | 우선순위 |
|---------|------|---------|
| DS003 — 단일회사 주요 재무지표 | PER, PBR, ROE, EPS | P0 |
| DS003 — 단일회사 전체 재무제표 | 손익/재무상태표/현금흐름 | P0 |
| DS002 — 배당에 관한 사항 | 배당금, 배당수익률 | P0 |
| DS001 — 공시검색 | 공시 이벤트 수집 | P1 |
| DS001 — 고유번호 | corp_code ↔ stock_code 매핑 | P0 (초기 셋업) |
| DS004 — 대량보유/임원 지분 | 수급 분석 | P2 |
| DS002 — 최대주주/임원 현황 | 지배구조 분석 | P2 |

### 3.5 향후 확장 예시

새 데이터 소스 추가 시 `DataProvider`만 구현하고 `capabilities()` 선언:

```python
class KRXProvider(DataProvider):
    """한국거래소 공공 API — 종가 기준 일봉 + 투자자별 매매동향."""
    name = "krx"
    def capabilities(self): return {"price"}

class ECOSProvider(DataProvider):
    """한국은행 ECOS — 금리, 환율, GDP 등 거시경제."""
    name = "ecos"
    def capabilities(self): return {"macro"}
```

---

## 4. DataAggregator

복수 DataProvider를 관리하고, 우선순위/폴백 로직을 제공하는 오케스트레이터.

```python
# cloud_server/data/aggregator.py

class DataAggregator:
    """복수 DataProvider를 우선순위 기반으로 조회한다."""

    def __init__(self, providers: list[DataProvider]):
        self._providers = {p.name: p for p in providers}
        # 우선순위: 등록 순서 (앞이 높음)
        self._priority = [p.name for p in providers]

    async def get_daily_bars(
        self,
        symbol: str,
        start: date,
        end: date,
        preferred: str | None = None,
    ) -> list[DailyBar]:
        """우선순위에 따라 일봉을 조회한다.

        preferred가 지정되면 해당 프로바이더 우선 시도.
        실패 시 다음 프로바이더로 폴백.
        """
        order = self._resolve_order(symbol, preferred)
        for name in order:
            provider = self._providers[name]
            if not await provider.supports_symbol(symbol):
                continue
            bars = await provider.get_daily_bars(symbol, start, end)
            if bars:
                return bars
        return []

    async def get_quote(
        self,
        symbol: str,
        preferred: str | None = None,
    ) -> ProviderQuote | None:
        """우선순위에 따라 현재가를 조회한다."""
        order = self._resolve_order(symbol, preferred)
        for name in order:
            provider = self._providers[name]
            if not await provider.supports_symbol(symbol):
                continue
            quote = await provider.get_quote(symbol)
            if quote:
                return quote
        return None

    async def get_financials(self, corp_code, year, quarter=None):
        """재무 데이터를 조회한다 (financials capability 가진 프로바이더)."""
        for name in self._priority:
            p = self._providers[name]
            if "financials" not in p.capabilities():
                continue
            result = await p.get_financials(corp_code, year, quarter)
            if result:
                return result
        return None

    async def get_dividends(self, symbol, year=None):
        """배당 데이터를 조회한다 (dividends capability 가진 프로바이더)."""
        for name in self._priority:
            p = self._providers[name]
            if "dividends" not in p.capabilities():
                continue
            result = await p.get_dividends(symbol, year)
            if result:
                return result
        return []

    def _resolve_order(self, symbol: str, preferred: str | None) -> list[str]:
        if preferred and preferred in self._providers:
            rest = [n for n in self._priority if n != preferred]
            return [preferred] + rest
        return list(self._priority)
```

### 기본 우선순위

```
가격: kis / kiwoom → yfinance (폴백)
재무: dart (유일한 한국 정본)
배당: dart → yfinance (보조)
```

서비스 키가 미등록이면 해당 프로바이더는 건너뛰고 다음으로 폴백.

### 에러 처리 정책

- **타임아웃**: 프로바이더별 요청 타임아웃 10초. 초과 시 다음으로 폴백
- **에러 로깅**: 프로바이더 실패 시 `logger.warning(provider=name, error=e, symbol=symbol)`. 조용히 삼키지 않음
- **응답 소스 기록**: Aggregator 반환값에 어떤 프로바이더가 응답했는지 로그 (디버깅/모니터링용)
- **capabilities 미스매치**: Aggregator가 capabilities 없는 프로바이더에 요청 시 건너뜀 + warning 로그
- **전체 실패**: 모든 프로바이더 실패 시 빈 값 반환 + `logger.error`. 호출부에서 캐시 사용 여부 결정
- **stale 캐시**: DB에 이전 수집 데이터가 있으면 fallback으로 사용 가능. 캐시 나이(collected_at)를 응답에 포함하여 호출부가 판단

---

## 5. 통합 지점

### 5.1 클라우드 서버 — 스케줄러

`cloud_server/collector/scheduler.py`에 이미 일봉 수집 구조가 존재:

```python
# 기존 스케줄러 작업
# - stock_master: 공공데이터포털 (08:00)
# - save_daily_bars: 16:00 (현재 yfinance 폴백)
# - collect_yfinance: 17:00 (지수/환율 6종목)
# - check_data_integrity: 18:00 (누락 거래일 감지)

# 변경: save_daily_bars()가 DataAggregator를 사용하도록 전환
# - 기존: YFinanceService.fetch_recent() 직접 호출
# - 변경 후: aggregator.get_daily_bars() → 우선순위 기반 수집
```

### 5.2 클라우드 서버 — REST API

레거시 `backend/` 가격 API를 대체하는 엔드포인트:

```
GET /api/v1/stocks/{symbol}/bars?start=&end=&interval=daily
  → aggregator.get_daily_bars() → 캐시 히트면 DB, 미스면 on-demand 수집

GET /api/v1/stocks/{symbol}/quote
  → aggregator.get_quote()
  → 지연 시세 (캐시/종가 기반). 실시간 시세 중계 아님.
  → 용도: 종목 상세 페이지의 최근가 표시, AI 분석 입력
  → 실시간 시세는 로컬 서버 → BrokerAdapter(유저 키) → WS
```

### 5.3 프론트엔드 마이그레이션

현재 `StockDetail.tsx`는 레거시 `api.ts` → `backend/:8000`으로 가격 차트를 요청한다.
DataProvider API가 준비되면:

```
변경 전: stockApi.getStockPrices(symbol) → localhost:8000/api/v1/stocks/{symbol}/prices
변경 후: cloudClient.get(`/stocks/{symbol}/bars`) → cloud_server:4010/api/v1/stocks/{symbol}/bars
```

### 5.4 로컬 서버

로컬 서버는 DataProvider를 직접 사용하지 않는다.
- 실시간 시세: BrokerAdapter.subscribe_quotes (유저 키, WS)
- 주문 전 가격 확인: BrokerAdapter.get_quote (유저 키, REST)

---

## 6. DB 모델

### 6.1 기존 모델 (가격)

`cloud_server/models/market.py`에 이미 정의:

```python
class StockMaster(Base):     # 종목 메타 (symbol PK)
class DailyBar(Base):        # 일봉 OHLCV (symbol + date unique)
class MinuteBar(Base):       # 분봉 (symbol + timestamp unique)
```

`cloud_server/services/market_repository.py`에 CRUD 구현 완료.

### 6.2 StockMaster 확장 (corp_code 추가)

```python
# cloud_server/models/market.py — StockMaster에 컬럼 추가

class StockMaster(Base):
    symbol: str              # PK (종목 코드)
    name: str
    market: str | None
    sector: str | None
    corp_code: str | None    # ← 신규: DART 기업 고유번호
    is_active: bool
    updated_at: datetime
```

### corp_code 매핑 전략

**초기 backfill**:
1. DART `고유번호` API → ZIP 파일 다운로드 (전체 기업 목록, corp_code ↔ stock_code)
2. StockMaster의 symbol과 DART stock_code 매칭 → corp_code 컬럼 채움
3. 매칭 실패(DART에 없는 종목)는 corp_code = NULL 유지

**주기적 갱신**:
- StockMaster 갱신 (08:00 공공데이터포털) 시 신규 종목에 대해 DART 매핑 재시도
- 주기: 주 1회 (종목 변동이 적으므로)

**충돌 규칙**:
- DART corp_code가 정본 — 공공데이터포털과 불일치 시 DART 우선
- 한 corp_code에 여러 symbol 가능 (보통주 + 우선주) — 정상
- 한 symbol에 여러 corp_code → 데이터 오류, 로그 경고 후 기존 값 유지

### 6.3 신규 모델 (재무/배당)

```python
# cloud_server/models/fundamental.py (신규)

class CompanyFinancial(Base):
    __tablename__ = "company_financials"
    id: int                      # PK
    corp_code: str               # DART 기업 고유번호 (인덱스)
    period: str                  # "2025", "2025Q4"
    revenue: BigInteger | None   # 매출액
    operating_income: BigInteger | None
    net_income: BigInteger | None
    total_assets: BigInteger | None
    total_equity: BigInteger | None
    total_debt: BigInteger | None
    eps: float | None
    per: float | None
    pbr: float | None
    roe: float | None
    debt_ratio: float | None
    provider: str                # "dart", "yfinance"
    collected_at: datetime
    # unique: (corp_code, period, provider)

class CompanyDividend(Base):
    __tablename__ = "company_dividends"
    id: int                      # PK
    symbol: str                  # 종목 코드
    fiscal_year: str             # "2025"
    dividend_per_share: float
    dividend_yield: float | None
    ex_date: date | None
    pay_date: date | None
    payout_ratio: float | None
    provider: str
    collected_at: datetime
    # unique: (symbol, fiscal_year, provider)
```

---

## 7. 파일 구조

```
cloud_server/
  data/                     # 신규 패키지
    __init__.py
    provider.py             # DataProvider ABC, 데이터 클래스
    aggregator.py           # DataAggregator (capabilities 기반 라우팅)
    yfinance_provider.py    # YFinanceProvider  {price, quote, dividends}
    kis_provider.py         # KISProvider       {price, quote}
    kiwoom_provider.py      # KiwoomProvider    {price, quote}
    dart_provider.py        # DartProvider      {financials, dividends, disclosure}
  models/
    market.py               # DailyBar, MinuteBar, StockMaster+corp_code (기존+확장)
    fundamental.py          # CompanyFinancial, CompanyDividend (신규)
  services/
    market_repository.py    # 가격 DB CRUD (기존)
    yfinance_service.py     # 지수/환율 수집 (기존, DataProvider와 별도 유지)
  collector/
    scheduler.py            # 스케줄러 (기존, DataProvider 호출 추가)
  api/
    market_data.py          # /bars, /quote, /financials, /dividends (신규, 단일 파일)
```

---

## 8. 마이그레이션 계획

### Step 1: ABC + YFinanceProvider + DartProvider
- `DataProvider` ABC 정의 (capabilities 패턴)
- `YFinanceProvider` 구현 (가격 + 배당)
- `DartProvider` 구현 (재무 + 배당 + corp_code 매핑)
- StockMaster에 `corp_code` 컬럼 추가
- `CompanyFinancial`, `CompanyDividend` DB 모델
- `/stocks/{symbol}/bars`, `/financials`, `/dividends` API
- 프론트엔드 전환은 Step 3으로 이동 (API 검증 후)

### Step 2: KIS/키움 프로바이더
- `KISProvider` 구현 (서비스 키 필요)
- `KiwoomProvider` 구현 (서비스 키 필요)
- `DataAggregator` capabilities 기반 라우팅
- 스케줄러: 장 마감 후 일봉 수집 + 분기별 재무 수집

### Step 3: 레거시 제거
- `backend/` 가격 관련 코드 제거
- 프론트엔드 `api.ts` (레거시 클라이언트) 제거
- 레거시 `backend/:8000` 의존성 완전 해소

---

## 9. 미결 사항

- [ ] KIS/키움 서비스 키 미등록 상태 — Step 1은 yfinance만으로 진행
- [ ] yfinance 한국 주식 품질: 종가 정확도 검증 필요 (기존 `spec/data-source/spec.md` §8.2 참고)
- [ ] 분봉 데이터 지원 시기: v2 이후 (현재 일봉만)
- [ ] 캐싱 전략: on-demand 수집 시 DB 캐시 TTL / 갱신 주기

### 향후 확장: 비구조화 데이터

DataProvider는 구조화된 수치 데이터(가격, 재무, 배당) 담당.
비구조화 데이터(텍스트, 감성)는 별도 추상화로 분리 예정:

```
DataProvider (구조화 수치)        ContentProvider (비구조화, 향후)
  ├─ YFinanceProvider              ├─ NewsProvider (뉴스/공시 텍스트)
  ├─ KISProvider                   ├─ CommunityProvider (포럼/SNS 감성)
  ├─ KiwoomProvider                ├─ PlatformProvider (거래 동향/인기종목)
  ├─ DartProvider                  └─ TrendsProvider (Google Trends)
  └─ ECOSProvider (향후)
```

목표: 모을 수 있는 데이터는 전부 수집 → AI 분석 파이프라인에 투입.
ContentProvider 설계 시점은 AI 분석 모듈(v2) 구현 시 함께 진행.
수집 가능 데이터 전체 목록: `docs/research/collectible-data-inventory.md`

---

## 10. 관련 문서

- `docs/architecture.md` §4.2 — 클라우드 서버 역할
- `sv_core/broker/base.py` — BrokerAdapter ABC (주문 + 실시간)
- `spec/data-source/spec.md` — Phase 1-2 데이터 소스 비교 (참고 자료)
- `docs/research/collectible-data-inventory.md` — 전체 수집 가능 데이터 인벤토리
- `cloud_server/collector/scheduler.py` — 기존 스케줄러
- `cloud_server/services/yfinance_service.py` — 기존 지수/환율 수집
- DART OpenAPI: https://opendart.fss.or.kr
