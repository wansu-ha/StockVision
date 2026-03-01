# 가상 자동매매 시스템 — 기능 명세서

## 목표

StockVision에 **가상 자동매매 시스템**을 구축한다.
기존 데이터 수집(yfinance)과 기술적 지표, RF 예측 모델을 활용하여
**스코어링 → 종목 선정 → 가상 매매 → 성과 분석**의 자동화된 투자 파이프라인을 완성한다.

키움증권 REST API를 통한 실시간 데이터 수집과 yfinance 과거 데이터를 결합하여,
**가상 거래 환경**에서 전략을 검증하고 운영한다.

## 아키텍처

영상의 4계층 구조를 StockVision에 맞게 적용:

```
[1. 데이터 레이어]     yfinance(과거) + 키움증권 REST API(실시간) + 기술적 지표
        ↓
[2. 전략 레이어]       스코어링 엔진 (신규)
        ↓
[3. 분석 레이어]       백테스팅 엔진 (신규)
        ↓
[4. 실행 레이어]       가상 거래 엔진 + 스케줄러 (신규)
```

## 요구사항

### 기능적 요구사항

#### FR-1: 가상 거래 엔진
- FR-1.1: 가상 계좌 생성 (초기 자본금 설정 가능, 기본 1천만원)
- FR-1.2: 매수 주문 처리 (시장가 기준, 수수료 0.015% 적용)
- FR-1.3: 매도 주문 처리 (시장가 기준, 수수료 0.015% + 세금 0.23%)
- FR-1.4: 포지션 관리 (보유 종목, 평균 매입가, 수량, 미실현 손익)
- FR-1.5: 계좌 현황 조회 (잔고, 총 자산, 수익률, 거래 내역)

#### FR-2: 스코어링 엔진
- FR-2.1: 기술적 지표 기반 스코어 계산 (RSI, MACD, 볼린저밴드, EMA 활용)
- FR-2.2: RF 예측 모델 결과 반영 (예측 가격 변동률)
- FR-2.3: 통합 스코어 산출 (0~100점, 가중 평균)
- FR-2.4: 종목 순위 산출 (스코어 기준 상위 N개 선정)

#### FR-3: 백테스팅 엔진
- FR-3.1: 과거 데이터 기반 전략 시뮬레이션 (시작일~종료일 지정)
- FR-3.2: 성과 지표 계산 (총 수익률, 승률, 샤프비율, 최대 낙폭)
- FR-3.3: 거래별 상세 기록 (진입/청산 가격, 손익, 보유 기간)
- FR-3.4: 결과 DB 저장 및 조회

#### FR-4: 자동매매 스케줄러
- FR-4.1: 매매 전략 규칙 등록 (매수 조건, 매도 조건, 예산 비율)
- FR-4.2: 스케줄 기반 자동 실행 (장 시작 후 스코어링 → 매수, 장 마감 전 일괄 매도)
- FR-4.3: 전략 활성화/비활성화 토글
- FR-4.4: 실행 로그 기록

#### FR-5: 키움증권 REST API 연동
- FR-5.1: 키움증권 REST API 인증 (App Key/Secret 기반 토큰 발급)
- FR-5.2: 실시간 시세 조회 (현재가, 호가, 체결 데이터)
- FR-5.3: 종목 정보 조회 (코스피/코스닥 종목 목록)
- FR-5.4: 모의투자 계좌 연동 (잔고, 주문 가능 금액)
- FR-5.5: 환경 변수 기반 설정 (APP_KEY, APP_SECRET, ACCOUNT_NO)

#### FR-6: API 엔드포인트
- FR-6.1: 가상 계좌 CRUD (`/api/v1/trading/accounts`)
- FR-6.2: 수동 매수/매도 (`/api/v1/trading/orders`)
- FR-6.3: 포지션 조회 (`/api/v1/trading/positions`)
- FR-6.4: 거래 내역 조회 (`/api/v1/trading/history`)
- FR-6.5: 스코어링 실행/조회 (`/api/v1/trading/scores`)
- FR-6.6: 백테스팅 실행/결과 조회 (`/api/v1/trading/backtest`)
- FR-6.7: 자동매매 규칙 CRUD (`/api/v1/trading/rules`)

