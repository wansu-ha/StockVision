# 프리셋 보강 + DSL 함수 확장 — 구현 계획서

> 작성일: 2026-03-29 | 상태: 구현 완료 | spec: spec/preset-expansion/spec.md

## 아키텍처

```
sv_core/parsing/
├─ builtins.py      ← 함수 등록 (MACD_HIST, STOCH, 다이버전스, 등락률)
├─ evaluator.py     ← 다이버전스 전용 구현 (상향돌파/하향돌파 패턴 따름)
└─ tests/           ← 파서/평가기 테스트

local_server/engine/
├─ indicator_history.py   ← 링버퍼 (다이버전스 로컬 저점/고점 탐색)
└─ indicator_provider.py  ← 지표 계산 (STOCH, MACD_HIST context 주입)

frontend/src/
├─ data/strategyPresets.ts    ← 프리셋 8개 추가
├─ pages/StrategyBuilder.tsx  ← 프리셋 선택 UI
├─ pages/StrategyList.tsx     ← 전략 상태 요약 표시
└─ utils/dslAnalyzer.ts       ← DSL 분석 유틸 (매수/매도 수, 손절 유무)
```

## 수정 파일 목록

| 파일 | 변경 |
|------|------|
| `sv_core/parsing/builtins.py` | MACD_HIST, STOCH_K, STOCH_D, 강세/약세다이버전스 함수 등록 + 등락률 필드 추가 |
| `sv_core/parsing/evaluator.py` | 강세/약세다이버전스 전용 구현 (_eval_divergence) |
| `local_server/engine/indicator_provider.py` | STOCH_K/D, MACD_HIST 계산 함수 추가, context 주입 확인 |
| `local_server/engine/rule_evaluator.py` | 등락률 필드 context 주입, 다이버전스 context 연결 |
| `sv_core/parsing/tests/test_parser_v2.py` | 새 함수 파싱 테스트 |
| `sv_core/parsing/tests/test_evaluator_v2.py` | 새 함수 평가 테스트 (다이버전스 포함) |
| `frontend/src/data/strategyPresets.ts` | 프리셋 8개 추가, 메타데이터 확장 (난이도, 장세) |
| `frontend/src/utils/dslAnalyzer.ts` | 신규 — DSL 분석 함수 (매수/매도 규칙 수, 손절 유무) |
| `frontend/src/pages/StrategyList.tsx` | 전략 카드에 상태 요약 배지 |
| `frontend/src/pages/StrategyBuilder.tsx` | 프리셋 메타데이터 표시 (카테고리, 난이도 태그) |

---

## 구현 순서

### Step 1 — 기존 함수 엔진 연결 검증

기존 builtins.py에 등록된 함수(MACD, EMA, 볼린저, 평균거래량, 상향/하향돌파)가 실제 엔진에서 동작하는지 검증.

**작업:**
- `local_server/engine/indicator_provider.py`에서 MACD, EMA, 볼린저, 평균거래량 계산 함수 존재 확인
- `local_server/engine/rule_evaluator.py`에서 context에 위 함수들이 주입되는지 확인
- 미연결 시 연결 구현

**검증:**
- 기존 프리셋 7개 중 MACD골든크로스, 볼린저하단돌파 패턴 함수가 사용하는 기저 함수가 context에서 호출 가능한지 단위 테스트
- `python -m pytest sv_core/parsing/tests/ -v`

### Step 2 — 내장 함수 추가 (파서 레벨)

builtins.py에 새 함수/필드 등록. 파서에서 인식되게 한다.

**작업:**
- `builtins.py`에 추가:
  - `MACD_HIST`: BuiltinFuncSpec("MACD_HIST", 0, 3, "number")
  - `STOCH_K`: BuiltinFuncSpec("STOCH_K", 0, 2, "number")
  - `STOCH_D`: BuiltinFuncSpec("STOCH_D", 0, 3, "number")
  - `강세다이버전스`: BuiltinFuncSpec("강세다이버전스", 1, 2, "boolean")
  - `약세다이버전스`: BuiltinFuncSpec("약세다이버전스", 1, 2, "boolean")
- `BUILTIN_FIELDS`에 추가:
  - `"등락률"` — 전일 대비 등락률 %

**검증:**
- test_parser_v2.py에 파싱 테스트 추가:
  - `parse_v2("MACD_HIST() > 0 → 매수 100%")` 성공
  - `parse_v2("STOCH_K(5, 3) < 20 → 매수 100%")` 성공
  - `parse_v2("강세다이버전스(MACD_HIST(), 20) → 매수 100%")` 성공
  - `parse_v2("등락률 >= 3 → 매수 100%")` 성공
- `python -m pytest sv_core/parsing/tests/test_parser_v2.py -v`

### Step 3 — 엔진 지표 계산 구현

로컬 서버 엔진에서 새 함수의 실제 계산 로직 구현.

