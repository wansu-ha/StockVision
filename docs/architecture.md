# 🧭 StockVision 아키텍처 설계(개선안)

## 🎯 목표와 제약
- 목표: 예측(ML) + 가상 투자(거래/백테스트)로 전략을 안전하게 검증 후 실제 투자 전 성숙도 확보
- 제약: 초기 1인 개발, 8주 MVP, 외부 유료 API 최소화, 운영 복잡도 억제
- 원칙: MVP 우선(일봉→분봉), 단순 체결 모델→현실성 고도화, 배치→실시간 단계적 전환

## 🚩 MVP 범위(현실적)
- 데이터: 일봉 OHLCV(1~5년), 관심 종목 소수(<=50)
- 분석: RSI/EMA/MACD 등 기본 지표 + 간단 신호 결합
- 모델: 베이스라인(RandomForest/LogReg)부터, LSTM은 후순위
- 거래: 가상 거래(시장가/지정가 on close), 고정 수수료·슬리피지, 포지션 1종류(롱)
- 백테스트: 바-클로즈 체결, 일봉 단위, 성과지표(Sharpe/MDD/승률/PF)
- 프론트: 대시보드/주식 상세/가상 거래 3페이지 + 최소 UI

---

## 🧩 모듈 경계(도메인 중심)
- 데이터 수집(ingestion): 외부 API → `stocks`, `stock_prices` 저장, 기본 검증/보정
- 지표/신호(engineering): `technical_indicators`, `signals` 생성
- 예측(ml-serving): 특징 집계 → 모델 추론 → `predictions` 저장
- 거래(trading): 주문/체결/포지션/계정/리스크 → `virtual_*` 테이블 갱신
- 백테스트(backtest): 전략 실행 → 성과 집계 → `backtest_results`
- API: 조회/명령의 얇은 계층(FastAPI)
- UI: 페이지별 서비스 모듈(React + React Query)

### 디렉터리 요약(백엔드)
```
backend/app/
├── api/                  # REST 엔드포인트
├── core/                 # 설정/DB/캐시
├── models/               # SQLAlchemy 모델
├── services/             # 도메인 서비스(수집/지표/ML/거래/백테스트)
├── trading/              # 엔진(주문/체결/리스크/사이징)
├── ml/                   # 피처/모델/서빙
└── utils/                # 공통 유틸
```

---

## 🗃️ 데이터/도메인 모델(핵심)
- Stock(id, symbol, name, exchange, sector)
- Bar(OHLCV, date, unique(stock_id,date))
- IndicatorSnapshot(stock_id, date, rsi_14, ema_x, macd...)
- Signal(stock_id, date, type, score, meta)
- Prediction(stock_id, prediction_date, target_date, y_hat, confidence, model_type)
- Account(account_id, balance, pnl, rules)
- Order(order_id, account_id, stock_id, side, qty, type, limit_price, status, ts)
- Fill(fill_id, order_id, price, qty, fee, slippage)
- Position(account_id, stock_id, qty, avg_price, unrealized_pnl)
- Trade(가상 체결 집계: side, qty, price, fee, pnl, ts)
- BacktestRun(id, strategy_name, window, params, metrics, created_at)

인덱스 원칙: `(stock_id,date)` 복합 인덱스, 빈번 조회 필드에 적절한 보조 인덱스

---

## 🔌 API 계약(MVP)
- GET `/health` → `{ status: "ok" }`
- GET `/stocks/{symbol}/bars?interval=1d&limit=500` → OHLCV
- GET `/stocks/{symbol}/indicators?date_from&date_to` → 지표 시계열
- GET `/signals/{symbol}?date_from&date_to` → 신호 시계열
- GET `/predictions/{symbol}?horizon=7` → 최근 예측 결과
- POST `/vt/accounts` → 가상계정 생성 `{ initial_balance }`
- GET `/vt/accounts/{id}` → 계정/잔고/PNL
- POST `/vt/orders` → `{ account_id, symbol, side:BUY|SELL, qty, type:MARKET|LIMIT, limit_price? }`
- GET `/vt/positions?account_id=...` → 보유 포지션
- GET `/vt/trades?account_id=...` → 체결 내역
- POST `/backtests/run` → `{ strategy, symbols, start_date, end_date, params }`
- GET `/backtests/{id}` → 결과/지표/에쿼티커브

응답은 표준화된 ISO-8601, 금액/수량은 소수 제한, 통화/소수점 스케일 명시

---

## 📈 지표/신호 설계
- 지표: SMA/EMA/RSI/MACD/BBANDS, 결측 보간 금지(빈칸 유지)
- 신호 생성: 규칙 기반(예: RSI<30 & EMA 상향) + 예측 기반(score 가중)
- 신호 스코어: [-1,1] 범위(매도~매수), 임계값 히스테리시스 적용(채터링 방지)

