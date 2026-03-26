# Phase E 통합 구현 계획서

> 작성일: 2026-03-26 | 상태: 초안
> 관련 spec: `spec/minute-bar-collection/`, `spec/backtest-engine/`, `spec/minute-indicators/`, `spec/frontend-test-expansion/`

---

## 개요

4개 기능을 의존성 순서에 따라 3단계(Wave)로 나눠 구현한다.

```
Wave 1 (기반)     Wave 2 (코어)         Wave 3 (확장)
─────────────     ──────────────        ──────────────
분봉 수집 MC-1~3   백테스트 BT-1~5       백테스트 UI BT-6
프론트 테스트 FT-1~4  DSL 확장 MI-1~3      대신증권 MC-4
지표 공유 모듈       분할 보정 MC-5        프론트 E2E FT-5~6
```

---

## 의존성 그래프

```
FT-1 (Vitest 설치) ──→ FT-2~4 (유닛 테스트) ──→ FT-5~6 (E2E)
                                                    ↑
MC-1 (키움 배치) ──→ MC-3 (API) ──→ BT-1 (Runner) ──→ BT-6 (UI)
MC-2 (실시간 sync) ─↗                  ↑
                            sv_core/indicators ──→ MI-2 (분봉 지표)
                                  ↑                    ↑
                            MI-1 (DSL 확장) ←── BT-2 (백테스트 지표)
```

---

## Wave 1: 기반 구축 (1주)

### Step 1-1: sv_core/indicators 공유 모듈 추출
- `local_server/engine/indicator_provider.py`의 계산 로직을 `sv_core/indicators/calculator.py`로 추출
- RSI, MA, EMA, MACD, 볼린저밴드, 평균거래량
- numpy 의존, 입력은 price 배열 → 출력은 지표 딕셔너리
- `indicator_provider.py`는 캐시/yfinance 래퍼만 남기고 계산은 sv_core 호출
- verify: 기존 engine 테스트 41개 통과

### Step 1-2: 키움 배치 수집 스크립트 (MC-1)
- `tools/kiwoom_minute_batch.py` — 키움 REST API로 과거 1년 1분봉 수집
- 최신→과거 순차 페이징, rate limit (초당 5회) 준수
- 결과: JSON/CSV 로컬 저장
- `tools/import_minute_bars.py` — cloud DB MinuteBar 테이블에 bulk insert
- verify: 1종목 1년치 수집 + DB row count 확인

### Step 1-3: 로컬→클라우드 분봉 sync (MC-2)
- `cloud_server/api/market_data.py`에 `POST /api/v1/bars/ingest` 추가
- `local_server/cloud/bar_sync.py` — 완성된 분봉을 주기적으로 cloud 전송
- offline queue: 실패 시 재전송
- verify: 로컬 수집 → cloud DB 반영 확인

### Step 1-4: cloud API 분봉 조회 (MC-3)
- `GET /api/v1/stocks/{symbol}/bars` resolution에 `1m`, `5m`, `15m`, `1h` 추가
- 서버사이드 집계 (1m → 5m/15m/1h)
- 페이징, 날짜 범위 필터
- verify: API 호출 → 정확한 OHLCV 반환

### Step 1-5: Vitest 설치 + dslParser 유닛 테스트 (FT-1, FT-2)
- `vitest`, `happy-dom` 설치
- `vite.config.ts` test 설정
- `dslParser.test.ts` 25~35개 테스트
- verify: `npm run test` 전체 통과

### Step 1-6: dslConverter + e2eCrypto 유닛 테스트 (FT-3, FT-4)
- `dslConverter.test.ts` 8~12개
- `e2eCrypto.test.ts` 15~20개 (IndexedDB mock)
- verify: `npm run test` 전체 통과

---

## Wave 2: 코어 엔진 (1.5주)

### Step 2-1: DSL 문법 확장 (MI-1)
- 함수 인자에 타임프레임 문자열 허용: `RSI(14, "5m")`
- `sv_core/parsing/builtins.py` — 함수 시그니처 1~2개 인자
- `sv_core/parsing/parser.py` — 인자 개수 유연화
- `sv_core/parsing/evaluator.py` — 타임프레임 전달
- 하위 호환: `RSI(14)` = `RSI(14, default_tf)`
- verify: 기존 DSL 테스트 69개 통과 + 신규 타임프레임 테스트

