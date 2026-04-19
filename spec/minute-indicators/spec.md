# 분봉 지표 + DSL 확장 — Minute Indicators

> 작성일: 2026-03-26 | 상태: 구현 완료

---

## 목표

현재 일봉 전용인 기술 지표와 DSL을 분봉 타임프레임으로 확장.
전략 엔진이 분 단위로 지표를 평가하고 매매 신호를 생성할 수 있게 한다.

---

## 범위

### 포함

1. **분봉 지표 계산** — 1분/5분/15분/1시간봉 RSI, MA, EMA, MACD, 볼린저밴드
2. **DSL 문법 확장** — 타임프레임 지정자 추가
3. **IndicatorProvider 확장** — 분봉 캐시 + 실시간 갱신
4. **Evaluator 연동** — 분봉 지표를 DSL context에 주입

### 미포함

- 커스텀 지표 사용자 정의 (v2)

### 참고: 멀티 타임프레임 동시 참조

`RSI(14, "5m") <= 30 AND MA(20, "1d") > MA(60, "1d")` 같은 혼합 사용은
MI-1 문법으로 이미 지원됨. 단, 라이브 엔진에서 여러 타임프레임 지표를
동시에 캐시/갱신하는 것은 MI-2의 범위에 포함.

### 지표 계산 공유 모듈

`sv_core/indicators/calculator.py`로 지표 계산 코어를 추출하여
local engine (MI-2)과 backtest engine (BT-2)이 동일 로직을 공유한다.
기존 `local_server/engine/indicator_provider.py`의 계산 로직을 이동.

---

## MI-1: DSL 문법 확장

**현재**:
```dsl
매수: RSI(14) <= 30 AND MA(5) > MA(20)
```
RSI(14) = 일봉 14일 고정. 타임프레임 지정 불가.

**확장안**:
```dsl
-- 기본값은 엔진 설정 타임프레임 (하위 호환)
매수: RSI(14) <= 30

-- 타임프레임 명시
매수: RSI(14, "5m") <= 30 AND MA(20, "1h") > MA(60, "1h")
```

**수용 기준**:
- [ ] 기존 `RSI(14)` 문법 하위 호환 (타임프레임 미지정 = 엔진 기본값)
- [ ] 두 번째 인자로 타임프레임 문자열 허용: `"1m"`, `"5m"`, `"15m"`, `"1h"`, `"1d"`
- [ ] 파서: 함수 인자 개수 유연화 (1개 또는 2개)
- [ ] 평가기: 타임프레임별 지표 딕셔너리에서 조회
- [ ] 빌트인 패턴 함수도 타임프레임 지원: `골든크로스("5m")`

**파일**:
- `sv_core/parsing/builtins.py` (수정) — 함수 시그니처 확장
- `sv_core/parsing/parser.py` (수정) — 인자 개수 유연화
- `sv_core/parsing/evaluator.py` (수정) — 타임프레임 전달

---

## MI-2: 분봉 IndicatorProvider

**설명**: 분봉 데이터로 기술 지표를 실시간 계산. 엔진 스케줄러 주기(1분)마다 갱신.

**수용 기준**:
- [ ] 타임프레임별 독립 캐시: `indicators["5m"]["rsi_14"]`, `indicators["1h"]["ma_20"]`
- [ ] 분봉 데이터 소스: 로컬 MinuteBarStore
- [ ] 롤링 윈도우: 지표 계산에 필요한 최소 바 수만 유지
  - RSI(14) → 최소 15바
  - MA(60) → 최소 61바
  - MACD(12,26,9) → 최소 35바
- [ ] 새 바 완성 시 incremental 갱신 (전체 재계산 아님)
- [ ] 캐시 TTL: 타임프레임 해상도 (1분봉 → 1분, 5분봉 → 5분)

**파일**:
- `local_server/engine/indicator_provider.py` (수정) — 멀티 타임프레임 지원

---

## MI-3: Evaluator 연동

**설명**: RuleEvaluator가 분봉 지표를 DSL context에 주입.

**수용 기준**:
- [ ] `_build_dsl_context()`에 타임프레임 인자 추가
- [ ] `ctx["RSI"] = lambda period, tf="default": indicators[tf][f"rsi_{period}"]`
- [ ] 기본 타임프레임은 엔진 설정에서 결정 (config `strategy.default_timeframe`)
- [ ] 백테스트에서도 동일 context 빌드 로직 사용 (코드 공유)

**파일**:
- `local_server/engine/evaluator.py` (수정)
- `cloud_server/services/backtest_runner.py` — 같은 context 빌드 재사용

---

## 하위 호환성

| 기존 문법 | 확장 후 동작 | 호환성 |
|----------|------------|--------|
| `RSI(14)` | `RSI(14, default_tf)` | ✅ 동일 |
| `MA(20)` | `MA(20, default_tf)` | ✅ 동일 |
| `골든크로스()` | `골든크로스(default_tf)` | ✅ 동일 |
| `MACD()` | `MACD(default_tf)` | ✅ 동일 |

`default_tf`는:
- 라이브 엔진: `"1d"` (현재 동작 그대로)
- 백테스트: 사용자가 선택한 타임프레임
