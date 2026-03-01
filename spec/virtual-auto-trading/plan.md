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

## Phase 2 후반: 런타임 진단 기반 수정 (Step 11~15)

> 2026-03-01 런타임 점검 결과 발견된 10개 이슈를 우선순위별로 수정.
> 근본 원인: 데이터 파이프라인이 끊겨 있어 모든 하위 기능이 빈 데이터로 동작.

### Step 11: 데이터 파이프라인 정비
**대상**: `data_collector.py`, `prediction_model.py`, `stocks.py` (API), `stock_data_service.py`
**의존성**: 없음 (최우선)

문제:
- 종목 등록 경로 없음 — DB가 비어 있으면 모든 기능 실패
- yfinance 한국 주식은 `.KS` suffix 필요하나 매핑 없음
- `fillna(method='ffill')` → pandas 2.x에서 제거됨 (`prediction_model.py:104`)
- 기술적 지표가 DB에 저장되지 않음 — 스코어링이 예측 점수만으로 동작

작업:
1. `POST /api/v1/stocks/register` 엔드포인트 추가
   - 입력: `{ symbols: ["005930", "000660"] }`
   - yfinance에서 종목 정보 수집 → Stock DB 저장
   - 가격 데이터 수집 → StockPrice DB 저장
   - 기술적 지표 계산 → TechnicalIndicator DB 저장
2. 한국 주식 심볼 매핑 유틸 (`005930` → `005930.KS`)
3. `prediction_model.py:104` 수정: `fillna(method='ffill')` → `ffill()`
4. `collect_and_save()`에 지표 계산 단계 추가
5. 개발용 seed 스크립트 (`backend/scripts/seed_data.py`)

수정 파일:

| 파일 | 변경 내용 |
|------|----------|
| `backend/app/api/stocks.py` | `POST /stocks/register` 엔드포인트 추가 |
| `backend/app/services/data_collector.py` | 심볼 매핑 유틸, `collect_and_save()`에 지표 계산 통합 |
| `backend/app/services/prediction_model.py` | `fillna(method='ffill')` → `ffill()` |
| `backend/scripts/seed_data.py` | 신규: 개발용 seed 스크립트 |

verify:
- `POST /api/v1/stocks/register` 호출 → Stock, StockPrice, TechnicalIndicator 테이블에 데이터 존재 확인
- `GET /api/v1/stocks/` → 등록한 종목 목록 반환
- prediction_model.py 에러 없이 특성 준비 완료

---

### Step 12: API 응답 포맷 + 프론트엔드 데이터 표시 수정
**대상**: `stock_data_service.py`, `stocks.py`, `LiveStockCard.tsx`, `StockDetail.tsx`, `Dashboard.tsx`
**의존성**: Step 11 (DB에 데이터 필요)

문제:
- `/stocks/{symbol}/prices` 응답이 리스트를 직접 반환하나, 프론트엔드는 `{ symbol, name, prices: [] }` 형태를 기대
- `stock_data_service.get_stock_data()` 97번째 줄: `result` dict 대신 `stored_data` 리스트 반환
- 가격 표시가 `$` (달러) — 한국 주식은 `₩` (원화) 사용
- Dashboard 카드에서 가격이 `$N/A`로 표시

작업:
1. `stock_data_service.get_stock_data()` 반환값 통일: `{ symbol, name, prices: [...] }`
2. `/stocks/{symbol}/prices` 응답 포맷 수정: `{ success, data: { symbol, name, prices } }`
3. 프론트엔드 가격 포맷 함수: `$` → `₩`, 천 단위 콤마
4. `LiveStockCard.tsx` 가격 표시 로직 수정
5. `StockDetail.tsx` 차트 데이터 바인딩 수정

수정 파일:

| 파일 | 변경 내용 |
|------|----------|
| `backend/app/services/stock_data_service.py` | `get_stock_data()` 반환값 `{ symbol, name, prices }` 형태로 통일 |
| `backend/app/api/stocks.py` | `/prices` 응답에 symbol, name 포함 |
| `frontend/src/components/LiveStockCard.tsx` | `$` → `₩`, 가격 포맷 함수 적용 |
| `frontend/src/pages/StockDetail.tsx` | 원화 표시, 차트 데이터 바인딩 확인 |
| `frontend/src/pages/Dashboard.tsx` | 원화 표시 |

verify:
- 브라우저 Dashboard에서 종목 카드에 실제 가격 표시 (₩ 단위)
- StockDetail 페이지에서 차트 렌더링 확인
- API 응답 형태: `{ success: true, data: { symbol, name, prices: [...] } }`

---

### Step 13: AI 분석 실제 데이터 연동
**대상**: `AIMarketOverview.tsx`, `AIStockAnalysis.tsx`, `ai_analysis.py` (API), `prediction_model.py`
**의존성**: Step 11 (지표 데이터), Step 12 (API 응답 정상화)