---

## 🤖 모델 서빙(MVP)
- 특징: 과거 N일 집계(수익률, 변동성, 지표), 미래 1~5일 수익률 예측
- 베이스라인: RandomForest/LogisticRegression
- 데이터 누수 방지: 시계열 분리(TimeSeriesSplit), 최근 구간 홀드아웃
- 저장: `predictions`에 y_hat, confidence, feature_meta
- 추론 주기: 일 1회(장 마감 후 배치)

---

## 💹 거래 엔진 설계(MVP)
- 체결 정책: Market on Close(그날 종가±슬리피지), Limit는 종가 기준 충족 시 체결
- 수수료: `max(고정, 비율*체결금액)` 단순 모델
- 슬리피지: `k * 종가 * 평균스프레드비`(k 기본 1.0)
- 포지션 사이징: 고정 위험(Risk %) 또는 ATR 기반 포지션 크기
- 리스크 가드레일:
  - 일 손실 한도 도달 시 당일 추가 진입 금지
  - 종목/섹터 편중 한도
  - 연속 손실 N회 시 전략 일시 중지
- 상태 머신: NEW → PARTIAL_FILLED → FILLED/CANCELLED

---

## 🔁 백테스트 엔진 설계(MVP)
- 시간 축: 일봉 바 시퀀스, 바-클로즈에서만 의사결정/체결
- 주문/체결: 거래 엔진 동일 로직 재사용
- 비용/슬리피지: 거래 엔진과 동일 파라미터
- 결과 산출: 에쿼티커브, 거래별 PnL, 지표(Sharpe/Sortino/MDD/PF/승률/손익비/Turnover)
- 시드/재현성: 랜덤 요소 고정

---

## 🪪 설정/환경
- `.env`: DB_URL, DATA_PROVIDER, FEE_RATE, SLIPPAGE_K, RISK_LIMIT_DAILY 등
- Feature Flags: `USE_PREDICTION`, `USE_RULE_SIGNALS`, `ALLOW_SHORT`, `INTRADAY_MODE`
- 프로필: `local`, `staging`, `prod`(파라미터/리소스 차등)

---

## 👀 관측/운영
- 로깅: 주문/체결/에러/리스크 위반 이벤트 구조화 로그(JSON)
- 메트릭: 요청 지연, 체결 비율, 승률, MDD, 일손익, 신호정확도, 데이터 신선도
- 트레이싱: 백테스트 실행/거래 사이클 단위 스팬(선택)
- 알림: 심각 에러/리스크 위반 시 Slack/Webhook

---

## 🔐 보안(초기)
- 로컬/개인 프로젝트 기준: 인증 생략 가능
- 원격 배포 시: JWT + CORS 최소 설정, Rate Limit, 입력 검증

---

## ⚙️ 성능 예산
- API P95 < 200ms(캐시된 조회)
- 백테스트 1전략·1종목·5년 일봉 < 5s 목표
- 일별 일괄 작업(수집/지표/예측) < 10m

---

## 🗺️ 단계적 로드맵(정제)
1) 주 1
- FastAPI 스캐폴딩, 일봉 수집(yfinance), 지표 계산, 기본 API(health/bars/indicators)
- 경량 백테스터 스켈레톤(바-클로즈)

2) 주 2
- 규칙 기반 신호 + RF 베이스라인 예측 저장
- 백테스트 성과지표 산출, 가상계정/주문/포지션 기본

3) 주 3
- 가상 거래 UI(계정/주문/포지션/내역), 대시보드 연결
- 리스크 규칙(일손실/편중/연속손실) 적용

4) 주 4
- 자동 실행 스케줄(장 마감 후), 전략 파라미터 관리, 리포트 자동 생성

5) 이후
- 분봉/실시간, LSTM/GRU, WebSocket, Celery, 전략 최적화

---

## 📜 샘플 페이로드
```json
// POST /vt/orders
{
  "account_id": 1,
  "symbol": "AAPL",
  "side": "BUY",
  "qty": 50,
  "type": "MARKET"
}
```
```json
// GET /backtests/{id}
{
  "id": 42,
  "strategy": "rsi_ema_combo",
  "period": { "start": "2021-01-01", "end": "2024-12-31" },
  "metrics": { "sharpe": 1.1, "mdd": 0.18, "win_rate": 0.54, "pf": 1.35 },
  "equity_curve": [{ "date": "2021-01-01", "equity": 10000000 }, ...]
}
```

---

## ✅ 품질 게이트
- 데이터 누수 유닛 테스트(시계열 분리 보장)
- 체결/수수료/슬리피지 일관성 테스트(백테스트=가상거래)
- 전략·파라미터 변경 시 회귀 테스트(주요 KPI 하락 경고)