#### FR-7: 프론트엔드 페이지
- FR-7.1: 가상 거래 대시보드 (계좌 현황, 포지션, 최근 거래)
- FR-7.2: 매매 주문 폼 (종목 선택, 수량, 매수/매도)
- FR-7.3: 스코어링 결과 테이블 (순위, 종목, 점수, 신호)
- FR-7.4: 백테스팅 결과 페이지 (성과 차트, 거래 기록)
- FR-7.5: 자동매매 설정 페이지 (규칙 관리, 실행 상태)

### 비기능적 요구사항

- NFR-1: 백테스팅 1년치 데이터 처리 10초 이내
- NFR-2: 스코어링 전 종목 계산 5초 이내
- NFR-3: API 응답 200ms 이내 (백테스팅 제외)
- NFR-4: 기존 API 패턴 준수 (`{ success, data, count }` 형식)

## 수용 기준

### Phase 2 전반 (Step 1~10) — 기본 구조
- [x] 가상 계좌 생성 후 매수/매도 주문이 정상 처리되고 잔고가 정확히 반영된다
- [x] 스코어링 결과가 0~100 범위로 산출된다
- [x] 백테스팅이 과거 데이터로 전략을 시뮬레이션하고 수익률/승률/샤프비율을 출력한다
- [x] 자동매매 규칙 등록 후 스케줄에 따라 스코어링→매수→매도가 자동 실행된다
- [x] 프론트엔드에서 계좌 현황, 스코어링 결과, 백테스팅 결과를 조회할 수 있다
- [ ] 키움증권 REST API로 실시간 시세를 조회할 수 있다 (stub만 구현)
- [x] 모든 API가 기존 `{ success, data, count }` 응답 형식을 따른다

### Phase 2 후반 (Step 11~15) — 런타임 진단 후 수정
> 2026-03-01 런타임 점검에서 발견된 이슈. 기본 구조는 완성되었으나 데이터 파이프라인 단절로 실제 동작에 문제가 있음.

- [ ] 종목 등록 API로 주식을 등록하면 가격 데이터와 기술적 지표가 자동 수집/계산된다
- [ ] Dashboard, StockDetail에서 실제 가격 데이터가 원화(₩)로 표시된다
- [ ] AI 분석 컴포넌트가 실제 예측 모델 결과를 표시한다 (더미 데이터 아님)
- [ ] Trading 페이지에서 매수/매도 주문 폼을 통해 주문을 실행할 수 있다
- [ ] 백테스트 결과에 수익률 차트가 렌더링된다
- [ ] 자동매매 규칙을 UI에서 생성할 수 있다
- [ ] E2E 플로우 (종목 등록→가격확인→스코어링→매수→매도→잔고확인)가 브라우저에서 동작한다

## 범위

### 포함
- 가상 거래 엔진 (매수/매도/포지션 관리)
- 통합 스코어링 시스템 (기술적 지표 + RF 예측)
- 백테스팅 엔진 (과거 데이터 시뮬레이션)
- 자동매매 스케줄러 (APScheduler 기반)
- 키움증권 REST API 연동 (모의투자 시세 조회)
- REST API 엔드포인트
- 프론트엔드 UI (거래 대시보드, 백테스팅, 자동매매 설정)

### 미포함
- 실제 계좌 매매 실행 (Phase 4, `docs/roadmap.md` 참고)
- 실시간 WebSocket 데이터 스트리밍
- 사용자 인증/권한 시스템
- LSTM/앙상블 모델 (Phase 3에서 별도 진행)
- AI 전략 리뷰 시스템 (Phase 3, `docs/ideas.md` 참고)
- 알림 시스템 (텔레그램 봇 등)

