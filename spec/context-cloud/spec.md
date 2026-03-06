# 컨텍스트 클라우드 기능 명세서 (context-cloud)

> 작성일: 2026-03-04 | 상태: **→ Unit 4 (cloud-server)에 통합**
>
> 이 spec의 내용은 `spec/cloud-server/`에서 통합 구현합니다.

---

> **아키텍처 노트 (2026-03-04)**
>
> | 구분 | 역할 |
> |------|------|
> | **클라우드 서버** | 시장 변수 **계산 및 API 제공** (`GET /api/context`) |
> | **로컬 서버** | 클라우드 API를 **fetch → 로컬 캐시** → 전략 평가에 활용 |
>
> - 클라우드는 DB를 직접 공유하지 않음
> - 로컬 서버가 장 마감 후 1회 `GET /api/context` 호출 → 로컬 캐시(JSON/SQLite) 저장
> - 전략 평가 엔진은 캐시된 컨텍스트를 참조

---

## 1. 개요

**컨텍스트 클라우드**는 StockVision 백엔드가 주기적으로 시장 상황 지표들을 계산하여 서버에 저장하고,
프론트엔드와 전략 조건 빌더가 실시간으로 조회할 수 있게 하는 데이터 레이어다.

핵심 역할:
- 시장 전체, 섹터별, 개별 종목의 **정량적 상황 지표** 제공
- 사용자가 자동매매 규칙의 **입력 조건**으로 활용 가능
- LLM이 시장 상황을 **자연어로 설명**하기 위한 기초 데이터 제공

## 2. 목표

### 주요 목표
1. **정책 준수**: 투자 판단 주체가 사용자 → 시스템은 "데이터 제공만"
   - 컨텍스트는 **사실(fact)** 제공, 추천(recommendation) 금지
   - 예: "시장_변동성 = 18.3%" ✓ vs "지금 매수하세요" ✗

2. **조건 빌더 활용성**:
   - 자동매매 규칙에서 "시장_RSI > 70이면 매수" 같은 조건 설정 가능
   - "코스피_모멘텀이 양수이고 반도체_강도가 75 이상이면" 등 복합 조건

3. **대시보드 시각화**:
   - 프론트엔드에서 현재 시장 상황을 한눈에 파악
   - 과거 컨텍스트 변화 추이 확인

4. **LLM 설명 레이어**:
   - 정량 데이터 → 자연어 설명 변환
   - "오늘 코스피 약세(RSI 28), 금융주 강세 대비 반도체 약세" 등

## 3. 제공 변수 목록

### 3.1 시장 전체 (Market-Level Context)

| 변수명 | 타입 | 업데이트 | 설명 | 범위 |
|--------|------|--------|------|------|
| `market_kospi_rsi` | Float | 매일 장 마감 후 | 코스피 지수 RSI | 0~100 |
| `market_kosdaq_rsi` | Float | 매일 장 마감 후 | 코스닥 지수 RSI | 0~100 |
| `market_kospi_volatility` | Float | 매일 장 마감 후 | 코스피 변동성(20일 표준편차) | % |
| `market_kosdaq_volatility` | Float | 매일 장 마감 후 | 코스닥 변동성 | % |
| `market_kospi_momentum` | Float | 매일 장 마감 후 | 코스피 모멘텀(ROC 12일) | % |
| `market_kosdaq_momentum` | Float | 매일 장 마감 후 | 코스닥 모멘텀 | % |
| `market_kospi_macd_histogram` | Float | 매일 장 마감 후 | 코스피 MACD 히스토그램 | - |
| `market_kosdaq_macd_histogram` | Float | 매일 장 마감 후 | 코스닥 MACD 히스토그램 | - |
| `market_vix_kr` | Float | 실시간(15분 지연) | 한국 VIX(공포 지수) | - |
| `market_usd_krw` | Float | 실시간 | USD/KRW 환율 | - |
| `market_bond_yield_10y` | Float | 일일 1회 | 10년물 국채 수익률 | % |
| `market_trend` | String | 매일 장 마감 후 | 시장 대세 판정 | "강세", "약세", "중립" |
| `market_strength_score` | Float | 매일 장 마감 후 | 전체 시장 강도 지표 | 0~100 |

