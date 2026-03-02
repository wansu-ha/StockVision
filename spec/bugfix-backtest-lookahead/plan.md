# 백테스팅 Look-Ahead Bias 제거 — 구현 계획서

## 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/services/scoring_engine.py` | `score_stock()` / `score_all_stocks()`에 `as_of_date` 파라미터 추가, 지표 쿼리 날짜 필터 |
| `backend/app/services/prediction_model.py` | `predict_next_day()`에 `as_of_date` 파라미터 추가, 가격 쿼리 날짜 필터 |
| `backend/app/services/backtest_engine.py` | 루프 내 `score_stock()` 호출 시 `as_of_date=date` 전달 |

## 단계별 구현

### Step 1: ScoringEngine — 지표 쿼리에 날짜 필터 추가

**변경 위치**: `scoring_engine.py` `score_stock()` 메서드

현재 코드 (문제):
```python
def score_stock(self, stock_id: int, symbol: str) -> Optional[dict]:
    indicators = (
        self.db.query(TechnicalIndicator)
        .filter(TechnicalIndicator.stock_id == stock_id)
        .order_by(TechnicalIndicator.date.desc())
        .first()
    )
```

수정 후:
```python
def score_stock(
    self,
    stock_id: int,
    symbol: str,
    as_of_date: Optional[datetime] = None,
) -> Optional[dict]:
    q = (
        self.db.query(TechnicalIndicator)
        .filter(TechnicalIndicator.stock_id == stock_id)
    )
    if as_of_date is not None:
        q = q.filter(TechnicalIndicator.date <= as_of_date)
    indicators = q.order_by(TechnicalIndicator.date.desc()).first()
```

`score_all_stocks()`도 동일하게 `as_of_date` 파라미터 받아 `score_stock()`에 전달.

### Step 2: PredictionModel — 가격 쿼리에 날짜 필터 추가

**변경 위치**: `prediction_model.py` `predict_next_day()` 메서드

현재 코드 (문제):
```python
def predict_next_day(self, stock_id: int) -> Optional[dict]:
    prices = (
        db.query(StockPrice)
        .filter(StockPrice.stock_id == stock_id)
        .order_by(StockPrice.date.desc())
        .limit(60)
        .all()
    )
```

수정 후:
```python
def predict_next_day(
    self,
    stock_id: int,
    as_of_date: Optional[datetime] = None,
) -> Optional[dict]:
    q = db.query(StockPrice).filter(StockPrice.stock_id == stock_id)
    if as_of_date is not None:
        q = q.filter(StockPrice.date <= as_of_date)
    prices = q.order_by(StockPrice.date.desc()).limit(60).all()
```

ScoringEngine에서 `predict_next_day(stock_id, as_of_date=as_of_date)` 호출 시 전달.

### Step 3: BacktestEngine — 루프에서 날짜 전달

**변경 위치**: `backtest_engine.py:129-168`

```python
# 수정 전
score_data = scorer.score_stock(sid, stock_symbols[sid])

# 수정 후
score_data = scorer.score_stock(sid, stock_symbols[sid], as_of_date=date)
```

매도/매수 판단 양쪽 모두 적용 (line 132, line 166).

### Step 4: ScoringEngine 내부에서 PredictionModel 호출 시 날짜 전달

**변경 위치**: `scoring_engine.py` `score_stock()` 내 prediction 호출

```python
# 수정 전
prediction = self.prediction_model.predict_next_day(stock_id)

# 수정 후
prediction = self.prediction_model.predict_next_day(stock_id, as_of_date=as_of_date)
```

## 검증

- `as_of_date=None` 호출 → 기존 실시간 스코어링 동작 동일
- `as_of_date=datetime(2025, 6, 30)` 호출 → 7월 이후 지표/가격 미포함 확인
- 백테스팅 2025-01-01~2025-06-30 실행 후 수익률이 전체 데이터 사용 시보다 낮거나 다름 확인