## 런타임 진단 결과 (2026-03-01)

### 발견된 이슈 (심각도순)

| # | 심각도 | 이슈 | 원인 | 위치 |
|---|--------|------|------|------|
| 1 | 높음 | 종목 등록 경로 없음 | 데이터 수집 API 엔드포인트 미구현 | `stocks.py` |
| 2 | 높음 | 가격 데이터 `$N/A` 표시 | API 응답 포맷 불일치 (`list` vs `{prices: list}`) | `stock_data_service.py:97` |
| 3 | 높음 | `fillna()` pandas 호환 에러 | `fillna(method='ffill')` pandas 2.x에서 제거 | `prediction_model.py:104` |
| 4 | 높음 | 기술적 지표 DB 비어있음 | 데이터 수집 시 지표 계산 미연동 | `data_collector.py` |
| 5 | 중간 | AI 분석 더미 데이터 | API가 목업 데이터 반환 | `ai_analysis.py` |
| 6 | 중간 | 매수/매도 주문 폼 없음 | UI 미구현 (API는 존재) | `Trading.tsx` |
| 7 | 중간 | 규칙 생성 폼 없음 | UI 미구현 (토글만 동작) | `Trading.tsx` |
| 8 | 중간 | 백테스트 차트 없음 | Recharts 미연동 (테이블만 존재) | `Trading.tsx` |
| 9 | 낮음 | 달러($) 표시 | 한국 주식은 원화(₩) 사용 | `LiveStockCard.tsx` |
| 10 | 낮음 | Dashboard 버튼 미연결 | onClick 핸들러 없음 | `Dashboard.tsx` |
| 11 | 낮음 | sklearn 버전 불일치 | 모델 1.7.1 → 런타임 1.8.0 | `prediction_model.py` |

## DB 스키마 변경

### 기존 모델 활용 (변경 없음)
- `VirtualAccount` — 계좌 관리
- `VirtualPosition` — 포지션 관리
- `VirtualTrade` — 거래 내역
- `AutoTradingRule` — 자동매매 규칙
- `BacktestResult` — 백테스팅 결과

### 기존 모델 확장

```python
# VirtualAccount에 추가할 필드
total_profit_loss = Column(Float, default=0.0)     # 총 실현 손익
total_trades = Column(Integer, default=0)           # 총 거래 횟수
win_trades = Column(Integer, default=0)             # 수익 거래 횟수

# VirtualTrade에 추가할 필드
total_amount = Column(Float)                        # 총 거래 금액
commission = Column(Float, default=0.0)             # 수수료
tax = Column(Float, default=0.0)                    # 세금
realized_pnl = Column(Float)                        # 실현 손익 (매도 시)
symbol = Column(String(10))                         # 종목 심볼 (조회 편의)

# VirtualPosition에 추가할 필드
current_price = Column(Float)                       # 현재가
unrealized_pnl = Column(Float, default=0.0)         # 미실현 손익
symbol = Column(String(10))                         # 종목 심볼

# AutoTradingRule에 추가할 필드
account_id = Column(Integer)                        # 연결 계좌
buy_score_threshold = Column(Float, default=70.0)   # 매수 스코어 기준
max_position_count = Column(Integer, default=5)     # 최대 보유 종목 수
budget_ratio = Column(Float, default=0.7)           # 예산 사용 비율
schedule_buy = Column(String(20))                   # 매수 스케줄 (cron 표현)
schedule_sell = Column(String(20))                  # 매도 스케줄
last_executed_at = Column(DateTime)                 # 마지막 실행 시간

# BacktestResult에 추가할 필드
total_trades = Column(Integer)                      # 총 거래 횟수
win_trades = Column(Integer)                        # 수익 거래 횟수
strategy_type = Column(String(50))                  # 전략 유형
trade_details = Column(JSON)                        # 개별 거래 상세 기록
```