### 3.2 섹터별 (Sector-Level Context)

각 섹터마다 다음 지표들을 제공:

| 변수명 | 타입 | 업데이트 | 설명 |
|--------|------|--------|------|
| `sector_{sector_name}_rsi` | Float | 매일 장 마감 후 | 해당 섹터 지수 RSI |
| `sector_{sector_name}_momentum` | Float | 매일 장 마감 후 | 해당 섹터 모멘텀 |
| `sector_{sector_name}_strength` | Float | 매일 장 마감 후 | 섹터 강도(0~100) |
| `sector_{sector_name}_relative_strength` | Float | 매일 장 마감 후 | 시장 대비 상대 강도 |
| `sector_{sector_name}_avg_rsi` | Float | 매일 장 마감 후 | 섹터 구성종목 평균 RSI |
| `sector_{sector_name}_avg_sentiment` | String | 매일 장 마감 후 | 섹터 전체 심리 | "강세", "약세", "중립" |

**포함 섹터** (한국시장 기준):
- 반도체 (Semiconductor)
- 금융 (Financial)
- 에너지 (Energy)
- 자동차 (Automotive)
- 통신 (Communication)
- 의약 (Healthcare)
- 식품 (Consumer)
- 화학 (Chemical)
- 철강 (Steel)

### 3.3 개별 종목 (Stock-Level Context)

이미 구현된 `stock_scores` 테이블의 주요 필드:

| 변수명 | 타입 | 업데이트 | 설명 |
|--------|------|--------|------|
| `stock_{symbol}_rsi` | Float | 매일 장 마감 후 | 종목 RSI |
| `stock_{symbol}_macd_signal` | String | 매일 장 마감 후 | MACD 신호 | "BUY", "SELL", "HOLD" |
| `stock_{symbol}_bollinger_position` | Float | 매일 장 마감 후 | 볼린저밴드 위치 | 0~100 |
| `stock_{symbol}_ema_trend` | String | 매일 장 마감 후 | EMA 트렌드 판정 | "상승", "하강", "중립" |
| `stock_{symbol}_prediction_score` | Float | 매일 장 마감 후 | RF 예측 점수 | 0~100 |
| `stock_{symbol}_total_score` | Float | 매일 장 마감 후 | 통합 스코어 | 0~100 |
| `stock_{symbol}_volume_ratio` | Float | 실시간 | 거래량 비율(평균 대비) | % |
| `stock_{symbol}_price_change_1d` | Float | 매일 장 마감 후 | 1일 변동률 | % |
| `stock_{symbol}_relative_strength_vs_market` | Float | 매일 장 마감 후 | 시장 대비 상대 강도 | - |

## 4. 계산 주기 및 스케줄링

### 4.1 데이터 수집 일정

| 데이터 | 계산 주기 | 타이밍 | 담당 서비스 |
|--------|----------|--------|-----------|
| 시장/섹터/종목 지표 | 매일 1회 | 장 마감 후 16:00~17:00 | `ContextCloudScheduler` |
| VIX/환율 | 실시간(15분 주기) | 거래 시간 중 | `KiwoomClient` 또는 별도 크롤러 |
| 매크로 지표 | 일일 1회(자동 + 수동) | 정보공시 후 | 크롤러/API(통계청, BOK) |
| 종목별 체결 데이터 | 실시간 또는 5분 주기 | 거래 시간 중 | `KiwoomClient` 또는 `StockDataService` |

### 4.2 스케줄러 설정 (APScheduler)

