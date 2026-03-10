> 작성일: 2026-03-10 | 상태: 초안 | Branch: feat/engine-live-execution

# 전략 엔진 E2E 실행 — Plan

## 설계 결정

- **시세 재배포 회피**: 클라우드가 시세 데이터를 수집·중개하면 재배포에 해당할 수 있음.
  로컬 서버가 yfinance로 직접 일봉을 가져와 지표를 계산한다.
- **sv_core 추출 불필요**: cloud_server와 local_server의 지표 계산 니즈가 다름.
  코드 중복보다 독립성 우선. 각자 내부에서 계산.
- **local_server에 pandas + yfinance 추가**: 트레이딩 엔진에 자연스러운 의존성.

## 아키텍처

```
                          ┌─────────────────────┐
                          │     yfinance         │
                          │  (60일 일봉 직접 조회) │
                          └──────────┬──────────┘
                                     │ pandas DataFrame
                          ┌──────────▼──────────┐
                          │  IndicatorProvider   │  ← NEW
                          │  (로컬 직접 계산)     │
                          │  캐시: 1일 1회 갱신   │
                          └──────────┬──────────┘
                                     │ indicators dict
┌──────────┐   QuoteEvent  ┌─────────▼──────────┐   OrderResult
│ KiwoomWS │──────────────→│   StrategyEngine    │──────────────→ Broker
│ (P1 ✅)  │               │                     │
└──────────┘               │ evaluate_all():     │
                           │  latest + indicators│
    ┌──────────┐           │  → Evaluator        │
    │ Heartbeat│──rules──→│  → Executor         │
    │ (P3)     │           └─────────────────────┘
    └──────────┘
```

### 데이터 흐름

1. **시세**: KiwoomWS → QuoteEvent → BarBuilder → `latest{price, volume, timestamp}`
2. **지표**: yfinance → IndicatorProvider → `indicators{rsi_14, bb_lower_20, macd, ...}` (일봉 기반)
3. **규칙**: Cloud → Heartbeat → RulesCache → Engine
4. **평가**: `market_data = {**latest, "indicators": indicators}` → Evaluator
5. **실행**: Evaluator True → Executor → BrokerAdapter.place_order()

## 수정 파일 목록

| 단계 | 파일 | 변경 |
|------|------|------|
| S1 | `local_server/broker/kiwoom/ws.py` | ✅ 완료 — REAL 메시지 파서 |
| S2 | `local_server/requirements.txt` | pandas, yfinance 추가 |
| S2 | `local_server/engine/indicator_provider.py` (NEW) | 종목별 일봉 지표 계산 + 캐싱 |
| S3 | `local_server/engine/engine.py` | IndicatorProvider 연결 + evaluate_all() 지표 주입 |
| S4 | `local_server/cloud/heartbeat.py` | 버전 비교 타입 수정 |
| S5 | E2E 수동 검증 | — |

## 구현 순서

### Step 1: WS 파서 ✅ 완료

`ws.py`의 `_handle_message`/`_handle_quote_data`를 실제 WS 형식에 맞게 수정.
- verify: 단위 테스트 통과 (시뮬레이션 메시지 → QuoteEvent 변환)

---

### Step 2: IndicatorProvider 구현

**의존성 추가**: `local_server/requirements.txt`에 `pandas`, `yfinance` 추가

**생성 파일**: `local_server/engine/indicator_provider.py`

```python
class IndicatorProvider:
    """종목별 일봉 기반 기술적 지표 제공.

    - 엔진 시작 시 활성 종목의 지표를 일괄 계산
    - 캐시 만료: 1일 (장중 일봉 지표는 변하지 않음)
    - 데이터 소스: yfinance (60일 일봉, 한국 종목은 {code}.KS 형식)
    """

    async def refresh(self, symbols: list[str]) -> None
        """종목들의 일봉 지표를 (재)계산하여 캐시."""

    def get(self, symbol: str) -> dict
        """evaluator가 기대하는 indicators dict 반환.
        {rsi_14, ma_5, ma_20, ema_20, bb_upper_20, bb_lower_20,
         macd, macd_signal, avg_volume_20}
        """
```

내부 계산 함수 (pandas 기반, context_service.py 참고):
- `_calc_rsi(prices, period)` → RSI
- `_calc_sma(prices, period)` → 단순이동평균 (신규)
- `_calc_ema(prices, period)` → 지수이동평균
- `_calc_macd(prices)` → MACD + signal
- `_calc_bollinger(prices, period)` → 상단/하단
- `_calc_avg_volume(volumes, period)` → 평균거래량 (신규)

yfinance 한국 주식 티커: `005930` → `005930.KS` (KOSPI), `005930.KQ` (KOSDAQ)

- verify: `provider.get("005930")["rsi_14"]`가 None이 아닌 float 반환

---

### Step 3: 엔진 지표 주입

`engine.py`의 `_evaluate_rule()` 수정:

```python
# BEFORE
latest = self._bar_builder.get_latest(symbol)
buy, sell = self._evaluator.evaluate(rule, latest, context)

# AFTER
latest = self._bar_builder.get_latest(symbol)
latest["indicators"] = self._indicator_provider.get(symbol)
buy, sell = self._evaluator.evaluate(rule, latest, context)
```

엔진 `__init__`에 IndicatorProvider 추가, `start()`에서 refresh 호출.

- verify: 로그에 `"Rule X BUY: SUCCESS"` 또는 `"REJECTED"` (None 아닌 평가 결과)

---

### Step 4: Heartbeat 버전 비교 수정

`heartbeat.py`에서 `rules_version` 비교 시 타입 통일:

```python
# BEFORE (잠재 버그: int != str 항상 True)
if rules_ver != self._last_rules_ver:

# AFTER
if str(rules_ver) != str(self._last_rules_ver):
```

- verify: heartbeat 로그에서 불필요한 중복 fetch 없음

---

### Step 5: E2E 수동 검증

1. 도커 재빌드 (cloud_server)
2. 로컬 서버 재시작
3. 프론트엔드에서 규칙 확인 (RSI ≤ 30 매수 등)
4. `POST /api/strategy/start` → 엔진 시작
5. WS 시세 수신 로그 확인
6. 지표 계산 로그 확인
7. 규칙 평가 결과 로그 확인
8. 주문 실행 또는 REJECTED 사유 확인
9. `GET /api/logs?log_type=fill` → 체결 내역 확인

- verify: logs.db에 최소 1건의 fill 또는 명확한 REJECTED 사유

## 검증 방법

| 항목 | 방법 |
|------|------|
| WS 파서 | 단위 테스트 (시뮬레이션 메시지) |
| 지표 계산 | `calc_rsi(prices, 14)` 반환값 vs 수동 계산 |
| IndicatorProvider | `provider.get("005930")` 키 존재 + 값 범위 확인 |
| 규칙 동기화 | 프론트엔드 규칙 생성 → 30초 후 `GET /api/rules` 확인 |
| E2E 주문 | 모의서버 잔고 변동 + fill 로그 |

## 의존성 순서

```
S1 (WS 파서) ✅ ─────────┐
                          ├──→ S3 (엔진 주입) ──→ S5 (E2E 검증)
S2 (IndicatorProvider) ──┘                           │
                                                      │
S4 (Heartbeat 수정) ──────────────────────────────────┘
```

S1 ✅ 완료. S2→S3 순차. S4는 독립적이므로 병렬 가능.
