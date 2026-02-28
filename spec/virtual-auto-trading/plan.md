# 가상 자동매매 시스템 — 구현 계획서

## 아키텍처

```
[키움증권 REST API] ──→ [KiwoomClient]
                              ↓
[yfinance] ──→ [DataCollector] ──→ [StockPrice DB]
                                        ↓
[TechnicalIndicators] ←─────────────────┘
        ↓
[ScoringEngine] ←── [PredictionModel (RF)]
        ↓
[StockScore DB] ──→ [BacktestEngine]
        ↓                   ↓
[TradingEngine]      [BacktestResult DB]
   ↓        ↓
[VirtualAccount]  [VirtualTrade/Position DB]
        ↓
[AutoTradeScheduler (APScheduler)]
        ↓
[FastAPI 라우터: /api/v1/trading/*]
        ↓
[React 프론트엔드: /trading/*]
```

### 데이터 흐름

1. **시세 수집**: KiwoomClient(실시간) + yfinance(과거) → StockPrice DB
2. **스코어링**: 기술적 지표 + RF 예측 → 통합 스코어 → StockScore DB
3. **거래 실행**: 스코어 기준 종목 선정 → TradingEngine → VirtualTrade/Position DB
4. **백테스팅**: 과거 StockPrice → ScoringEngine 시뮬레이션 → BacktestResult DB
5. **스케줄러**: APScheduler → 장 시작 후 스코어링+매수 / 장 마감 전 매도

## 수정 파일 목록

### 백엔드 — 모델 수정 (기존 파일)

| 파일 | 변경 내용 |
|------|----------|
| `backend/app/models/virtual_trading.py` | VirtualAccount에 total_profit_loss/total_trades/win_trades 추가, VirtualTrade에 total_amount/commission/tax/realized_pnl/symbol 추가, VirtualPosition에 current_price/unrealized_pnl/symbol 추가 |
| `backend/app/models/auto_trading.py` | AutoTradingRule에 account_id/buy_score_threshold/max_position_count/budget_ratio/schedule_buy/schedule_sell/last_executed_at 추가, BacktestResult에 total_trades/win_trades/strategy_type/trade_details 추가 |
| `backend/app/models/__init__.py` | StockScore import 추가 |

### 백엔드 — 모델 신규

| 파일 | 내용 |
|------|------|
| `backend/app/models/stock_score.py` | StockScore 모델 |

### 백엔드 — 서비스 신규

| 파일 | 내용 |
|------|------|
| `backend/app/services/kiwoom_client.py` | 키움증권 REST API 클라이언트 (인증, 시세 조회, 종목 정보) |
| `backend/app/services/scoring_engine.py` | 스코어링 엔진 (지표별 점수 계산, 가중 평균, 신호 판정) |
| `backend/app/services/trading_engine.py` | 가상 거래 엔진 (매수/매도 주문, 포지션 관리, 손익 계산) |
| `backend/app/services/backtest_engine.py` | 백테스팅 엔진 (과거 데이터 시뮬레이션, 성과 지표) |
| `backend/app/services/auto_trade_scheduler.py` | 자동매매 스케줄러 (APScheduler 크론잡) |

### 백엔드 — API 신규

| 파일 | 내용 |
|------|------|
| `backend/app/api/trading.py` | 가상 거래 API (계좌, 주문, 포지션, 거래 내역, 스코어링, 백테스팅, 자동매매 규칙) |

### 백엔드 — 기존 파일 수정

| 파일 | 변경 내용 |
|------|----------|
| `backend/app/main.py` | trading 라우터 등록, 스케줄러 startup/shutdown 이벤트 추가 |
| `backend/requirements.txt` | apscheduler, httpx 추가 |

### 프론트엔드 — 신규

| 파일 | 내용 |
|------|------|
| `frontend/src/types/trading.ts` | 거래 관련 타입 정의 (Account, Position, Trade, Score, BacktestResult, Rule) |
| `frontend/src/pages/Trading.tsx` | 가상 거래 대시보드 — 탭 구조로 계좌 총괄/스코어링/백테스팅/자동매매 통합 |