```python
# backend/app/services/context_cloud_scheduler.py (신규)

scheduler.add_job(
    func=calculate_market_context,
    trigger="cron",
    hour=16, minute=30,  # 장 마감 후
    id="context_cloud_market_daily"
)

scheduler.add_job(
    func=calculate_sector_context,
    trigger="cron",
    hour=16, minute=35,  # 시장 지표 이후
    id="context_cloud_sector_daily"
)

scheduler.add_job(
    func=calculate_stock_context,
    trigger="cron",
    hour=16, minute=40,  # 섹터 지표 이후
    id="context_cloud_stock_daily"
)

scheduler.add_job(
    func=update_macro_context,
    trigger="cron",
    hour=9, minute=0,  # 장 시작 전
    id="context_cloud_macro_daily"
)

scheduler.add_job(
    func=update_realtime_context,
    trigger="interval",
    minutes=15,  # 15분마다
    id="context_cloud_realtime"
)
```

## 5. LLM 설명 레이어

### 5.1 개념
컨텍스트 클라우드의 정량 데이터를 사용자 친화적인 자연어로 변환하는 프롬프트.

### 5.2 설명 생성 API (신규)

```
GET /api/v1/context-cloud/explain
Query Parameters:
  - language: "ko" (기본값), "en"
  - detail_level: "brief", "normal", "detailed" (기본값: "normal")

Response:
{
  "success": true,
  "data": {
    "market_summary": "현재 코스피는 약세 추세(RSI 28)지만, 기술적 반등 가능성 있음...",
    "sector_highlights": [
      "금융주 강세(RSI 72, 상대강도 +5%)",
      "반도체 약세 지속(RSI 35, 모멘텀 음수)"
    ],
    "macro_context": "환율 강세(1,250원), 장기 금리 상승세",
    "trading_implications": "금융주 중심 매수, 반도체 관찰 필요"
  }
}
```

### 5.3 LLM 프롬프트 구조

```
당신은 금융 시장 분석가입니다.
다음 정량 지표들을 해석하고 자연어로 설명해주세요.
(정책 준수) 투자 추천은 절대 금지. 객관적 사실만 설명하세요.

[시장 상황]
- 코스피 RSI: 28 → "과매도 상태"
- 코스피 모멘텀: -2.3% → "하락 추세"
- VIX: 18.5 → "정상 변동성"

[현재 상황 설명]
"현재 코스피는 기술적 과매도 상태이나, 모멘텀은 약세를 지속 중입니다..."

---
금지 사항:
❌ "지금 매수할 기회입니다"
❌ "이 종목은 강력한 추천입니다"
❌ 개인 투자 조언

허용 사항:
✓ "현재 RSI 35로 역사적 평균 대비 낮은 수준"
✓ "섹터별로 금융주는 상대 강도가 높고 반도체는 낮음"
✓ "기술적 관점에서 반등 신호는 가시화되지 않음"
```

## 6. 전략 빌더와의 연동 인터페이스

### 6.1 조건 빌더에서 컨텍스트 활용

프론트엔드의 규칙 생성 폼에서:

```
[조건 1] 시장 RSI (is greater than) 70  ← context_cloud.market_kospi_rsi 참조
[조건 2] 반도체 섹터 강도 (is greater than) 75  ← context_cloud.sector_semiconductor_strength
[조건 3] 종목 거래량배수 (is greater than) 1.2  ← context_cloud.stock_{symbol}_volume_ratio

연결: AND / OR
→ 모든 조건 만족하면 → 매수 신호 발생
```

### 6.2 API: 조건 검증 엔드포인트 (신규)

```
POST /api/v1/context-cloud/validate-condition
Request Body:
{
  "condition": {
    "left": "context_cloud.market_kospi_rsi",
    "operator": "gt",
    "right": 70
  }
}

Response:
{
  "success": true,
  "data": {
    "variable": "context_cloud.market_kospi_rsi",
    "current_value": 68,
    "condition_met": false,
    "last_updated": "2026-03-04T16:35:00Z"
  }
}
```

### 6.3 API: 변수 목록 조회 (신규)