문제:
- `AIMarketOverview`, `AIStockAnalysis` 컴포넌트가 랜덤/더미 데이터 표시
- AI 분석 API가 실제 예측 모델 결과 대신 목업 데이터 반환
- sklearn 모델 버전 불일치 경고 (1.7.1 → 1.8.0)

작업:
1. AI 분석 API 엔드포인트가 실제 `PredictionModel` 결과 반환하도록 수정
2. 시장 개요: 등록된 전 종목의 스코어링 결과 집계
3. 종목별 AI 분석: RF 예측 + 기술적 지표 종합 분석 반환
4. sklearn 모델 재학습 또는 버전 호환 처리
5. 프론트엔드 컴포넌트가 실제 API 데이터 표시하도록 연결

수정 파일:

| 파일 | 변경 내용 |
|------|----------|
| `backend/app/api/ai_analysis.py` | 더미 데이터 → 실제 PredictionModel/ScoringEngine 결과 연동 |
| `backend/app/services/prediction_model.py` | sklearn 호환 처리, 모델 재학습 로직 |
| `frontend/src/components/AIMarketOverview.tsx` | API 데이터 바인딩 확인 |
| `frontend/src/components/AIStockAnalysis.tsx` | API 데이터 바인딩 확인 |

verify:
- Dashboard AI 분석 카드에 실제 시장 분석 데이터 표시
- StockDetail AI 분석 탭에 해당 종목의 예측 결과 표시
- 콘솔에 sklearn 경고 없음

---

### Step 14: 거래 UI 완성
**대상**: `Trading.tsx`, `Dashboard.tsx`
**의존성**: Step 11 (종목 데이터), Step 12 (가격 표시)

문제:
- 매수/매도 주문 폼 없음 (API는 존재)
- 자동매매 규칙 생성 폼 없음 (토글만 동작)
- 백테스트 결과에 수익률 차트 없음 (테이블만 존재)
- Dashboard 버튼 (AI 분석, 가상 거래 등)에 클릭 핸들러 없음

작업:
1. Overview 탭: 매수/매도 주문 폼 추가
   - 종목 검색/선택, 수량 입력, 가격 표시
   - BUY/SELL 버튼 + React Query mutation
2. Backtest 탭: Recharts `LineChart`로 수익률 곡선 시각화
   - equity_curve 데이터 바인딩
   - trade_details에서 매수/매도 마커
3. Rules 탭: 규칙 생성 모달/폼
   - 종목 선택, 매수/매도 스코어 임계값, 예산 비율
4. Dashboard: 버튼 핸들러 연결 (navigate)

수정 파일:

| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/pages/Trading.tsx` | 주문 폼, 백테스트 차트, 규칙 생성 폼 추가 |
| `frontend/src/pages/Dashboard.tsx` | 버튼 클릭 핸들러 연결 |

verify:
- Trading Overview에서 매수 주문 → 포지션 목록에 표시
- Backtest 실행 → 수익률 차트 렌더링
- Rules에서 새 규칙 생성 → 목록에 표시
- Dashboard 버튼 클릭 시 해당 페이지 이동

---

### Step 15: 통합 테스트 + 안정화
**대상**: 전체
**의존성**: Step 11~14

작업:
1. E2E 플로우 테스트:
   - 종목 등록 → 가격 확인 → 스코어링 → 매수 → 포지션 확인 → 매도 → 잔고 확인
   - 백테스트 실행 → 결과 차트 확인
   - 자동매매 규칙 등록 → 활성화 → 실행 확인
2. 에러 핸들링:
   - API 실패 시 프론트엔드 에러 메시지 표시 (빈 화면 방지)
   - toast 알림 (주문 성공/실패, 스코어링 완료 등)
3. 빌드 확인:
   - `npm run build` TypeScript 에러 없음
   - `npm run lint` 경고 최소화
   - 백엔드 서버 기동 시 에러 없음

verify:
- 전체 플로우 브라우저에서 수동 테스트 통과
- `npm run build` 성공
- 백엔드 로그에 에러 없음

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
1. 종목 등록 → 주식 목록 확인 → 가격 데이터 확인 → 기술적 지표 확인
2. 계좌 생성 → 매수 → 포지션 확인 → 매도 → 잔고 확인
3. 스코어링 실행 → 순위 조회
4. 백테스팅 실행 → 결과 조회
5. 자동매매 규칙 등록 → 활성화 → 실행 로그 확인

### 브라우저 확인
- `/` — Dashboard: AI 분석 카드, 종목 카드에 실제 가격 (₩)
- `/stocks/{symbol}` — 가격 차트, 기술적 지표, AI 분석
- `/trading` — 계좌 현황, 주문 폼, 포지션, 거래 내역
- `/trading` (Scores 탭) — 스코어 테이블, BUY/SELL/HOLD 신호
- `/trading` (Backtest 탭) — 수익률 차트, 성과 지표
- `/trading` (Rules 탭) — 규칙 생성, 활성화 토글
