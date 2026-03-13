# 백테스팅 Look-Ahead Bias 제거 — 기능 명세서

> 상태: 구현 완료 (Phase 2) | 구현: `78b0e06`, `da188da`

## 목표

백테스팅 시뮬레이션에서 미래 데이터가 과거 매매 신호 계산에 사용되는 Look-Ahead Bias를 제거하여 백테스팅 결과의 신뢰성을 확보한다.

## 문제

### C-1: 스코어링 엔진이 시뮬레이션 날짜를 무시하고 전체 데이터 사용

`BacktestEngine.run()`은 날짜를 순회하며 매매를 시뮬레이션하지만,
각 날짜에서 호출하는 `ScoringEngine.score_stock()`은 DB에 저장된 **전체 가격/지표 데이터**를 조회한다.

```python
# backtest_engine.py:132
for date in all_dates:                          # date = 예: 2025-01-15
    score_data = scorer.score_stock(sid, ...)   # ← DB에서 전체 데이터 조회 (2026년까지 포함)
```

```python
# scoring_engine.py 내부 — score_stock() → get_stock_prices()
indicators = (
    db.query(TechnicalIndicator)
    .filter(TechnicalIndicator.stock_id == stock_id)
    # ← date 필터 없음 → 미래 데이터 포함
    .order_by(TechnicalIndicator.date.desc())
    .first()
)
```

결과: 2025-01-15 시점에서 2025-12-31의 지표로 매수 결정 → 수익률 과장.

## 요구사항

### FR-1: 날짜 인식 스코어 계산

- FR-1.1: `score_stock(stock_id, symbol, as_of_date)`에 기준 날짜 파라미터 추가
- FR-1.2: 기술적 지표 조회 시 `as_of_date` 이하 데이터만 사용
- FR-1.3: RF 예측 모델도 `as_of_date` 이하 가격 데이터만 입력으로 사용
- FR-1.4: `as_of_date=None`이면 기존 동작(전체 최신 데이터) 유지 — 실시간 스코어링 영향 없음

### FR-2: 백테스팅 루프에서 날짜 전달

- FR-2.1: `BacktestEngine` 루프의 매도/매수 판단 시 `scorer.score_stock(sid, symbol, as_of_date=date)` 호출
- FR-2.2: 지표 데이터가 없는 날짜(거래일이지만 지표 미계산)는 스코어링 스킵 처리

### FR-3: 예측 모델 날짜 제한 (범위 최소화)

- FR-3.1: `PredictionModel.predict_next_day(stock_id, as_of_date)`에 날짜 파라미터 추가
- FR-3.2: 가격 데이터 조회 시 `as_of_date` 이하만 사용
- FR-3.3: 실시간 호출(`as_of_date=None`)은 기존 동작 유지

## 수용 기준

- [ ] 2025-01-01~2025-06-30 백테스팅 실행 시 7월 이후 데이터 미사용 확인 (로그)
- [ ] 백테스팅 결과 수익률이 기존보다 낮아짐 (look-ahead bias 제거 효과)
- [ ] `GET /api/v1/trading/scores` (실시간 스코어링)는 기존 결과와 동일
- [ ] 백테스팅 완료 시간이 크게 증가하지 않음 (쿼리 최적화)