```
GET /api/v1/context-cloud/variables?category=market

Response:
{
  "success": true,
  "count": 12,
  "data": [
    {
      "key": "market_kospi_rsi",
      "name": "코스피 RSI",
      "type": "float",
      "range": [0, 100],
      "description": "코스피 지수의 상대강도지수",
      "category": "market",
      "update_frequency": "daily",
      "last_value": 68,
      "last_updated": "2026-03-04T16:35:00Z"
    }
    ...
  ]
}
```

## 7. 데이터 소스

| 데이터 | 소스 | 비고 |
|--------|------|------|
| 코스피/코스닥 지수 | yfinance (`^KS11`, `^KQ11`) | 일일 종가 |
| 섹터 지수 | KRX API 또는 yfinance 섹터 ETF | 대체: 섹터 구성종목 평균 계산 |
| 개별 종목 가격/거래량 | 이미 수집 중 (`stock_prices` 테이블) | - |
| VIX-Korea | 거래소 API 또는 크롤링 | 실시간 공시 |
| 환율 | yfinance 또는 한국은행 API | KRW=X |
| 국채 수익률 | 한국은행 금융통계 API | 10년물 기준 |

## 8. 기술 요구사항

### 8.1 신규 테이블

```python
# backend/app/models/context_cloud.py (신규)

class ContextCloudSnapshot(Base):
    """시장 상황 스냅샷 (매일 저장)"""
    __tablename__ = "context_cloud_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(Date, nullable=False, unique=True)

    # 시장 전체
    market_kospi_rsi = Column(Float)
    market_kosdaq_rsi = Column(Float)
    market_kospi_volatility = Column(Float)
    market_kosdaq_volatility = Column(Float)
    market_kospi_momentum = Column(Float)
    market_kosdaq_momentum = Column(Float)
    market_kospi_macd_histogram = Column(Float)
    market_kosdaq_macd_histogram = Column(Float)
    market_vix_kr = Column(Float)
    market_usd_krw = Column(Float)
    market_bond_yield_10y = Column(Float)
    market_trend = Column(String(20))  # "강세", "약세", "중립"
    market_strength_score = Column(Float)

    # 섹터별 (JSON으로 유연하게 저장)
    sector_contexts = Column(JSON)  # {sector_name: {rsi, momentum, strength, ...}}

    # 매크로
    macro_contexts = Column(JSON)  # {indicator: value}

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_context_date', 'snapshot_date'),
    )

class ContextCloudRealtimeSnapshot(Base):
    """실시간 상황 스냅샷 (15분 주기 덮어씌우기)"""
    __tablename__ = "context_cloud_realtime_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_time = Column(DateTime, nullable=False)

    # 실시간 변수들
    market_vix_kr = Column(Float)
    market_usd_krw = Column(Float)

    # 개별 종목 실시간 데이터 (JSON)
    stock_realtime_data = Column(JSON)  # {symbol: {price, volume, change_pct}}

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 8.2 신규 서비스 계층

```python
# backend/app/services/context_cloud_service.py (신규)

class ContextCloudService:
    """컨텍스트 클라우드 데이터 관리"""

    def get_latest_context(self, snapshot_type: str = "daily") -> dict:
        """최신 컨텍스트 스냅샷 조회"""
        pass

    def get_context_history(self, days: int = 30) -> List[dict]:
        """N일간 컨텍스트 변화 조회"""
        pass

    def validate_condition(self, condition: dict) -> dict:
        """규칙 조건 검증"""
        pass

    def explain_context(self, detail_level: str = "normal") -> str:
        """컨텍스트 자연어 설명 생성 (LLM 호출)"""
        pass

# backend/app/services/context_cloud_scheduler.py (신규)

class ContextCloudScheduler:
    """컨텍스트 클라우드 스케줄링 및 계산"""

    def calculate_market_context(self):
        """시장 지표 계산"""
        pass

    def calculate_sector_context(self):
        """섹터 지표 계산"""
        pass

    def calculate_stock_context(self):
        """개별 종목 지표 계산"""
        pass

    def update_macro_context(self):
        """매크로 지표 업데이트"""
        pass

    def update_realtime_context(self):
        """실시간 지표 업데이트"""
        pass