**작업:**
- `indicator_provider.py`에 추가:
  - `calc_macd_hist(closes, fast, slow, signal)` → MACD - Signal
  - `calc_stoch_k(highs, lows, closes, k_period, slowing)` → %K
  - `calc_stoch_d(highs, lows, closes, k_period, slowing, d_period)` → %D
- `rule_evaluator.py` context에 주입:
  - `"MACD_HIST"`: lambda → calc_macd_hist 호출
  - `"STOCH_K"`: lambda → calc_stoch_k 호출
  - `"STOCH_D"`: lambda → calc_stoch_d 호출
  - `"등락률"`: 전일 종가 대비 현재가 변동률

**검증:**
- 단위 테스트: 알려진 데이터셋으로 STOCH, MACD_HIST 계산 결과 검증
- `python -m pytest local_server/engine/tests/ -v`

### Step 4 — 다이버전스 함수 구현 (평가기)

evaluator.py에 강세/약세다이버전스 전용 구현. 상향돌파/하향돌파 패턴 따름.

**작업:**
- `evaluator.py`의 `_eval_func_call`에 분기 추가:
  ```python
  if name == "강세다이버전스":
      return self._eval_bullish_divergence(node)
  if name == "약세다이버전스":
      return self._eval_bearish_divergence(node)
  ```
- `_eval_bullish_divergence` 구현:
  1. 첫 번째 인자(지표 함수)를 최근 N봉에 대해 평가
  2. IndicatorHistory에서 가격 데이터 조회
  3. 로컬 저점 2개 찾기 (양쪽보다 낮은 봉, 최소 2봉 간격)
  4. 가격 저점↓ + 지표 저점↑ → True
- `_eval_bearish_divergence`: 위와 반대 (고점 기반)

**검증:**
- test_evaluator_v2.py에 테스트 추가:
  - 강세 다이버전스 시나리오 (가격↓ 지표↑) → True
  - 다이버전스 없는 시나리오 → False
  - 데이터 부족 시 (N봉 미만) → False
- `python -m pytest sv_core/parsing/tests/test_evaluator_v2.py -v`

### Step 5 — 프리셋 8개 추가

프론트엔드에 프리셋 추가 및 메타데이터 확장.

**작업:**
- `strategyPresets.ts` 타입 확장:
  ```typescript
  interface StrategyPreset {
    id: string
    name: string
    description: string
    category: string        // 추세 | 역추세 | 돌파 | 모멘텀 | 청산 | 복합
    difficulty: string      // 초보 | 중급 | 고급
    marketCondition: string // 추세장 | 횡보장 | 변동성 | 테마/이슈
    script: string
  }
  ```
- 기존 7개에 difficulty, marketCondition 추가
- 신규 8개 프리셋 추가 (spec §7의 DSL 사용)
- `StrategyBuilder.tsx` 프리셋 선택 UI에 카테고리/난이도 태그 표시

**검증:**
- 15개 프리셋 모두 `parse_v2()` 통과하는 E2E 테스트
- 프론트 빌드 성공: `cd frontend && npm run build`
- 브라우저: 프리셋 목록 15개 표시, 카테고리/난이도 태그 확인

### Step 6 — 전략 상태 요약

전략 카드에 매수/매도 규칙 수 + 손절 유무 표시.

**작업:**
- `frontend/src/utils/dslAnalyzer.ts` 신규:
  ```typescript
  interface DslSummary {
    buyCount: number    // 매수 규칙 수
    sellCount: number   // 매도 규칙 수
    hasStopLoss: boolean // 수익률 <= -N 조건 존재
  }
  function analyzeDsl(script: string): DslSummary
  ```
  - dslParserV2.ts의 parseDslV2 활용 → rules에서 action side별 카운트
  - 손절: 매도 규칙 중 `수익률` + `<=` + 음수 패턴 매칭
- `StrategyList.tsx`: RuleCard에 상태 요약 배지 추가
  ```
  매수 2 | 매도 3 | ✅ 손절
  ```

**주의:**
- parseDslV2가 v1 문법(매수:/매도:) 전략도 분석 가능한지 확인. 불가 시 v1 전략은 "분석 불가" 표시
- 다이버전스 구현 시 evaluator가 IndicatorHistory에 접근하는 경로 확인 필요 (context를 통한 간접 접근 vs 직접 참조)

**검증:**
- dslAnalyzer 단위 테스트 (프리셋 15개 모두 분석)
- 브라우저: 전략 카드에 상태 요약 표시 확인
- `cd frontend && npm run build && npm run lint`

---

## 검증 방법 (전체)

| 단계 | 검증 |
|------|------|
| Step 1~4 | `python -m pytest sv_core/parsing/tests/ -v` |
| Step 3 | `python -m pytest local_server/engine/tests/ -v` |
| Step 5~6 | `cd frontend && npm run build && npm run lint` |
| 전체 | 기존 테스트 521개 통과 (회귀 없음) |
| 브라우저 | 프리셋 15개 표시, 상태 요약 표시, 프리셋 선택 → DSL 적용 |
