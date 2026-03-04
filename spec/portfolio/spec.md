# 포트폴리오 조회 기능 명세서 (portfolio)

> 작성일: 2026-03-04 | 상태: 초안 | 범위: Phase 2 후반 (Step 11~15)

---

## 1. 개요

StockVision 사용자가 **현재 보유한 종목, 자산 배분, 수익률 현황**을 한눈에 파악할 수 있는 종합 포트폴리오 조회 기능이다.

**핵심 목표:**
- 가상 거래 계좌의 **실시간 포지션 현황** 조회 (현재가 기반 평가손익)
- 전략별 매매 기여도 분석 (어떤 자동매매 규칙이 어떤 종목을 보유했는지)
- 수익률 시계열 차트 (일/주/월 단위)
- 자산 배분 시각화 (섹터별, 종목별 비중)

**기존 기능과의 관계:**
- Trading 페이지: 수동 매수/매도 + 거래 내역 조회
- Portfolio 페이지(신규): 종합 자산 현황 + 분석
- Dashboard: 핵심 지표만 요약

---

## 2. 사용자 시나리오

### 시나리오 1: 포트폴리오 요약 조회
```
1. Portfolio 페이지 접속
2. "계좌 선택" 드롭다운에서 가상 계좌 선택
3. 포트폴리오 요약 카드 확인
   - 총 자산: 1,050만원
   - 수익률: +5.2% (평가 + 실현 손익)
   - 보유 종목: 5개
   - 최대 낙폭: -8.3%
4. 현재 포지션 테이블 확인
   - 종목, 수량, 평균 단가, 현재가, 평가손익, 비중(%)
```

### 시나리오 2: 전략별 포트폴리오 분석
```
1. Portfolio 페이지의 "전략별 기여도" 탭 클릭
2. 등록된 자동매매 규칙 목록 표시
   - 규칙명: "수익 추적 전략"
   - 상태: 활성화
   - 보유 종목: 3개 (삼성전자, SK하이닉스, NAVER)
   - 총 평가 손익: +520,000원
   - 수익률: +6.2%
3. 규칙별 거래 이력 클릭 → 해당 규칙으로 체결된 거래만 필터링
```

### 시나리오 3: 수익률 차트 조회
```
1. Portfolio 페이지의 "수익률 차트" 섹션
2. 기간 선택 버튼 (1주, 1개월, 3개월, 1년, 전체)
3. 라인 차트 렌더링 (Recharts)
   - X축: 날짜 (최근 30일 각 거래일)
   - Y축: 누적 수익률(%)
   - 곡선: 포트폴리오 누적 수익률 변화 추이
```

### 시나리오 4: 자산 배분 시각화
```
1. Portfolio 페이지의 "자산 배분" 섹션
2. 섹터별 도넛 차트
   - IT: 45.2%
   - 금융: 22.5%
   - 화학: 18.8%
   - 기타: 13.5%
3. 종목별 도넛 차트
   - 삼성전자: 35%
   - SK하이닉스: 20%
   - NAVER: 15%
   - 기타 (2개): 30%
```

### 시나리오 5: 현금 현황 확인
```
1. Portfolio 페이지의 "자산 구성" 섹션
2. 보유 현금, 보유 주식 평가액, 총 자산 표시
   - 보유 현금: 2,000,000원
   - 보유 주식 평가액: 8,500,000원
   - 총 자산: 10,500,000원
3. 예비자금 비율: 19.0% (추천: 10~20%)
```

---

## 3. 화면 구성

