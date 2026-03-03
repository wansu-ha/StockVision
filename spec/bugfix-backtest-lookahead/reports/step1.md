# Step 1 완료 보고서 — C-1 Look-Ahead Bias 제거

## 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/services/technical_indicators.py` | `get_stock_prices(as_of_date=None)` 추가, `as_of_date` 있으면 `StockPrice.date <= as_of_date` 필터. `calculate_all_indicators(as_of_date=None)` 추가, `get_stock_prices`에 전달. |
| `backend/app/services/scoring_engine.py` | `score_stock(as_of_date=None)` 추가, `calculate_all_indicators`, `get_stock_prices`, `predict_next_day` 호출 시 전달. |
| `backend/app/services/prediction_model.py` | `prepare_features(as_of_date=None)` 추가, StockPrice/TechnicalIndicator 쿼리 모두 `as_of_date` 이하 필터. `predict_next_day(as_of_date=None)` 추가, `prepare_features` 및 현재 가격 조회에 전달. |
| `backend/app/services/backtest_engine.py` | 루프 내 매도(line 132), 매수(line 166) 양쪽 `score_stock` 호출에 `as_of_date=date` 전달. |

## 검증

- `as_of_date=None` → 기존 동작 유지 (실시간 스코어링 영향 없음)
- `as_of_date=date` → 해당 날짜 이하 데이터만 사용 (look-ahead bias 제거)
