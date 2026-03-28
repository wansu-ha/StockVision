> 작성일: 2026-03-28 | 상태: 구현 완료 | Unit live-minute-indicators

# 구현 계획: 라이브 엔진 분봉 IndicatorProvider

## Step 1: IndicatorProvider 분봉 지원

파일: `local_server/engine/indicator_provider.py`

### 변경 사항
- `get(symbol, tf="1d")` 시그니처 확장
- tf="1d": 기존 일봉 캐시 그대로 반환
- tf="1m"/"5m" 등: 분봉 캐시 조회 → 만료/없으면 None 반환
- `refresh_minute(symbol, tf)`: CloudClient로 분봉 조회 → calc_all_indicators → 캐시
- 분봉 캐시 구조: `{symbol: {tf: {"expires": datetime, "indicators": dict}}}`
- 유효기간 1분 (장중 분봉은 매분 바뀜)

verify: IndicatorProvider 단위 테스트 통과

## Step 2: evaluator tf 분기

파일: `local_server/engine/evaluator.py`

### 변경 사항
- `_build_dsl_context`에서 `indicators`가 `{tf: dict}` 구조임을 가정
- `make_indicator_func(name)` → tf=None이면 "1d" 키, tf="5m"이면 "5m" 키
- tf 해당 dict 없으면 None 반환 (안전 처리)

verify: evaluator DSL tf 분기 테스트 통과

## Step 3: 엔진 루프 통합

파일: `local_server/engine/engine.py`

### 변경 사항
- `_collect_candidates`: `latest["indicators"]` → `{tf: dict}` 구조로 변경
  ```python
  # 변경 전
  latest["indicators"] = self._indicator_provider.get(symbol)

  # 변경 후
  indicators_by_tf: dict[str, dict] = {}
  indicators_by_tf["1d"] = self._indicator_provider.get(symbol, "1d")
  for tf in _extract_tfs(rule):
      ind = self._indicator_provider.get(symbol, tf)
      if ind is not None:
          indicators_by_tf[tf] = ind
  latest["indicators"] = indicators_by_tf
  ```
- `_extract_tfs(rule)`: rule의 script에서 tf 인자 목록 추출 (단순 파싱)

verify: engine 기존 테스트 통과 (회귀 없음)

## Step 4: 테스트

파일: `local_server/tests/test_live_minute_indicators.py`

### 테스트 목록
1. `test_indicator_provider_daily_unchanged` — tf="1d" 기존 동작 유지
2. `test_indicator_provider_minute_hit` — 분봉 캐시 히트 시 dict 반환
3. `test_indicator_provider_minute_expired` — 캐시 만료 시 None 반환
4. `test_evaluator_tf_daily` — tf=None → "1d" 지표 사용
5. `test_evaluator_tf_minute` — tf="5m" → "5m" 지표 사용

verify: `python -m pytest local_server/tests/test_live_minute_indicators.py -q` 전체 통과