```

### 8.3 신규 API 라우터

```python
# backend/app/api/context_cloud.py (신규)

@router.get("/api/v1/context-cloud/current")
async def get_current_context():
    """현재 컨텍스트 조회"""
    pass

@router.get("/api/v1/context-cloud/history")
async def get_context_history(days: int = 30):
    """컨텍스트 변화 조회"""
    pass

@router.get("/api/v1/context-cloud/variables")
async def list_variables(category: str = None):
    """조회 가능한 변수 목록"""
    pass

@router.post("/api/v1/context-cloud/validate-condition")
async def validate_condition(condition: ConditionInput):
    """규칙 조건 검증"""
    pass

@router.get("/api/v1/context-cloud/explain")
async def explain_context(detail_level: str = "normal", language: str = "ko"):
    """컨텍스트 자연어 설명"""
    pass
```

### 8.4 프론트엔드 연동

```typescript
// frontend/src/services/contextCloudClient.ts (신규)

export const contextCloudClient = {
  getCurrentContext: () => api.get('/context-cloud/current'),
  getContextHistory: (days: number) => api.get(`/context-cloud/history?days=${days}`),
  listVariables: (category?: string) => api.get('/context-cloud/variables', { category }),
  validateCondition: (condition: Condition) => api.post('/context-cloud/validate-condition', condition),
  explainContext: (detailLevel: string = 'normal') => api.get(`/context-cloud/explain?detail_level=${detailLevel}`),
};

// frontend/src/components/ConditionBuilder.tsx (기존 수정)
// 규칙 작성 UI에서 context_cloud 변수들을 드롭다운으로 제공
```

## 9. 미결 사항

### 9.1 섹터 분류 체계
- **미결**: 한국시장 섹터별 대표 종목/ETF 명시 필요
- **제안**: GICS 기반 또는 거래소 공시 기준 확정

### 9.2 LLM 프롬프트 엔지니어링
- **미결**: 자동생성된 설명의 정확도/품질 검증 필요
- **제안**: Claude API 통합 또는 로컬 모델(Gemma 등) 평가

### 9.3 성능 & 확장성
- **미결**: 일일 계산 5초 이내 달성 가능성 검증
  - 코스피/코스닥: yfinance 수집 (1초)
  - 9개 섹터 × 5개 지표: 2초
  - 구성종목 스코어링(100+ 종목): 2초
- **제안**: 캐싱, 병렬 처리, DB 인덱싱 최적화

### 9.4 정규화 및 신호 판정
- **미결**: RSI 28은 "과매도"인지 "약세"인지 일관성 있게 정의
- **제안**: 동적 임계값 vs 고정 임계값 결정

### 9.5 API 인증
- **미결**: 퍼블릭 변수 vs 프리미엄 변수 구분 필요
- **제안**: 현재는 모든 변수 공개, 향후 API 키 기반 분류

### 9.6 백테스팅과의 연동
- **미결**: 백테스팅 시 과거 컨텍스트 조회 방식
  - 예: 2025-03-04 기준 백테스팅 시, 2025-03-04의 컨텍스트만 사용
- **제안**: `as_of_date` 파라미터로 historical context 조회 가능하게

## 참고: 기존 코드 경로

| 영역 | 경로 |
|------|------|
| 기술적 지표 | `backend/app/services/technical_indicators.py` |
| 스코어링 | `backend/app/services/scoring_engine.py` |
| 스코어 모델 | `backend/app/models/stock_score.py` |
| 자동매매 규칙 | `backend/app/models/auto_trading.py` |
| 거래 엔진 | `backend/app/services/trading_engine.py` |
| 자동매매 스케줄러 | `backend/app/services/auto_trade_scheduler.py` |
