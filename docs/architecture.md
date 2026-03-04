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

---

## 🚀 Phase 3: 로컬 브릿지 + 시스템매매 (키움 실전 연동)

### 목표
사용자가 설치파일 하나로 로컬 실행 환경을 구축하고,
클라우드 웹 UI에서 전략을 설정하면 로컬 PC에서 키움 API로 자동 체결되는 시스템.

**법적 포지션**: 시스템매매 (투자일임·투자자문 아님)
- 사용자가 직접 규칙 정의 → 시스템이 실행
- AI/시스템이 독자 판단으로 종목 선정 금지

---

### 아키텍처 다이어그램

```
Cloud (stockvision.app)                 Local PC (Windows)
┌──────────────────────────┐           ┌─────────────────────────────────┐
│  React 앱 (정적 호스팅)  │ ◀─ WS ──▶│  FastAPI 로컬 서버              │
│  컨텍스트 API            │ ◀─ HTTP──▶│  localhost:8765                 │
│  전략 템플릿 API         │           │  ├── 키움 COM API 실행 레이어   │
│  버전 체크 API           │           │  ├── config.json (자동저장)     │
│  하트비트 수신           │ ◀─ ping ──│  ├── logs.db (체결·오류 기록)   │
└──────────────────────────┘           │  └── 전략 규칙 평가 엔진        │
                                       └─────────────────────────────────┘
```

**흐름 설명**
1. 사용자: 브라우저로 `stockvision.app` 접속 → React 앱 로딩
2. React 앱: `ws://localhost:8765/ws` 연결 시도 (브라우저 localhost 예외 허용)
3. 설정 변경: React 앱 → HTTP POST → 로컬 서버 → `config.json` 자동 저장 (debounce 500ms)
4. 전략 실행: 로컬 서버가 키움 COM API 호출 → 체결 결과 → WS로 React 앱에 push
5. 하트비트: 로컬 서버 → cloud `/api/heartbeat` (5분마다 익명 UUID + 버전)

---

### 설치 모델

| 항목 | 내용 |
|------|------|
| 배포 형태 | 단일 `.exe` (PyInstaller 번들) |
| 포함 요소 | FastAPI 서버 + 의존성 + 기본 config.json 템플릿 |
| 제외 요소 | React 앱 (cloud 호스팅, exe에 포함 안 함) |
| 설치 후 | 실행하면 백그라운드에서 localhost:8765 서버 시작 |
| 업데이트 | 로컬 서버가 cloud `/api/version` 폴링 → 신버전 알림 |

---

### 데이터 저장 모델

```
로컬 PC (%APPDATA%\StockVision\)
├── token.dat           # Refresh Token (OS 파일 권한 보호)
├── local_secrets.json  # 계좌번호만 (평문, 절대 클라우드 업로드 금지)
├── logs.db (SQLite)    # 체결 로그, 오류 로그, 전략 실행 이력
└── kiwoom_cache/       # 당일 시세 캐시 (선택)

Cloud DB
├── users               # 이메일, password_hash (Argon2id), email_verified
├── refresh_tokens      # SHA-256(token), 30일 TTL, Rotation
├── config_blobs        # 서버사이드 AES-256-GCM 암호화 blob
└── heartbeat           # UUID, 버전, OS, 타임스탬프만 (개인정보 없음)
```

**자동 저장 규칙**
- 설정 변경 → 500ms debounce → `PUT /api/v1/config` (평문 JSON 전송)
- 서버가 AES-256-GCM 암호화 후 `config_blobs`에 저장
- 저장 버튼 없음, 사용자가 저장을 신경 쓸 필요 없음
- 앱 재시작 시 `GET /api/v1/config` → 서버 복호화 → 설정 로드

---

### 클라우드 역할 (최소)

