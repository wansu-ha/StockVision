# StockVision Phase 2 가상 자동매매 — 코드 분석 결과

**분석 일시**: 2026-03-02
**분석 브랜치**: `feat/virtual-auto-trading` (Step 15 완료 상태)
**분석 범위**: frontend Trading.tsx, StockList.tsx, services/api.ts, types/, backend api/, services/, models/, spec/

---

## 요약

| 심각도 | 건수 |
|--------|------|
| Critical | 4 |
| Warning | 10 |
| Info | 5 |

---

## Critical

### C-1. 백테스팅 엔진의 Look-Ahead Bias

**파일**: `backend/app/services/backtest_engine.py:132`

`ScoringEngine.score_stock()`은 DB에 저장된 전체 가격 데이터(현재까지)를 대상으로 지표를 계산합니다.
백테스팅 루프에서 2025-01-01 시점을 시뮬레이션하더라도 2026년 데이터까지 포함된 지표로 매매 신호를 생성합니다.
미래 정보를 과거 의사결정에 사용하는 치명적 bias입니다.

**영향**: 백테스팅 결과(수익률, 승률, 샤프비율)가 실제보다 낙관적으로 왜곡됩니다.

---

### C-2. POST /trading/accounts 응답에서 필드 누락

**파일**: `backend/app/api/trading.py:76-86`

계좌 생성 응답에 `total_profit_loss`, `total_trades`, `win_trades`가 없습니다.
프론트엔드 `VirtualAccount` 타입(`types/trading.ts:3-12`)에서 이 필드들은 `number`로 선언되어 `undefined`가 됩니다.

---

### C-3. 스코어링 실행 결과에 `id` 필드 없음

**파일**: `backend/app/services/scoring_engine.py:194-204`

`score_all_stocks()`는 `id` 필드 없는 dict를 반환합니다.
프론트엔드 ScoresTab에서 `scores.map((s) => <tr key={s.id} ...>)`로 렌더링 시 key가 모두 `undefined`가 됩니다.

---

### C-4. `StockList.tsx`에서 null 필드 접근 시 런타임 에러

**파일**: `frontend/src/pages/StockList.tsx:46-47`

```tsx
stock.sector.toLowerCase().includes(searchTerm.toLowerCase())
stock.industry.toLowerCase().includes(searchTerm.toLowerCase())
```

DB 모델에서 `sector`, `industry`는 nullable. `null.toLowerCase()`는 런타임 TypeError입니다.

---

## Warning

### W-1. 매수 후 unrealized_pnl 순간 오표시

**파일**: `backend/app/services/trading_engine.py:125-131`

기존 포지션에 추가 매수 시 평균가 재계산 직후 즉시 `unrealized_pnl = (price - avg_price) * quantity`를 계산하여 비정상 값이 발생할 수 있습니다.

---

### W-2. `account_id` 없는 자동매매 규칙 생성 시 무경고

**파일**: `frontend/src/pages/Trading.tsx:821-823`

`account_id` 없으면 스케줄러가 해당 규칙을 스킵(`auto_trade_scheduler.py:106`)하지만, 사용자에게 이 사실이 안내되지 않습니다.

---

### W-3. `selectedAccountId` setter 없음 — 다중 계좌 불가

**파일**: `frontend/src/pages/Trading.tsx:35`

```tsx
const [selectedAccountId] = useState<number | null>(null)
```

setter가 구조분해에서 제외되어 있어 여러 계좌가 있어도 항상 첫 번째(`accounts[0]`)만 사용됩니다.

---

### W-4. onError 콜백이 백엔드 상세 오류를 무시

**파일**: `frontend/src/pages/Trading.tsx:104, 115, 129, 157, 167`

```tsx
onError: () => showToast('주문 실행에 실패했습니다.', 'error'),
```

백엔드가 반환하는 구체적 오류(예: "잔고 부족 (필요: 500,000원, 잔고: 100,000원)")가 표시되지 않습니다.

---

### W-5. `TechnicalIndicatorCalculator`의 독립 Session 관리

**파일**: `backend/app/services/technical_indicators.py:13`

API 요청마다 새 `SessionLocal()`이 열립니다. 백테스팅 루프에서 `ScoringEngine`이 반복 생성되면 Session이 누적될 수 있습니다.

---

### W-6. `BacktestEngine`에서 예외 발생 시 `scorer.close()` 미호출

**파일**: `backend/app/services/backtest_engine.py:114-207`

try-finally가 없어 루프 중 예외 시 Scorer의 내부 Session이 닫히지 않아 DB Session 누수가 발생합니다.

---

### W-7. 백테스팅 수익률 차트의 부정확한 잔고 계산

**파일**: `frontend/src/pages/Trading.tsx:669-682`

차트 equity curve가 SELL 거래의 `realized_pnl`만 누적합니다. 매수 시 현금 감소가 반영되지 않은 차트입니다.

---

### W-8. `/stocks/{symbol}/prices` 응답 포맷 불확실

**파일**: `backend/app/api/stocks.py:117-126`

프론트엔드(`api.ts:44`)는 `{ symbol, name, prices }` 형태를 기대하는데 실제 반환 포맷이 불일치할 수 있습니다.

---

### W-9. 스케줄러 규칙 변경 시 `reload_rules()` 미호출

**파일**: `backend/app/api/trading.py:351-364`

규칙 PATCH(토글 포함) 시 `AutoTradeScheduler.reload_rules()`가 호출되지 않아, 규칙을 활성화해도 서버 재시작 전까지 반영되지 않습니다.

---

### W-10. `PredictionModel` 없으면 기본값 0.0 → 50점 왜곡

**파일**: `backend/app/services/scoring_engine.py:173`

모델 파일 없음/데이터 부족 시 `pred_change_pct = 0.0` → `_prediction_score(0.0) = 50.0`으로 처리됩니다.
예측 가중치가 0.30이므로 스코어 왜곡 영향이 큽니다.

---

## Info

### I-1. `main.py`의 `on_event` deprecated

`@app.on_event("startup")`은 FastAPI에서 deprecated. `lifespan` 컨텍스트 매니저로 교체 권장.

### I-2. `SELL(CLOSE)` 타입 UI 미처리

백테스팅 말 청산 시 `type: "SELL(CLOSE)"`가 기록되지만 프론트엔드에서 구분 표시 없음.

### I-3. `StockScore.date` 필드 UI 미활용

스코어링 테이블에 산출 시각이 표시되지 않습니다.

### I-4. 에러 토스트에서 네트워크 에러와 비즈니스 로직 에러 구분 없음

### I-5. `api.ts` 파일 중간에 `import` 구문 위치 — ESLint `import/first` 경고 가능성