### Step 2-2: 백테스트 Runner (BT-1)
- `cloud_server/services/backtest_runner.py`
- 바 데이터 로드 (MinuteBar / DailyBar)
- 타임프레임 집계 (1m → 5m/15m/1h)
- DSL AST에서 사용된 타임프레임 추출 → 필요한 데이터만 로드
- 각 바마다: 지표 계산 → DSL 평가 → 주문 실행
- `sv_core/indicators/calculator.py` 사용 (Step 1-1)
- verify: 알려진 규칙 + 알려진 데이터로 예상 거래 수/P&L 일치

### Step 2-3: 수수료/세금/슬리피지 (BT-3)
- `cloud_server/services/backtest_cost.py`
- 매수 수수료 0.015%, 매도 수수료 0.015%, 매도 세금 0.18%, 슬리피지 0.1%
- 설정 가능 (API 파라미터)
- verify: 비용 포함 P&L < 비용 미포함 P&L

### Step 2-4: 결과 리포트 (BT-4)
- equity_curve, trades, summary_metrics
- 총수익률, CAGR, MDD, 승률, 손익비, 샤프비율
- verify: 수동 계산과 일치

### Step 2-5: API 엔드포인트 (BT-5)
- `POST /api/v1/backtest/run`
- inline script 지원 (저장 전 테스트)
- rate limit 분당 5회, 타임아웃 60초
- verify: API 호출 → 결과 JSON 반환

### Step 2-6: 분봉 IndicatorProvider 확장 (MI-2, MI-3)
- 멀티 타임프레임 캐시: `indicators["5m"]["rsi_14"]`
- 로컬 MinuteBarStore에서 데이터 읽기
- Evaluator context에 타임프레임 주입
- verify: 분봉 지표로 라이브 엔진 규칙 평가 동작

### Step 2-7: 주식 분할 보정 (MC-5)
- 배치 수집 데이터에만 적용 (yfinance는 이미 adjusted)
- 분할 이력 테이블 or StockMaster 필드
- verify: 삼성전자 2018년 분할 전후 가격 연속성

---

## Wave 3: UI + 확장 (1주)

### Step 3-1: 백테스트 프론트엔드 (BT-6)
- `Backtest.tsx` — 종목/기간/타임프레임 선택 폼
- `BacktestResult.tsx` — 수익 곡선, 지표 카드, 거래 목록
- StrategyBuilder에서 "백테스트" 버튼
- verify: 브라우저에서 백테스트 실행 + 결과 표시

### Step 3-2: 프론트엔드 E2E 확장 (FT-5, FT-6)
- `strategy-crud.spec.ts` — 전략 CRUD 흐름
- `dashboard.spec.ts` — 대시보드 데이터 로딩
- StrategyBuilder data-testid 추가
- verify: `npx playwright test` 전체 통과

### Step 3-3: 대신증권 Creon Plus (MC-4) — 계좌 확보 후
- `tools/creon_collector.py` — Windows COM 배치
- `tools/import_csv_bars.py` — CSV → DB
- 5년 5분봉 + 2년 1분봉
- verify: 키움 중복 구간과 정합성 확인

---

## 검증 체크리스트

### Wave 1
- [ ] sv_core/indicators 추출 → 기존 엔진 테스트 통과
- [ ] 키움 배치 1종목 수집 성공
- [ ] 로컬→클라우드 분봉 sync 동작
- [ ] cloud API 분봉 조회 (1m/5m/15m/1h)
- [ ] Vitest + dslParser 테스트 통과
- [ ] dslConverter + e2eCrypto 테스트 통과

### Wave 2
- [ ] DSL 타임프레임 확장 + 하위 호환
- [ ] 백테스트 일봉 MVP 동작 (알려진 규칙으로 검증)
- [ ] 백테스트 분봉 동작 (키움 데이터로)
- [ ] 수수료/세금 반영
- [ ] API 엔드포인트 동작
- [ ] 분봉 IndicatorProvider 라이브 엔진 통합

### Wave 3
- [ ] 백테스트 UI 브라우저 동작
- [ ] StrategyBuilder → 백테스트 연동
- [ ] E2E 테스트 확장 통과
- [ ] 대신증권 5년 데이터 임포트 (계좌 확보 후)

---

## 리스크

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 키움 REST API 분봉 조회가 모의서버에서 안 될 수 있음 | 배치 수집 불가 | 실계좌 필요 여부 먼저 확인 |
| 분봉 5년 데이터 DB 성능 | 쿼리 느림 | 파티셔닝, 타임스탬프 인덱스, 필요 시 TimescaleDB |
| DSL 문법 변경이 기존 저장된 규칙에 영향 | 규칙 깨짐 | 하위 호환 보장 (인자 미지정 = 기존 동작) |
| 대신증권 COM API Windows 의존 | CI/CD 불가 | 1회성 배치 → 이후 실시간 수집으로 전환 |
