# 데이터 소스 전략 명세서 (data-source)

> 작성일: 2026-03-04 | 상태: **Unit 4 (cloud-server) 참고 자료**

---

## 1. 개요

### 목표
StockVision의 AI 시스템매매 플랫폼에서 사용할 **주가 데이터, 재무 데이터, 거시경제 지표**의 최적 소스를 정의하고, 각 소스별 **법적 제약, 기술 요구사항, 비용 구조**를 문서화한다.

### 현황 (2026-03-04)
- **현재 사용**: yfinance (무료, Yahoo Finance 기반)
- **시장 범위**: 미국 주식 중심 (AAPL, GOOGL 등), 한국 주식 가능하나 품질 이슈
- **데이터 타입**: 일봉 OHLCV (Open, High, Low, Close, Volume)
- **추가 계획**: 키움증권 REST API (모의투자용 실시간 시세)

### 문제점
1. **한국 주식 데이터 품질**: yfinance는 한국 데이터가 불완전하거나 지연된 경우 多
2. **실시간성 부족**: yfinance는 종가 기준 야간 업데이트 (실시간 X)
3. **법적 불확실성**:
   - yfinance는 Yahoo Finance ToS 기반 스크래핑 → 상업용 사용 제약 있을 수 있음
   - 키움 G5 제5조③: 서버에서 수집한 시세 데이터를 다수 사용자에게 중계 금지
4. **무료 API 제약**: rate limit, 기능 제약 (실시간 아님, 기술적 지표 미제공 등)

---

## 2. 데이터 종류별 요구사항

### 2.1 주가 시세 데이터 (Price Data)

#### 요구 항목
| 항목 | 주기 | 범위 | 품질 목표 |
|------|------|------|---------|
| OHLCV (일봉) | 매 거래일 | 코스피/코스닥 전 종목 | 지연 < 24시간 |
| OHLCV (분봉) | 매 분 | 관심 종목 20~50개 | 실시간 (필요시 향후) |
| 거래량 | 매 거래일 | 전 종목 | 정확 ±1% |
| 호가 데이터 | 실시간 | 관심 종목 | 실시간 (Phase 3 이후) |
| 공시 정보 | 수시 | 관련 종목 | 당일 수집 |

#### 용도
- **백테스팅**: 과거 1~5년 일봉 데이터로 전략 검증
- **예측 모델**: 최근 N일 OHLCV → 다음 날 수익률 예측
- **기술적 지표**: RSI, EMA, MACD 등 계산용 기초 데이터
- **위험 관리**: 실시간 가격 조회로 포지션 평가 (현재가, 수익률)

---

### 2.2 재무 데이터 (Fundamental Data)

#### 요구 항목
| 항목 | 주기 | 범위 | 정확도 |
|------|------|------|-------|
| PER, PBR, ROE | 분기 | 관심 종목 | 공식 공시 기준 |
| EPS, BPS | 분기 | 관심 종목 | 공식 공시 기준 |
| 부채비율, 유동비율 | 분기 | 관심 종목 | 공식 공시 기준 |
| 배당수익률 | 연간 | 관심 종목 | 공식 공시 기준 |
| 영업이익, 순이익 | 분기 | 관심 종목 | 공식 공시 기준 |

#### 용도
- **스코어링**: 가치주 선정 (PER < 10 등)
- **스크리닝**: 재무 건전성 필터
- **모델 피처**: ML 예측 모델의 입력 특징

#### 현재 지원 상황
- ✅ yfinance에서 일부 제공 (info, balancesheet, income_stmt)
- ⚠️ 데이터 신선도 불확실, API 마다 필드명 상이

---

### 2.3 거시경제 지표 (Macro Indicators)

#### 요구 항목
| 항목 | 주기 | 범위 | 정확도 |
|------|------|------|-------|
| 기준금리 | 월 | 한국 | 한국은행 공식 |
| 환율 (USD/KRW) | 일 | 한국 | 실시간 |
| 코스피/코스닥 지수 | 일 | 한국 시장 전체 | 실시간 |
| 미국 S&P 500 | 일 | 미국 시장 | 실시간 |
| 원유/금 가격 | 일 | 글로벌 | 일 1회 |
| 실업률, GDP | 월/분기 | 한국/미국 | 공식 공시 |

