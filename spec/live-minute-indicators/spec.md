> 작성일: 2026-03-28 | 상태: 구현 완료 | Unit live-minute-indicators

# 라이브 엔진 분봉 IndicatorProvider

## 배경

전략 DSL에서 `RSI(14, "5m")` 같은 분봉 기반 지표를 평가하려면
IndicatorProvider가 일봉뿐 아니라 분봉도 지원해야 한다.
현재는 tf 인자를 파싱만 하고 무시한다.

## 목표

라이브 엔진 루프에서 분봉(1m/5m 등) 지표를 평가 가능하게 한다.

## 범위

- `local_server/engine/indicator_provider.py` — tf 분기 + 분봉 캐시
- `local_server/engine/evaluator.py` — make_indicator_func tf 실제 사용
- `local_server/engine/engine.py` — TF별 지표 주입 구조 변경
- 단위 테스트 추가

## 수용 기준

- [x] `IndicatorProvider.get(symbol, tf="1d")` — 기존 일봉 동작 유지
- [x] `IndicatorProvider.get(symbol, tf="5m")` — 분봉 지표 반환 (캐시 1분)
- [x] 분봉 캐시 만료(1분) 시 None 반환 (만료 = 데이터 없음)
- [x] evaluator `make_indicator_func` — tf=None→일봉, tf="5m"→분봉 dict
- [x] engine `_collect_candidates` — indicators가 `{tf: dict}` 구조
- [x] 단위 테스트 통과

## 제약

- 고정 period만 지원 (rsi_14, ma_5 등). 임의 period(rsi_7)는 None.
- 분봉 데이터는 cloud_server MinuteBar API에서 조회 (`GET /api/v1/stocks/{symbol}/bars?resolution={tf}&limit=200`).
- CloudClient 없으면(None) 분봉 지표 빈 dict 반환.