### 3.1 Portfolio 페이지 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ Portfolio                    [계좌 선택 ▼]  [기간 선택 ▼]     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐
│  │ 총 자산      │ 수익률       │ 보유 종목    │ 최대 낙폭    │
│  │ 10,500,000₩ │ +5.2% (연)   │ 5개         │ -8.3%       │
│  └──────────────┴──────────────┴──────────────┴──────────────┘
│                                                               │
│  ┌───────────────────────┬────────────────────────────────────┐
│  │ 현재 포지션           │ 자산 배분                          │
│  │                       │ [섹터별 도넛]  [종목별 도넛]      │
│  │ 종목     수량  평균단가 현재가  평가손익   비중            │
│  │ 삼성전자  100  75,000  76,500 +150k  33%                │
│  │ SK하이닉스 50 110,000 112,000  +100k  20%              │
│  │ NAVER    10  250,000 260,000   +100k  15%              │
│  │ ...                                                      │
│  └───────────────────────┴────────────────────────────────────┘
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐
│  │ 수익률 차트 (최근 30일)                                  │
│  │                 /‾‾‾‾\___/‾‾‾‾                         │
│  │ 0%         ___/              \___                        │
│  │       ____/                       \___                  │
│  │ -10% /                                \___              │
│  │ ────────────────────────────────────────────────        │
│  │ 1W  1M  3M  1Y  전체                                   │
│  └─────────────────────────────────────────────────────────┘
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐
│  │ 전략별 기여도                                            │
│  │                                                          │
│  │ 규칙1: "수익추적"        보유종목 3개   수익률 +6.2%    │
│  │ 규칙2: "저가매수"        보유종목 2개   수익률 +2.1%    │
│  └──────────────────────────────────────────────────────────┘
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 포트폴리오 컴포넌트 계층

```
<Portfolio>
  ├── <AccountSelector />          # 계좌 선택 드롭다운
  ├── <PeriodSelector />           # 기간 선택 (1W/1M/3M/1Y/전체)
  ├── <SummaryCards />             # 총자산, 수익률, 보유종목, 최대낙폭
  ├── <CurrentPositions />         # 현재 포지션 테이블 (정렬/필터링)
  ├── <AssetAllocation />          # 섹터별/종목별 도넛 차트
  ├── <ReturnChart />              # 수익률 시계열 라인 차트 (Recharts)
  ├── <CashPosition />             # 현금 현황 (보유 현금, 예비자금 비율)
  └── <StrategyContribution />     # 전략별 기여도 테이블
```

---

## 4. 데이터 소스 및 갱신 전략

### 4.1 데이터 소스

| 항목 | 출처 | 갱신 주기 | 비고 |
|------|------|---------|------|
| **보유 종목/수량** | `VirtualPosition` DB | 실시간 (거래 즉시) | 가상 계좌의 현재 포지션 |
| **현재가** | yfinance + 로컬 브릿지 | 5분 (증시 시간) | 또는 마지막 체결가 |
| **평가손익** | `(현재가 - 평균매입가) × 수량` | 실시간 | 클라이언트 사이드 계산 |
| **거래 내역** | `VirtualTrade` DB | 실시간 (거래 즉시) | 매수/매도 체결 기록 |
| **전략별 매매** | `AutoTradingRule` + `VirtualTrade.rule_id` | 실시간 | FK 연계 필요 |
| **섹터 정보** | Stock 모델의 `sector` 필드 | 정적 | 종목 등록 시점 고정 |

### 4.2 DB 모델 확장

#### VirtualPosition에 추가
```python
# 전략 추적을 위한 FK
rule_id = Column(Integer, ForeignKey('auto_trading_rules.id'), nullable=True)
# 포지션 생성 시각
acquired_at = Column(DateTime, nullable=False)
# 보유 기간 최대 수익률 (드로우다운 분석용)
peak_price = Column(Float, nullable=True)
```

#### VirtualTrade 확인사항
```python
# 이미 존재하는 필드 (수정 불필요)
realized_pnl     # 매도 시 실현 손익
rule_id          # 거래를 발생시킨 자동매매 규칙 (선택사항)
```