#### 용도
- **백그라운드**: 시장 심리, 리스크 환경 판단
- **모델 컨텍스트**: 경기 사이클 반영 (향후)
- **리스크 조정**: 금리 인상 시 포지션 조정 (향후)

#### 현재 지원 상황
- ⚠️ yfinance에서 지수만 가능 (^KS11, ^GSPC)
- ❌ 금리, 환율 등은 별도 소스 필요

---

## 3. 소스별 비교 분석

### 3.1 yfinance (현재 사용 중)

#### 개요
- **출처**: Yahoo Finance
- **비용**: 무료
- **API 방식**: Python 라이브러리 (`pip install yfinance`)
- **현황**: 적극적 개발 (오픈소스, Github 활발)

#### 지원 기능
| 기능 | 지원 | 품질 |
|------|------|------|
| 미국 주식 OHLCV | ✅ | 우수 |
| 한국 주식 OHLCV (.KS/.KQ) | ✅ | 중간 (지연, 누락) |
| 배당, 스플릿 | ✅ | 우수 |
| 재무 정보 (info, balance, income) | ✅ | 중간 (신선도 불확실) |
| 옵션 데이터 | ✅ | 우수 |
| 지수 (^KS11, ^GSPC) | ✅ | 우수 |
| 일봉 (일일 종가) | ✅ | 우수 |
| 분봉 / 시간봉 | ❌ | N/A |
| 실시간 시세 | ❌ | N/A |
| Rate Limit | 제약 | ~2000 호출/시간 (비공식) |

#### 코드 예시 (StockVision 현황)
```python
# backend/app/services/data_collector.py
import yfinance as yf

yf_symbol = "005930.KS"  # 삼성전자
ticker = yf.Ticker(yf_symbol)
df = ticker.history(start="2020-01-01", end="2026-03-04")
```

#### 법적/약관 제약
- **Yahoo Finance ToS**: 상업적 사용 제한 가능성 있음
  - 조항: "개인 정보 목적에만 사용 가능"
  - 실제 집행: 관대한 편 (대부분 용인)
- **yfinance 라이센스**: Apache 2.0 (오픈소스)
- **권장사항**:
  - 경량 데이터만 사용 (OHLCV, 배당)
  - 대규모 상업 배포 시 Yahoo에 문의
  - 자체 API로 전환 검토

#### 장점
- ✅ 무료
- ✅ Python 친화적 (이미 통합)
- ✅ 한국 주식 지원 (6자리 코드 → .KS 변환)
- ✅ 개발 초기 빠른 프로토타이핑

#### 단점
- ❌ 한국 주식 데이터 품질 낮음 (지연, 누락)
- ❌ 실시간 데이터 지원 안 함 (야간 업데이트만)
- ❌ 법적 불확실성 (상업용 ToS)
- ❌ Rate limit 비공식 (언제 바뀔지 불명)
- ❌ 분봉 데이터 지원 안 함

---

### 3.2 키움증권 REST API (계획 중)

#### 개요
- **출처**: 키움증권 Open API+
- **비용**: 무료 (시스템매매 가입 후 신청)
- **API 방식**: HTTP REST + OAuth2
- **현황**: 공식 지원 (기술지원팀 있음)

#### 지원 기능
| 기능 | 지원 | 범위 | 비고 |
|------|------|------|------|
| 실시간 시세 | ✅ | 한국 주식 | WebSocket 또는 REST |
| 과거 OHLCV (분봉~일봉) | ✅ | 한국 주식 | 최대 100일 |
| 재무정보 | ✅ | 한국 상장사 | 별도 구독료? |
| 모의투자 (Paper Trading) | ✅ | 데모 계좌 | 무료 |
| 실 거래 실행 | ✅ | 실제 계좌 | 사용자 책임 |

#### 코드 예시 (개발 예정)
```python
# backend/app/services/kiwoom_client.py (현재 스텁)
import httpx

class KiwoomClient:
    def __init__(self, app_key, app_secret):
        self.base_url = "https://openapi.kiwoom.com:8443"
        self.app_key = app_key
        self.app_secret = app_secret

    async def get_real_time_quote(self, ticker: str):
        """삼성전자 (005930) 실시간 시세"""
        # 코드 미구현 (스텁만 있음)
        pass
```