| API | 용도 |
|-----|------|
| `POST /api/auth/register` | 회원가입 (이메일 인증 메일 발송) |
| `POST /api/auth/login` | 이메일+비밀번호 로그인 → JWT (24h) + Refresh Token (30d) |
| `POST /api/auth/refresh` | Refresh Token → 새 JWT + 새 Refresh Token (Rotation) |
| `POST /api/auth/logout` | Refresh Token 무효화 |
| `GET /api/version` | 최신 버전 번호 반환 |
| `GET /api/context` | 서버에서 계산한 시장 컨텍스트 변수 (RSI, 변동성 등) |
| `GET /api/templates` | 전략 템플릿 목록 |
| `POST /api/heartbeat` | 익명 UUID + 버전 수신 (서비스 현황 파악용) |
| `PUT /api/v1/config` | 설정 업로드 (서버가 AES-256-GCM 암호화 후 저장) |
| `GET /api/v1/config` | 설정 다운로드 (서버가 복호화 후 평문 JSON 반환) |

클라우드는 **API 키, 체결 내역, 계좌번호, 프로파일 평문 저장 금지** (G5 제5조② 준수)

---

### 인증 모델

**클라우드 Auth** (이메일 + 비밀번호) + **서버사이드 AES-256-GCM 설정 암호화**

| 구분 | 인증 여부 | 역할 |
|------|:--------:|------|
| 클라우드 (stockvision.app) | ✅ 필요 | 이메일+비밀번호(Argon2id) → JWT 발급, 프로파일 식별 |
| 로컬 서버 (localhost:8765) | ❌ 불필요 | localhost-only 수신, 외부 접근 불가 |

**설정 암호화 (서버사이드):**
- 서버가 `CONFIG_ENCRYPTION_KEY` (AES-256-GCM)로 설정 blob 암호화/복호화
- 클라이언트는 평문 JSON 송수신 — 암호화 로직 없음
- DB 직접 접근 시에도 CONFIG_ENCRYPTION_KEY 없으면 복호화 불가
- 비밀번호 재설정 시 설정 데이터에 영향 없음 (서버 키로 암호화)
- 법적 근거: [개인정보보호법 제29조](https://www.law.go.kr/법령/개인정보보호법), 안전성확보조치기준 §10

**키움 인증:** 영웅문 HTS에 위임 (ID/PW/공동인증서는 우리 앱 미보관)

---

### Phase 3 스펙 목록

| 스펙 | 파일 | 상태 |
|------|------|------|
| 로컬 브릿지 서버 | `spec/local-bridge/spec.md` | 초안 완료 |
| 키움 API 연동 | `spec/kiwoom-integration/spec.md` | 초안 완료 |
| 전략 빌더 UI | `spec/strategy-builder/spec.md` | 초안 완료 |
| 컨텍스트 클라우드 | `spec/context-cloud/spec.md` | 초안 완료 |
| 실행 엔진 | `spec/execution-engine/spec.md` | 초안 완료 |
| 사용자 대시보드 | `spec/user-dashboard/spec.md` | 초안 완료 |
| 포트폴리오 | `spec/portfolio/spec.md` | 초안 완료 |
| 체결 로그 | `spec/execution-log/spec.md` | 초안 완료 |
| 알림 | `spec/notification/spec.md` | 초안 완료 |
| 온보딩 | `spec/onboarding/spec.md` | 초안 완료 |
| 전략 템플릿 | `spec/strategy-template/spec.md` | 초안 완료 |
| 관리자 대시보드 | `spec/admin-dashboard/spec.md` | 초안 완료 |

---

### Phase 3 스펙 목록 (auth 추가)

| 스펙 | 파일 | 상태 |
|------|------|------|
| **인증** | `spec/auth/spec.md` | ✅ 업데이트 완료 |

### 보류/미래 계획

| 항목 | 이유 |
|------|------|
| 코스콤 연동 | 로컬 모델 전환으로 우선순위 하락, Phase 4+ |
| 클라우드 VM 전략 실행 | 미래 계획 (멀티 사용자 확장 시) |
| 수익화 모델 | 미래 계획 |

---

### 📋 미완료 리서치 항목

- [ ] **개인정보 제외 수집 가능 영역 조사** — 개인정보보호법 기준, 익명 UUID 하트비트·집계 통계·오류 로그 수집의 법적 허용 범위 확인
  - 파일: `docs/research/data-privacy-research.md` (미작성)
  - 우선순위: Phase 3 배포 전 필수