#### BacktestResult (포트폴리오 성과 추적)
```python
# 백테스트가 아닌 실제 거래의 누적 성과 기록용 신규 모델
class PortfolioSnapshot(Base):
    """포트폴리오 일일 스냅샷 (누적 수익률 추적)"""
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey('virtual_accounts.id'), nullable=False)
    snapshot_date = Column(Date, nullable=False)

    # 평가 지표
    total_portfolio_value = Column(Float)      # 총 자산액
    cash_balance = Column(Float)               # 보유 현금
    position_value = Column(Float)             # 주식 평가액
    cumulative_return_pct = Column(Float)      # 누적 수익률(%)
    realized_pnl = Column(Float)               # 실현 손익
    unrealized_pnl = Column(Float)             # 미실현 손익

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_snapshot_account_date', 'account_id', 'snapshot_date'),
    )
```

### 4.3 갱신 전략

**실시간 갱신 (클라이언트):**
- 현재가: 5분마다 폴링 (React Query staleTime)
- 평가손익: 현재가 변경 시 자동 재계산
- 수익률: 백엔드에서 캐시된 스냅샷 + 클라이언트 라이브 계산

**배치 갱신 (서버):**
- `PortfolioSnapshot`: 매일 장 마감 후 1회 기록
- 캐시: Redis에 1시간 TTL로 저장

---

## 5. 전략별 기여도 분석

### 5.1 분석 구조

```
AutoTradingRule (규칙)
  ├─ rule_id: 1
  ├─ name: "수익추적 전략"
  ├─ status: "ACTIVE"
  └─ VirtualTrade (거래)
      ├─ [거래1] 삼성전자 매수 (2026-02-15) → 보유 중
      ├─ [거래2] SK하이닉스 매수 (2026-02-20) → 보유 중
      ├─ [거래3] LG전자 매도 (2026-02-28) → 실현 손익 +50k
      └─ [거래4] NAVER 매수 (2026-03-01) → 보유 중
```

### 5.2 전략별 기여도 메트릭

| 메트릭 | 계산식 | 용도 |
|--------|--------|------|
| **보유 종목 수** | COUNT(VirtualPosition WHERE rule_id = X) | 규칙의 현재 포지션 수 |
| **총 평가손익** | SUM(VirtualPosition WHERE rule_id = X의 unrealized_pnl) | 규칙의 현재 손익 |
| **총 실현손익** | SUM(VirtualTrade WHERE rule_id = X AND trade_type = 'SELL'의 realized_pnl) | 규칙의 청산 손익 |
| **규칙별 수익률** | (평가손익 + 실현손익) / 규칙이 투입한 총자금 × 100 | 규칙의 성과율 |
| **거래 횟수** | COUNT(VirtualTrade WHERE rule_id = X) | 규칙의 활동성 |
| **승률** | COUNT(...WHERE realized_pnl > 0) / COUNT(거래) × 100 | 수익 거래 비율 |

### 5.3 규칙이 없는 거래

- `rule_id = NULL`: 수동 매수/매도 거래
- Portfolio 페이지에서 "수동 거래" 항목으로 분류

---

## 6. 기술 요구사항

### 6.1 새 API 엔드포인트

| Method | Path | 설명 | 응답 포맷 |
|--------|------|------|---------|
| GET | `/api/v1/portfolio/{account_id}` | 포트폴리오 요약 | `{ success, data: {...}, count }` |
| GET | `/api/v1/portfolio/{account_id}/positions` | 현재 포지션 | `{ success, data: [...], count }` |
| GET | `/api/v1/portfolio/{account_id}/snapshot` | 일일 스냅샷 (수익률) | `{ success, data: [...], count }` |
| GET | `/api/v1/portfolio/{account_id}/strategy-contribution` | 전략별 기여도 | `{ success, data: [...], count }` |
| GET | `/api/v1/portfolio/{account_id}/asset-allocation` | 섹터/종목별 비중 | `{ success, data: {...}, count }` |

### 6.2 API 응답 예시