#### 법적/약관 제약 — **중요**
| 제약 | 내용 | 영향 |
|------|------|------|
| **G5 제5조②** | API 키/시크릿은 제3자(서버) 저장 금지 | 로컬 브릿지에서만 사용 |
| **G5 제5조③** | 서버에서 수집한 시세 데이터를 **다수 사용자에게 중계 금지** | ⚠️ SaaS 모델에서 문제! |
| **거래 시간** | 평일 09:00~15:30만 조회/주문 가능 | 야간/주말 거래 불가 |
| **Rate Limit** | 조회/주문 초당 5건 | 대량 데이터 수집 불가 |
| **플랫폼 제약** | Windows COM/OCX 기반 | Linux/macOS 미지원 |

#### 아키텍처 영향 (G5 제5조③)
```
문제: StockVision SaaS에서 여러 사용자가 공유 서버를 통해 시세 조회
              ↓
해결 1 (현재 권장): 로컬 브릿지 (사용자 PC에서 실행)
  - 사용자 PC → 로컬 브릿지 (Node.js/Python) → 키움 API
  - 백엔드은 거래 신호만 전송
  - 로컬 브릿지가 시세 조회 및 주문 실행
  - 참고: spec/kiwoom-integration/spec.md

해결 2 (미래): 모의투자 계좌 제한
  - 모의투자는 제약이 약할 수 있음 (확인 필요)
  - 실거래 시에만 로컬 브릿지 필수
```

#### 장점
- ✅ 실시간 한국 주식 시세 (공식, 신뢰성 높음)
- ✅ 실제 거래 실행 가능 (Phase 4 목표)
- ✅ 분봉 데이터 지원
- ✅ 공식 기술 지원

#### 단점
- ❌ **법적 제약 심함 (G5 제5조③)** — SaaS 모델 부적합
- ❌ Windows COM 기반 → 로컬 브릿지 필수
- ❌ Rate limit 엄격 (초당 5건)
- ❌ 사용자가 별도 가입 필요 (키움 계좌)
- ❌ 모의투자 한정 (실거래 시 신용/보유자금 필요)

---

### 3.3 한국거래소 (KRX) — 공공 API