### 프론트엔드 — 기존 파일 수정

| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/services/api.ts` | tradingApi 객체 추가 (계좌/주문/포지션/스코어/백테스트/규칙 CRUD) |
| `frontend/src/App.tsx` | /trading 라우트 추가 |
| `frontend/src/components/Layout.tsx` | 네비게이션에 '가상 거래' 메뉴 추가 |

## 구현 순서

### Step 1: DB 모델 확장 + 신규 모델
**대상**: `virtual_trading.py`, `auto_trading.py`, `stock_score.py`, `__init__.py`
**의존성**: 없음 (독립)

작업:
- 기존 모델에 필드 추가 (spec DB 스키마 변경 섹션 기준)
- StockScore 신규 모델 생성
- DB 테이블 자동 생성 확인

verify: 백엔드 서버 기동 시 테이블 생성 로그 확인, SQLite DB에 새 컬럼/테이블 존재 확인

---

### Step 2: 키움증권 REST API 클라이언트
**대상**: `kiwoom_client.py`, `requirements.txt`
**의존성**: 없음 (독립)

작업:
- httpx 기반 비동기 HTTP 클라이언트
- 토큰 발급/갱신 (App Key/Secret)
- 현재가 조회, 종목 정보 조회 API 래핑
- 환경 변수 기반 설정 (키 없으면 graceful 비활성화)

verify: 키움 API 키 설정 시 실시간 시세 조회 성공, 키 없으면 에러 없이 비활성화

---

### Step 3: 가상 거래 엔진
**대상**: `trading_engine.py`
**의존성**: Step 1 (DB 모델)

작업:
- 계좌 생성 (초기 자본금 기본 1천만원, 설정 가능)
- 매수 처리 (잔고 차감, 포지션 생성/업데이트, 수수료 0.015%)
- 매도 처리 (포지션 감소/삭제, 잔고 증가, 수수료 0.015% + 세금 0.23%)
- 포지션 미실현 손익 업데이트
- 계좌 통계 (총 수익률, 승률)

verify: 매수→포지션 생성→매도→잔고 정확성 수동 계산 검증

---

### Step 4: 스코어링 엔진
**대상**: `scoring_engine.py`
**의존성**: Step 1 (DB 모델), 기존 `technical_indicators.py`, `prediction_model.py`

작업:
- RSI 스코어 (0~100, 과매도=높은 점수, 과매수=낮은 점수)
- MACD 스코어 (골든크로스=높은 점수)
- 볼린저밴드 스코어 (하단 근접=높은 점수)
- EMA 스코어 (상승 추세=높은 점수)
- RF 예측 스코어 (예측 상승률 기반)
- 가중 평균: RSI 0.20, MACD 0.20, 볼린저 0.15, EMA 0.15, RF 0.30
- 신호 판정: ≥70 BUY, ≤30 SELL, 그 외 HOLD
- 결과 StockScore DB 저장

verify: 알려진 기술적 지표 값으로 스코어 수동 계산 대조

---

### Step 5: 백테스팅 엔진
**대상**: `backtest_engine.py`
**의존성**: Step 3 (TradingEngine), Step 4 (ScoringEngine)

작업:
- 기간 지정 (시작일~종료일)
- 일봉 단위 시뮬레이션: 매일 스코어링→매수/매도 판단→거래 실행
- 성과 지표 계산: 총 수익률, 승률, 샤프비율, 최대 낙폭
- 거래별 상세 기록 (JSON)
- BacktestResult DB 저장

verify: 과거 1개월 데이터로 백테스팅 실행, 수익률 수동 계산 대조

---

### Step 6: 백엔드 API 라우터
**대상**: `trading.py`, `main.py`
**의존성**: Step 2~5 (모든 서비스)

작업:
- 가상 계좌 CRUD (POST/GET /accounts)
- 매수/매도 주문 (POST /orders)
- 포지션 조회 (GET /positions/{account_id})
- 거래 내역 조회 (GET /history/{account_id})
- 스코어링 실행/조회 (POST /scores/calculate, GET /scores)
- 백테스팅 실행/결과 (POST /backtest, GET /backtest/{id})
- 자동매매 규칙 CRUD (POST/GET/PATCH/DELETE /rules)
- main.py에 라우터 등록

verify: Swagger UI에서 모든 엔드포인트 호출 테스트, 응답 `{ success, data, count }` 형식 확인

---

### Step 7: 자동매매 스케줄러
**대상**: `auto_trade_scheduler.py`, `main.py`
**의존성**: Step 3~6 (거래 엔진, 스코어링, API)

작업:
- APScheduler 기반 크론잡 등록
- 매수 잡: 스코어링 실행 → 상위 N종목 매수
- 매도 잡: 보유 전 종목 일괄 매도
- 규칙 활성화/비활성화에 따라 잡 동적 추가/제거
- 실행 로그 기록
- main.py startup/shutdown 이벤트에 스케줄러 연결

verify: 테스트용 짧은 간격(1분)으로 스케줄러 실행, 로그에서 매수/매도 실행 확인

---

### Step 8: 프론트엔드 타입 + API 클라이언트
**대상**: `trading.ts`, `tradingApi.ts`
**의존성**: Step 6 (백엔드 API 완성 후)

작업:
- 타입 정의: VirtualAccount, VirtualPosition, VirtualTrade, StockScore, BacktestResult, AutoTradingRule
- API 클라이언트: 기존 axios 인스턴스 활용, tradingApi 객체로 모듈화
- React Query 키 규칙 준수

verify: `npm run build` (TypeScript 컴파일 에러 없음)

---

### Step 9: 프론트엔드 페이지 — 가상 거래 대시보드
**대상**: `Trading.tsx`, `App.tsx`, `Layout.tsx`
**의존성**: Step 8

작업:
- 계좌 현황 카드 (잔고, 총 자산, 수익률)
- 포지션 테이블 (종목, 수량, 평균가, 현재가, 손익)
- 최근 거래 내역
- 매수/매도 주문 폼 (종목 검색, 수량 입력)
- App.tsx에 /trading 라우트 추가
- Layout.tsx 네비게이션에 메뉴 추가

verify: 브라우저에서 /trading 접속, 계좌 생성→매수→포지션 확인→매도 플로우 동작

---

### Step 10: 프론트엔드 페이지 — 스코어링, 백테스팅, 자동매매
**대상**: `Scores.tsx`, `Backtest.tsx`, `AutoTrading.tsx`, `App.tsx`
**의존성**: Step 8, Step 9

작업:
- Scores.tsx: 종목 스코어 순위 테이블, 스코어링 실행 버튼, BUY/SELL/HOLD 신호 Chip
- Backtest.tsx: 기간 선택 폼, 실행 버튼, 결과 차트 (수익률 곡선 Recharts), 성과 지표 카드, 거래 기록 테이블
- AutoTrading.tsx: 규칙 목록, 추가/수정 모달, 활성화 토글, 실행 로그
- App.tsx에 /scores, /backtest, /auto-trading 라우트 추가

verify: 각 페이지 접속 및 기능 동작 확인, 백테스팅 결과 차트 렌더링 확인

---

## 검증 방법

### 빌드 확인
```bash
# 백엔드
cd backend && python -m uvicorn app.main:app --reload
# 프론트엔드
cd frontend && npm run build && npm run dev
```

### API 테스트 (Swagger UI)
1. 계좌 생성 → 매수 → 포지션 확인 → 매도 → 잔고 확인
2. 스코어링 실행 → 순위 조회
3. 백테스팅 실행 → 결과 조회
4. 자동매매 규칙 등록 → 활성화 → 실행 로그 확인

### 브라우저 확인
- `/trading` — 대시보드 렌더링, 주문 폼 동작
- `/scores` — 스코어 테이블 렌더링
- `/backtest` — 차트 렌더링, 성과 지표 표시
- `/auto-trading` — 규칙 관리, 토글 동작