#### `/api/v1/portfolio/{account_id}`
```json
{
  "success": true,
  "data": {
    "account_id": 1,
    "account_name": "My Portfolio",
    "total_portfolio_value": 10500000,
    "cash_balance": 2000000,
    "position_value": 8500000,
    "cumulative_return_pct": 5.2,
    "realized_pnl": 100000,
    "unrealized_pnl": 420000,
    "max_drawdown_pct": -8.3,
    "position_count": 5,
    "sharpe_ratio": 1.28,
    "updated_at": "2026-03-04T15:30:00Z"
  },
  "count": 1
}
```

#### `/api/v1/portfolio/{account_id}/positions`
```json
{
  "success": true,
  "data": [
    {
      "position_id": 101,
      "stock_id": 5,
      "symbol": "005930",
      "stock_name": "삼성전자",
      "quantity": 100,
      "average_price": 75000,
      "current_price": 76500,
      "position_value": 7650000,
      "unrealized_pnl": 150000,
      "pnl_pct": 2.0,
      "weight_pct": 33.0,
      "sector": "IT",
      "acquired_at": "2026-02-15T10:30:00Z",
      "rule_id": 1,
      "rule_name": "수익추적 전략"
    },
    ...
  ],
  "count": 5
}
```

#### `/api/v1/portfolio/{account_id}/snapshot?period=30d`
```json
{
  "success": true,
  "data": [
    {
      "date": "2026-02-03",
      "total_portfolio_value": 10200000,
      "cumulative_return_pct": 2.0,
      "realized_pnl": 0,
      "unrealized_pnl": 200000
    },
    {
      "date": "2026-02-04",
      "total_portfolio_value": 10150000,
      "cumulative_return_pct": 1.5,
      "realized_pnl": 0,
      "unrealized_pnl": 150000
    },
    ...
  ],
  "count": 30
}
```

#### `/api/v1/portfolio/{account_id}/strategy-contribution`
```json
{
  "success": true,
  "data": [
    {
      "rule_id": 1,
      "rule_name": "수익추적 전략",
      "status": "ACTIVE",
      "position_count": 3,
      "total_pnl": 520000,
      "realized_pnl": 150000,
      "unrealized_pnl": 370000,
      "pnl_pct": 6.2,
      "trade_count": 8,
      "win_count": 6,
      "win_rate_pct": 75.0,
      "stocks": [
        { "symbol": "005930", "name": "삼성전자", "weight_pct": 35.0 },
        { "symbol": "000660", "name": "SK하이닉스", "weight_pct": 20.0 },
        { "symbol": "035420", "name": "NAVER", "weight_pct": 15.0 }
      ]
    },
    {
      "rule_id": null,
      "rule_name": "수동거래",
      "position_count": 2,
      "total_pnl": 100000,
      "realized_pnl": -50000,
      "unrealized_pnl": 150000,
      "pnl_pct": 2.5,
      "trade_count": 4,
      "win_count": 2,
      "win_rate_pct": 50.0,
      "stocks": [...]
    }
  ],
  "count": 2
}
```

#### `/api/v1/portfolio/{account_id}/asset-allocation`
```json
{
  "success": true,
  "data": {
    "by_sector": [
      { "sector": "IT", "value": 4750000, "weight_pct": 45.2 },
      { "sector": "금융", "value": 2362500, "weight_pct": 22.5 },
      { "sector": "화학", "value": 1974000, "weight_pct": 18.8 },
      { "sector": "기타", "value": 1413500, "weight_pct": 13.5 }
    ],
    "by_stock": [
      { "symbol": "005930", "name": "삼성전자", "value": 3675000, "weight_pct": 35.0 },
      { "symbol": "000660", "name": "SK하이닉스", "value": 2100000, "weight_pct": 20.0 },
      { "symbol": "035420", "name": "NAVER", "value": 1575000, "weight_pct": 15.0 },
      { "symbol": "기타", "quantity": 2, "value": 3150000, "weight_pct": 30.0 }
    ],
    "cash": {
      "balance": 2000000,
      "weight_pct": 19.0
    }
  },
  "count": 1
}
```