#### 개요
- **출처**: Korea Exchange (거래소 공식)
- **비용**: 무료
- **API 방식**: OPEN API (https://openapi.krx.co.kr)
- **현황**: 공식 지원, 정기 업데이트

#### 지원 기능
| 기능 | 지원 | 품질 |
|------|------|------|
| 상장 종목 정보 (코드, 이름, 업종) | ✅ | 우수 |
| 일별 OHLCV (종가 기준) | ✅ | 우수 (공식) |
| 시가총액, 거래량 | ✅ | 우수 |
| 지수 (코스피, 코스닥) | ✅ | 우수 |
| 분봉 | ⚠️ | 제한적 |
| 실시간 시세 | ❌ | 종가 기준만 |
| 재무정보 | ❌ | 업종분류만 |

#### 코드 예시
```python
# 미 구현 (향후 추가 가능)
# https://openapi.krx.co.kr/docs/reference?group=Market
# TRADEDATE: 거래일
# ISUCODE: 종목 코드
# TRDPRC: 종가
# TRDVOL: 거래량
```

#### 법적/약관 제약
- **라이센스**: 공공 데이터 (제약 거의 없음)
- **사용 조건**: 저작권 표시 필수, 상업용 O
- **Rate Limit**: 비교적 관대 (분당 몇십 건)
- **데이터 품질**: 공식 거래소 데이터 (신뢰성 ✅)

#### 장점
- ✅ 무료, 공식 데이터
- ✅ 법적 제약 거의 없음
- ✅ 종목 분류, 지수 등 메타데이터 풍부
- ✅ 대규모 데이터 수집 가능

#### 단점
- ❌ 종가 기준만 (분봉 X, 실시간 X)
- ❌ 일봉 데이터 24시간 지연 (종가 기준)
- ❌ API 문서 영어 부족, 한국어 기술지원 미약
- ❌ 재무정보 미제공

---

### 3.4 코스콤 (KOSCOM) OpenPlatform

#### 개요
- **출처**: 코스콤 (한국거래소 자회사)
- **비용**: 유료 (기본 가입료 + 데이터료)
- **API 방식**: REST API + WebSocket
- **현황**: 공식 금융 데이터 제공자

#### 지원 기능
| 기능 | 지원 | 품질 |
|------|------|------|
| 실시간 시세 | ✅ | 우수 |
| 분봉 | ✅ | 우수 |
| 재무 정보 | ✅ | 우수 |
| 뉴스/공시 | ✅ | 우수 |
| 모의/실거래 계좌 연동 | ✅ | 우수 |

#### 비용 구조
| 항목 | 금액 | 비고 |
|------|------|------|
| 기본 가입료 | 월 50K~100K | 데이터 팩에 따라 다름 |
| 실시간 시세 | 추가 비용 | 종목 수에 따라 증가 |
| 월 | ~500K | 스타트업 프리티어 할인 |

#### 법적/약관 제약
- **라이센스**: 상업용 명시 OK
- **사용 범위**: 회사 구독에 포함된 모든 기능 사용 가능
- **재판매**: 데이터 재판매 금지 (SaaS 분석용 O, 데이터 판매 X)

#### 장점
- ✅ 실시간 + 분봉 모두 지원
- ✅ 재무 정보 풍부
- ✅ 법적으로 명확한 SaaS 사용 OK
- ✅ 공식 금융 데이터 제공자 (신뢰성)

#### 단점
- ❌ **유료** (월 50K 이상)
- ❌ 초기 가입 비용 & 기술지원 필요
- ❌ 스타트업 초기에는 과도한 비용

---

### 3.5 Alpha Vantage

#### 개요
- **출처**: Alpha Vantage (제3자 데이터 애그리게이터)
- **비용**: 무료 (제한), 유료 (Tier 가격)
- **API 방식**: HTTP REST
- **현황**: 인기 있는 무료 API

#### 지원 기능
| 기능 | 지원 | 품질 |
|------|------|------|
| 미국 주식 OHLCV | ✅ | 우수 |
| 분봉 | ✅ | 우수 |
| 기술적 지표 (RSI, EMA, MACD) | ✅ | 우수 (직접 계산 불필요) |
| FX (외환) | ✅ | 우수 |
| 암호화폐 | ✅ | 우수 |
| 한국 주식 | ❌ | 미지원 |

#### Rate Limit & 가격
| 플랜 | 호출 수 | 월 비용 |
|------|---------|--------|
| 무료 | 5건/분, 500/일 | $0 |
| 제1 플랜 | 무제한 | $8/월 |

#### 장점
- ✅ 기술적 지표 직접 제공 (계산 불필요)
- ✅ 무료 플랜 충분 (개발/테스트용)
- ✅ 미국 주식 데이터 우수

#### 단점
- ❌ **한국 주식 미지원**
- ❌ 무료 플랜 Rate limit 심각
- ❌ 유료화하려면 월 구독 필요

---

## 4. 추천 데이터 소스 전략

### 4.1 Phase 별 권장사항

#### Phase 1~2 (현재: 개발/테스트)
```
목표: 빠른 프로토타이핑, 최소 비용

데이터 구성:
  [일봉 OHLCV]     → yfinance (무료, 충분함)
  [기술적 지표]    → 직접 계산 (TA-Lib 또는 pandas)
  [재무 정보]      → yfinance (필요시만)
  [지수/리스크]    → yfinance (^KS11, ^GSPC)

비용: $0
장점: 무료, 빠른 개발
단점: 한국 데이터 품질 낮음 (허용 범위)
```

**구현 현황**:
- ✅ `backend/app/services/data_collector.py`: yfinance 기반 수집
- ✅ `backend/app/services/technical_indicators.py`: 지표 직접 계산
- ⚠️ `backend/app/services/kiwoom_client.py`: 스텁 상태 (미구현)

---

#### Phase 3 (런타임 개선: 한국 주식 정확성)
```
목표: 한국 주식 데이터 품질 향상, 실시간성 추가

데이터 구성:
  [일봉 OHLCV]     → KRX 공공 API (무료, 공식)
  [기술적 지표]    → 직접 계산 (그대로)
  [분봉 시세]      → 키움 REST API (필수, 로컬 브릿지)
  [실시간 시세]    → 키움 REST API (필수, 로컬 브릿지)
  [재무 정보]      → 코스콤 또는 yfinance (선택)

비용: $0 (로컬 브릿지만 설정)
단점: 사용자가 키움 계좌 필요, 로컬 브릿지 운영

아키텍처:
  BackEnd (지표 계산)
         ↓
  LocalBridge (키움 REST API 호출, 시세 조회)
         ↓
  사용자 PC
```

**미결 사항**:
- [ ] KRX API 통합
- [ ] 키움 로컬 브릿지 구현 (별도 프로젝트)
- [ ] yfinance → KRX 마이그레이션 스크립트

---

#### Phase 4 (실거래: 완전성)
```
목표: 실거래 지원, 재무 정보 포함

데이터 구성:
  [일봉 OHLCV]     → KRX 공공 API
  [기술적 지표]    → 직접 계산
  [분봉/실시간]    → 키움 로컬 브릿지
  [재무 정보]      → 코스콤 또는 yfinance
  [거시경제]       → 한국은행 API + yfinance

비용: ~월 50K (코스콤 기본료)
단점: 유료 데이터

아키텍처:
  StockVision Backend (신호 생성)
         ↓ (WebSocket)
  LocalBridge (실거래 주문 실행)
         ↓ (REST API)
  키움증권 OpenAPI+
         ↓
  실제 거래소 (매매 실행)
```

**미결 사항**:
- [ ] 코스콤 데이터 구독 & 통합
- [ ] 한국은행 API 통합 (금리 등)

---

### 4.2 현재 권장 (Phase 2)

#### 즉시 적용
- ✅ **yfinance 계속 사용** (Phase 2 목표 달성 충분)
- ✅ **KRX 공공 API 추가** (보조 데이터로 정확성 향상)
  - 종목 메타데이터 (이름, 업종, 상장일)
  - 일봉 OHLCV 검증/보정 (yfinance와 비교)
  - 거래량 검증

#### 코드 구조 제안
```python
# backend/app/services/data_sources/
├── yfinance_source.py      # 기존 (수정 X)
├── krx_source.py           # 신규 (KRX API)
├── kiwoom_source.py        # 향후 (로컬 브릿지)
└── data_aggregator.py      # 여러 소스 결합

# 사용 예
aggregator = DataAggregator()
prices = aggregator.get_daily_prices(
    symbol="005930",
    start="2020-01-01",
    end="2026-03-04",
    sources=["yfinance", "krx"]  # 두 소스에서 조회 후 검증
)
```

---

## 5. 법적/약관 제약 정리

### 5.1 yfinance (현재)

| 제약 | 내용 | 대응 방안 |
|------|------|---------|
| **Yahoo Finance ToS** | 상업용 사용 제한 모호 | 경량 데이터만 사용, 규모 작을 때는 관대 |
| **라이센스** | Apache 2.0 | 저작권 표시 필요 |
| **API 안정성** | 비공식 API (웹 스크래핑) | 언제 망가질지 불명, 백업 필수 |
| **Rate Limit** | 비공식 (~2000/시간) | 체계적 관리 필요 (현재 구현됨) |

**권장**: 개발/테스트 단계에서는 OK, 상용화 시 정규 API로 전환 필수

---

### 5.2 키움증권 OpenAPI+ (G5 제5조)

#### **중요 제약: G5 제5조③ (금지 사항)**
```
"거래소 제공 정보(시세, 공시 등)를 수집 후
 제3자(서버)에서 다수 사용자에게 중계하는 것"을 금지
```

#### 해석 (법률 자문 필요)
```
❌ 금지: 백엔드 서버에서 키움 시세를 조회해서
       프론트엔드의 모든 사용자에게 송신

✅ 허용: 각 사용자 PC의 로컬 브릿지에서 직접 조회
       (1대1 대응, 중계 X)

⚠️ 모호: 모의투자 모드는 제약이 약할 수 있음 (별도 확인)
```

#### 준수 방안
1. **로컬 브릿지 아키텍처 필수**
   - 사용자 PC에 브릿지 설치
   - 키움 API는 로컬에서만 호출
   - 참고: `spec/kiwoom-integration/spec.md`

2. **모의투자 제한**
   - Phase 2~3: 모의투자만 (제약 약함)
   - Phase 4: 실거래 (로컬 브릿지 필수)

3. **문서화 & 컴플라이언스**
   - 키움증권에 사전 문의 (권장)
   - 이용약관 준수 명시

---

### 5.3 KRX 공공 API

| 제약 | 내용 | 대응 |
|------|------|-----|
| **라이센스** | 공공 데이터 (CC 또는 정부 라이센스) | 저작권 표시 필수 |
| **상업용** | 명시 OK | 자유로운 사용 |
| **재판매** | 추가 분석 후 판매 O, 원본 판매 X | 분석 부가가치 필요 |
| **Rate Limit** | 관대 (분당 100~1000) | 특별 대응 불필요 |

**권장**: 가장 안전한 선택, 향후 주요 소스로 전환

---

### 5.4 코스콤

| 제약 | 내용 | 대응 |
|------|------|-----|
| **라이센스** | 유료 데이터 (구독 계약) | 계약서 상 사용 범위 준수 |
| **SaaS** | 명시 O (분석/투자 서비스) | 자유로운 사용 |
| **재판매** | 금지 (데이터 판매 불가) | 서비스로만 제공 |
| **Rate Limit** | 구독 수준에 따라 | 구독 플랜 선택 |

**권장**: Phase 4 실거래 시 법적으로 가장 명확

---

## 6. 기술 요구사항

### 6.1 데이터 수집 아키텍처

#### 현재 (Phase 2)
```
┌─────────────────────────────────┐
│     StockVision Backend         │
│  (FastAPI, SingleCore)          │
├─────────────────────────────────┤
│  DataCollector                  │
│    ├─ yfinance (OHLCV)          │
│    ├─ KRX API (종목 정보)       │
│    └─ Technical Indicators      │
├─────────────────────────────────┤
│  Database                       │
│    ├─ Stock                     │
│    ├─ StockPrice                │
│    └─ TechnicalIndicator        │
└─────────────────────────────────┘
```

**코드 경로**:
- `backend/app/services/data_collector.py` — 데이터 수집
- `backend/app/services/stock_data_service.py` — 캐싱 & 서빙
- `backend/app/services/technical_indicators.py` — 지표 계산
- `backend/app/core/rate_limit_monitor.py` — Rate limit 관리
- `backend/app/api/stocks.py` — REST 엔드포인트

#### 향후 (Phase 3~4)
```
┌────────────────────────────────────────┐
│  LocalBridge (사용자 PC)               │
│  ├─ Kiwoom OpenAPI+ Client             │
│  ├─ WebSocket Client (Backend 연결)    │
│  └─ SQLite Cache                       │
└────────────────────────────────────────┘
         ↕ (WebSocket)
┌────────────────────────────────────────┐
│  StockVision Backend                   │
│  ├─ DataAggregator                     │
│  │  ├─ yfinance (미국 주식)            │
│  │  ├─ KRX API (한국 일봉)             │
│  │  ├─ KOSCOM (재무정보, 실시간)       │
│  │  └─ LokalBridge (키움 분봉/실시간)  │
│  └─ Technical Indicators               │
└────────────────────────────────────────┘
```

---

### 6.2 구체적 구현 계획 (Phase 3)

#### Step 1: KRX API 통합
```python
# 신규: backend/app/services/krx_source.py
class KRXDataSource:
    """한국거래소 공공 API"""

    async def get_daily_prices(self, code: str, start_date, end_date):
        """일봉 OHLCV 조회"""
        # REST API 호출: openapi.krx.co.kr
        # 응답 파싱 & DataFrame 반환
        pass

    async def get_listed_stocks(self):
        """상장 종목 정보 (코드, 이름, 업종)"""
        pass
```

**테스트**:
```python
# backend/tests/test_krx_integration.py
async def test_krx_daily_prices():
    source = KRXDataSource()
    df = await source.get_daily_prices("005930", "2020-01-01", "2026-03-04")
    assert not df.empty
    assert set(df.columns) == {"open", "high", "low", "close", "volume"}
```

#### Step 2: 데이터 소스 추상화
```python
# 신규: backend/app/services/data_sources/base.py
from abc import ABC, abstractmethod

class DataSource(ABC):
    @abstractmethod
    async def get_daily_prices(self, code: str, start, end) -> pd.DataFrame:
        pass

    @abstractmethod
    async def get_metadata(self, code: str) -> dict:
        pass

# 구현
class YFinanceDataSource(DataSource):
    async def get_daily_prices(self, code: str, start, end):
        # yfinance 호출
        pass

class KRXDataSource(DataSource):
    async def get_daily_prices(self, code: str, start, end):
        # KRX 호출
        pass
```

#### Step 3: 데이터 애그리게이터
```python
# 신규: backend/app/services/data_aggregator.py
class DataAggregator:
    def __init__(self):
        self.sources = {
            "yfinance": YFinanceDataSource(),
            "krx": KRXDataSource(),
        }

    async def get_daily_prices(self, code: str, start, end,
                               sources=None):
        """여러 소스에서 조회, 검증, 병합"""
        if sources is None:
            sources = ["krx", "yfinance"]  # 기본: KRX 우선

        results = {}
        for source_name in sources:
            df = await self.sources[source_name].get_daily_prices(
                code, start, end
            )
            results[source_name] = df

        # 데이터 검증: KRX와 yfinance 비교
        #   - OHLCV 오차율 ±1% 이내?
        #   - 거래량 차이?

        # 병합: KRX 우선, yfinance 보충
        merged = self._merge_sources(results, sources)
        return merged

    def _merge_sources(self, results, priority):
        """우선순위 기반 병합"""
        # TODO
        pass
```

---

### 6.3 기술 스택

#### 기존
| 항목 | 선택 |
|------|------|
| API 클라이언트 | yfinance (Python 라이브러리) |
| HTTP 클라이언트 | httpx (async) |
| DB | SQLAlchemy ORM |
| 캐싱 | LRUCache (메모리) |
| Rate Limit | 커스텀 (초당 요청 수 추적) |

#### 추가 필요
| 항목 | 선택 | 비용 |
|------|------|------|
| KRX API 클라이언트 | httpx 또는 requests | 무료 |
| 데이터 검증 | pandas, numpy | 무료 |
| 시계열 데이터 분석 | pandas, TA-Lib | 무료 |

#### 향후 (로컬 브릿지)
| 항목 | 선택 | 비고 |
|------|------|------|
| 언어 | Python 3.13 | yfinance와 호환 |
| 키움 API | pywin32 (COM) | Windows 전용 |
| WebSocket | websockets | 백엔드와 통신 |
| 로컬 DB | SQLite | 오프라인 캐시 |

---

## 7. 구현 체크리스트

### Phase 2 (현재, 무변경)
- [x] yfinance 기반 일봉 수집
- [x] 기술적 지표 계산 (RSI, EMA, MACD, Bollinger)
- [x] Rate limit 관리
- [x] 캐싱 (LRU)
- [x] API 엔드포인트 (`GET /api/v1/stocks/{symbol}/bars`)

### Phase 3 (계획)
- [ ] KRX 공공 API 통합
  - [ ] 종목 메타데이터 조회
  - [ ] 일봉 OHLCV 조회
  - [ ] 데이터 검증 (yfinance vs KRX 비교)
- [ ] 데이터 소스 추상화
  - [ ] `DataSource` 인터페이스 정의
  - [ ] `YFinanceDataSource` 구현
  - [ ] `KRXDataSource` 구현
- [ ] 데이터 애그리게이터
  - [ ] 우선순위 기반 병합
  - [ ] 품질 메트릭 (수집 성공률, 데이터 신선도)
- [ ] 문서화
  - [ ] KRX API 호출 가이드
  - [ ] 운영 매뉴얼 (데이터 신선도 모니터링)

### Phase 4 (계획)
- [ ] 코스콤 데이터 구독 & 통합
  - [ ] 인증/토큰 관리
  - [ ] 실시간 시세 WebSocket 수신
  - [ ] 재무정보 조회
- [ ] 한국은행 API 통합
  - [ ] 기준금리 조회
  - [ ] 환율 데이터
- [ ] 로컬 브릿지 (별도 프로젝트)
  - [ ] 키움 OpenAPI+ 연동
  - [ ] WebSocket 통신
  - [ ] 백테스트/실거래 지원

---

## 8. 미결 사항

### 8.1 아키텍처 결정
- [ ] **KRX API 우선순위**: yfinance와 KRX 중 어느 것을 주 소스로 쓸 것인가?
  - 옵션 A: yfinance 우선 (현상 유지), KRX는 검증용
  - 옵션 B: KRX 우선, yfinance는 미국 주식/보충용
  - **권장**: 옵션 B (한국 주식 품질 향상)

- [ ] **코스콤 구독 시기**: Phase 3 끝 vs Phase 4 시작?
  - 비용 고려: 월 50K~
  - 시점 고려: 사용자 수, 수익화 계획

- [ ] **로컬 브릿지 개발**: 별도 오픈소스 vs StockVision 통합?
  - 의존성 분리 vs 단일 프로젝트
  - 사용자 설치 복잡도

### 8.2 기술 검증 필요
- [ ] **yfinance 한국 주식 품질**: 실제 거래소 데이터와 오차 측정
  - 샘플: 삼성전자 (005930), 카카오 (035720) 등
  - 기간: 최근 1년
  - 평가지표: OHLC 오차율, 거래량 누락률

- [ ] **KRX API 안정성**: 업타임, Rate limit, 응답 속도
  - 부하 테스트: 동시 100개 종목 조회
  - 장시간 모니터링: 일주일 이상

- [ ] **키움 G5 제5조③ 해석**: 법률 자문 필수
  - 모의투자 vs 실거래 제약 차이
  - 로컬 브릿지 아키텍처 타당성

### 8.3 문서화 필요
- [ ] **운영 매뉴얼**: 데이터 신선도, 수집 실패 대응
- [ ] **마이그레이션 가이드**: yfinance → KRX 전환 절차
- [ ] **로컬 브릿지 설치 가이드**: 사용자용 (향후)

### 8.4 법적 컴플라이언스
- [ ] **키움증권 사전 문의**: G5 제5조 해석
  - 문의처: 키움증권 시스템매매 기술지원팀
  - 목표: 로컬 브릿지 아키텍처 사전 승인

- [ ] **코스콤 계약 검토**: 서비스 조건
  - 데이터 재판매 제약
  - 가격 결정 방식 (종목 수, 사용자 수)

- [ ] **이용약관 업데이트**:
  - 데이터 출처 명시 (yfinance, KRX, 코스콤)
  - 라이센스 공개 (Apache 2.0, CC 등)

---

## 9. 참고 자료

### 공식 문서
- **yfinance**: https://github.com/ranaroussi/yfinance
- **KRX OpenAPI**: https://openapi.krx.co.kr/
- **코스콤**: https://openplatform.koscom.co.kr/
- **키움 OpenAPI+**: https://www.kiwoom.com/ (기술지원팀)
- **한국은행 API**: https://www.bok.or.kr/

### 프로젝트 문서
- `docs/architecture.md` — 전체 아키텍처
- `spec/kiwoom-integration/spec.md` — 키움 연동 & 로컬 브릿지
- `spec/virtual-auto-trading/spec.md` — 가상 거래 엔진
- `backend/app/services/data_collector.py` — 현재 구현

### 코드 경로 (StockVision)
| 영역 | 경로 | 상태 |
|------|------|------|
| 데이터 수집 | `backend/app/services/data_collector.py` | ✅ yfinance만 |
| 데이터 서빙 | `backend/app/services/stock_data_service.py` | ✅ 캐싱 포함 |
| 지표 계산 | `backend/app/services/technical_indicators.py` | ✅ 완성 |
| Rate Limit | `backend/app/core/rate_limit_monitor.py` | ✅ 완성 |
| REST API | `backend/app/api/stocks.py` | ✅ 완성 |
| 키움 클라이언트 | `backend/app/services/kiwoom_client.py` | ⚠️ 스텁만 |

---

## 10. 요약

### 현황 (2026-03-04)
- yfinance 기반 일봉 데이터 수집 (미국 주식 중심)
- 한국 주식 데이터 품질 문제 존재
- 실시간 시세 미지원

### 즉시 추천 (Phase 2 내)
1. **유지**: yfinance 계속 사용 (변경 불필요)
2. **추가**: KRX 공공 API로 데이터 검증/보정
3. **문서화**: 이 명세서 기반 운영 가이드

### 중기 계획 (Phase 3)
- KRX를 주 소스로 전환 (한국 주식)
- 데이터 소스 추상화 & 애그리게이터 구현
- 로컬 브릿지 초안 완성

### 장기 계획 (Phase 4)
- 코스콤 구독 (실시간 + 재무)
- 키움 실거래 지원 (로컬 브릿지 완성)
- 거시경제 지표 통합

### 법적 주의점
- ⚠️ **yfinance**: 상용화 시 Yahoo Finance ToS 확인 필수
- ⚠️ **키움**: G5 제5조③ 때문에 로컬 브릿지 필수 (SaaS 모델에서)
- ✅ **KRX**: 공공 데이터, 안전함
- ✅ **코스콤**: 유료지만 법적으로 명확

---

**작성자**: Claude Code
**최종 검토 일시**: 2026-03-04
**다음 검토**: Phase 3 기획 시