### 신규 모델

```python
class StockScore(Base):
    """종목 스코어링 결과 (스냅샷)"""
    __tablename__ = "stock_scores"

    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, nullable=False)
    symbol = Column(String(10), nullable=False)
    date = Column(DateTime, nullable=False)

    # 개별 지표 스코어 (0~100)
    rsi_score = Column(Float)
    macd_score = Column(Float)
    bollinger_score = Column(Float)
    ema_score = Column(Float)
    prediction_score = Column(Float)        # RF 예측 기반

    # 통합 스코어
    total_score = Column(Float, nullable=False)
    signal = Column(String(10))             # BUY, SELL, HOLD

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_score_date', 'stock_id', 'date'),
    )
```

## API 엔드포인트 스케치

### 신규 추가 (Step 11)

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/stocks/register` | 종목 등록 (yfinance 수집 + 지표 계산) |

### 기존

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/trading/accounts` | 가상 계좌 생성 |
| GET | `/api/v1/trading/accounts` | 계좌 목록 조회 |
| GET | `/api/v1/trading/accounts/{id}` | 계좌 상세 (잔고, 수익률) |
| POST | `/api/v1/trading/orders` | 매수/매도 주문 |
| GET | `/api/v1/trading/positions/{account_id}` | 포지션 조회 |
| GET | `/api/v1/trading/history/{account_id}` | 거래 내역 조회 |
| POST | `/api/v1/trading/scores/calculate` | 전 종목 스코어링 실행 |
| GET | `/api/v1/trading/scores` | 최신 스코어 조회 (순위) |
| POST | `/api/v1/trading/backtest` | 백테스팅 실행 |
| GET | `/api/v1/trading/backtest/{id}` | 백테스팅 결과 조회 |
| GET | `/api/v1/trading/backtest` | 백테스팅 결과 목록 |
| POST | `/api/v1/trading/rules` | 자동매매 규칙 등록 |
| GET | `/api/v1/trading/rules` | 규칙 목록 조회 |
| PATCH | `/api/v1/trading/rules/{id}` | 규칙 수정/활성화 토글 |
| DELETE | `/api/v1/trading/rules/{id}` | 규칙 삭제 |

## 스코어링 공식 (초안)

```
통합 스코어 = Σ(지표별 스코어 × 가중치)

가중치:
  RSI 스코어      : 0.20  (과매수/과매도 판단)
  MACD 스코어     : 0.20  (추세 전환 신호)
  볼린저밴드 스코어: 0.15  (가격 위치 판단)
  EMA 스코어      : 0.15  (추세 방향)
  RF 예측 스코어  : 0.30  (AI 예측 반영)

매수 신호: 통합 스코어 ≥ 70
매도 신호: 통합 스코어 ≤ 30
홀드:      30 < 통합 스코어 < 70
```

## 참고: 기존 코드 경로

| 영역 | 경로 | 비고 |
|------|------|------|
| DB 모델 (주식) | `backend/app/models/stock.py` | Stock, StockPrice, TechnicalIndicator |
| DB 모델 (가상거래) | `backend/app/models/virtual_trading.py` | VirtualAccount, VirtualPosition, VirtualTrade |
| DB 모델 (자동매매) | `backend/app/models/auto_trading.py` | AutoTradingRule, BacktestResult |
| 기술적 지표 | `backend/app/services/technical_indicators.py` | RSI, EMA, MACD, 볼린저밴드 |
| 예측 모델 | `backend/app/services/prediction_model.py` | RandomForest, 다음 날 종가 예측 |
| 주식 API | `backend/app/api/stocks.py` | 가격, 지표, 요약 조회 |
| DB 설정 | `backend/app/core/database.py` | SQLite, SessionLocal |
| 프론트 페이지 | `frontend/src/pages/` | Dashboard, StockDetail, StockList |