### 6.3 프론트엔드 페이지

**파일:**
- `frontend/src/pages/Portfolio.tsx` (신규)
- `frontend/src/services/portfolioAPI.ts` (신규)
- `frontend/src/components/Portfolio/` (여러 서브컴포넌트)

**라이브러리:**
- **Recharts**: 수익률 차트, 섹터/종목별 도넛 차트
- **React Table**: 포지션 테이블 (정렬, 필터링)
- **React Query**: 캐싱 + 실시간 갱신

### 6.4 백엔드 구현

**파일:**
- `backend/app/api/portfolio.py` (신규, 5개 엔드포인트)
- `backend/app/services/portfolio_service.py` (신규, 비즈니스 로직)
- `backend/app/models/portfolio.py` (신규, `PortfolioSnapshot` 모델)

**핵심 로직:**
```python
# portfolio_service.py

def get_portfolio_summary(account_id: int):
    """포트폴리오 요약 (총 자산, 수익률, 최대 낙폭)"""
    # 1. account 조회
    # 2. 모든 position 조회
    # 3. 각 position의 current_price 폴링 (yfinance)
    # 4. unrealized_pnl 계산
    # 5. realized_pnl sum (완료 거래)
    # 6. max_drawdown 계산 (PortfolioSnapshot 시계열 이용)
    return {...}

def get_current_positions(account_id: int):
    """현재 포지션 (stock_id, quantity, avg_price, current_price 등)"""
    # LEFT JOIN with Stock, TechnicalIndicator, sector info
    return [...]

def get_portfolio_snapshot(account_id: int, period: str):
    """수익률 차트 데이터 (일일 스냅샷)"""
    # 1. PortfolioSnapshot에서 period에 해당하는 행 조회
    # 2. 최신 스냅샷이 없으면 오늘 것 신규 생성
    return [...]

def get_strategy_contribution(account_id: int):
    """전략별 기여도 (rule별 수익률, 거래횟수 등)"""
    # GROUP BY rule_id
    # 각 rule의 positions, trades 조회
    # pnl, win_rate 계산
    return [...]

def get_asset_allocation(account_id: int):
    """자산 배분 (sector별, stock별 비중)"""
    # by_sector: GROUP BY stock.sector
    # by_stock: 보유 position 정렬
    # cash: cash_balance / total_value
    return {...}

# 일일 배치 작업 (Scheduler)
async def create_daily_portfolio_snapshot(account_id: int):
    """매일 장 마감 후 실행 (19:00)"""
    # 오늘 스냅샷이 없으면 생성
    # cumulative_return_pct, realized_pnl, unrealized_pnl 계산
    # DB 저장
```

### 6.5 성능 요구사항

- NFR-1: 포트폴리오 요약 조회 응답 시간 < 200ms (현재가 캐시 이용)
- NFR-2: 전략별 기여도 GROUP BY 쿼리 < 500ms
- NFR-3: 수익률 차트 (최근 365일) 렌더링 < 1초

### 6.6 캐싱 전략 (Redis)

```python
# 1시간 TTL로 캐시
cache_key = f"portfolio:{account_id}:summary"
cache_key = f"portfolio:{account_id}:positions"
cache_key = f"portfolio:{account_id}:strategy_contribution"

# 현재가 갱신 시 무효화
def invalidate_portfolio_cache(account_id: int):
    # 관련 모든 캐시 키 삭제
```

---

## 7. 법적/기술 고려사항

### 7.1 키움증권 API 제약

**현행 규정 (G5 제5조③):**
> API 제공자(키움)가 제공한 시세 데이터를 서버를 통해 중계하거나 재판매 금지

**StockVision 준수 방안:**
- 현재가는 **사용자 로컬 브릿지**를 통해 취득 (서버 미중계)
- 또는 yfinance 등 **오픈소스 데이터** 활용
- Portfolio 페이지의 "현재가"는 프론트엔드 폴링 기반

### 7.2 데이터 보호

- 포트폴리오 데이터는 사용자 계정에 종속
- 인증 없이 타사용자 포트폴리오 조회 불가 (권한 검증)

---

## 8. 마이그레이션 (기존 거래 데이터)

### 8.1 과거 거래 스냅샷 재구성 (선택사항)

기존 `VirtualTrade` 데이터가 있다면, `PortfolioSnapshot` 역사 데이터 생성:

```python
# 초기화 배치 작업
def backfill_portfolio_snapshots():
    """과거 거래 데이터를 기반으로 일일 스냅샷 재구성"""
    # VirtualTrade를 날짜 순으로 정렬
    # 매일 시점의 position 상태 시뮬레이션
    # 각 날짜별 PortfolioSnapshot 생성
    # (과거 "현재가" 데이터가 없으면 매매 당시 가격 사용)
```

### 8.2 점진적 도입

1. **Phase 2-1 (즉시)**: 포트폴리오 조회 API + 페이지 (현재 데이터만)
2. **Phase 2-2 (선택)**: 과거 스냅샷 역사 재구성 (선택사항, 정확도 부족)
3. **Phase 3**: 실시간 WebSocket 스트리밍 추가

---

## 9. 미결 사항 및 TBD

| 항목 | 상태 | 우선도 | 비고 |
|------|------|--------|------|
| **현재가 데이터 소스** | TBD | 높음 | yfinance vs 로컬브릿지 vs Kiwoom API |
| **과거 스냅샷 정확도** | TBD | 중간 | 과거 "현재가" 수집 전략 부재 |
| **실시간 WebSocket** | TBD | 낮음 | Phase 3 예정 |
| **모바일 반응형** | TBD | 낮음 | Recharts 모바일 차트 최적화 |
| **데이터 감시 알림** | TBD | 낮음 | 수익률 임계값 도달 시 알림 (Phase 4) |

---

## 10. 수용 기준

### Phase 2-1: 기본 포트폴리오 조회

- [ ] Portfolio 페이지 렌더링 (총 자산, 수익률, 최대 낙폭 카드)
- [ ] 현재 포지션 테이블 조회 가능 (정렬, 필터링)
- [ ] 섹터별/종목별 도넛 차트 렌더링
- [ ] 수익률 라인 차트 (최근 30일) 표시
- [ ] API 응답 형식 `{ success, data, count }` 준수
- [ ] 계좌 선택 드롭다운 정상 작동
- [ ] 응답 시간 < 200ms (캐시 이용)

### Phase 2-2: 전략별 분석 (선택사항)

- [ ] 전략별 기여도 테이블 표시
- [ ] 규칙별 손익, 거래횟수, 승률 계산 정확
- [ ] "수동 거래" 카테고리 분리
- [ ] 규칙 클릭 → 해당 거래 필터링

### Phase 2-3: 성능 개선 (선택사항)

- [ ] Redis 캐싱 적용 (1시간 TTL)
- [ ] 일일 스냅샷 자동 생성 배치 작업
- [ ] 모바일 반응형 대응

---

## 참고: 기존 코드 경로

| 영역 | 경로 | 비고 |
|------|------|------|
| DB 모델 (가상거래) | `backend/app/models/virtual_trading.py` | VirtualAccount, VirtualPosition, VirtualTrade |
| DB 모델 (자동매매) | `backend/app/models/auto_trading.py` | AutoTradingRule, BacktestResult |
| 기술적 지표 | `backend/app/services/technical_indicators.py` | RSI, EMA, MACD, 볼린저밴드 |
| 거래 API | `backend/app/api/trading.py` | orders, positions, history |
| 프론트 페이지 | `frontend/src/pages/` | Dashboard, StockDetail, StockList, Trading |
| API 응답 포맷 | `backend/app/core/utils.py` | response() 함수 (success, data, count) |

---

**다음 단계:** `/plan` 작성 → 구현 로드맵 및 Step별 작업 목록 정의
