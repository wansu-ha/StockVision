# 전략 엔진 잔여 구현 계획 (strategy-engine)

> 작성일: 2026-03-09 | 상태: 구현 완료 | Unit 3 잔여분
>
> **이전 plan**: v2 (2026-03-07) — 8 Steps 중 대부분 완료. 본 plan은 미완성 항목만 다룬다.

---

## 1. 현황

### 구현 완료 (spec §6 수용 기준 기준)

- **6.1 스케줄러**: EngineScheduler (APScheduler cron), start/stop API 라우터
- **6.2 조건 평가**: RuleEvaluator (DSL + JSON v1 폴백), AST 캐시, 상향돌파/하향돌파 state
- **6.3 중복 방지**: SignalManager (매수/매도 독립 상태, 일일 리셋, ONCE 정책 콜백)
- **6.4 가격 검증**: PriceVerifier (BrokerAdapter.get_quote, 1% 괴리 임계값)
- **6.5 주문 실행**: OrderExecutor 파이프라인 + `_on_execution` 콜백 (logs.db 기록 + WS 브로드캐스트)
- **6.6 한도**: LimitChecker (일일 예산, 최대 포지션 수)
- **6.7 Kill Switch**: STOP_NEW/CANCEL_OPEN 2단계 + 라우터에서 미체결 취소 구현
- **6.7 최대 손실 제한**: check_max_loss (실현손익 기준), loss_lock, 수동 해제 (unlock API)
- **6.7 주문 속도 제한**: 분당 주문 수 체크 + 차단
- **6.8 분봉**: BarBuilder (WS 시세 → 1분 OHLCV), SYNCING 상태 (09:00~09:02)

### 미완성 (2건)

| # | spec 항목 | 설명 | 우선순위 |
|---|----------|------|---------|
| A | §6.7 최대 손실 발동 시 CANCEL_OPEN 자동 실행 | `check_max_loss()`에서 loss_lock만 설정하고, 미체결 자동 취소 + WS 알림 없음 | P0 |
| B | §6.8 WS 끊김 복구 시 누락 분봉 REST 보충 | BarBuilder에 REST 폴백 로직 없음 | P1 |

### 코드 분석 상세

**A. 최대 손실 → CANCEL_OPEN 미연결**

`safeguard.py`의 `check_max_loss()`는 `self._state.loss_lock = True`를 설정하지만,
`set_kill_switch(CANCEL_OPEN)` 호출이나 미체결 취소 로직이 없다.
spec은 "발동 시: CANCEL_OPEN 자동 실행 + 트레이/프론트 알림"을 요구한다.

현재 흐름:
```
engine.evaluate_all()
  → safeguard.check_max_loss(pnl, balance) → loss_lock = True
  → is_trading_enabled() → False (이후 주문 차단)
```

필요한 흐름:
```
engine.evaluate_all()
  → safeguard.check_max_loss(pnl, balance) → loss_lock = True
  → (NEW) broker.get_open_orders() → broker.cancel_order(each) → 미체결 전량 취소
  → (NEW) WS 브로드캐스트: 손실 제한 알림
  → (NEW) logs.db: 손실 제한 발동 이벤트 기록
```

CANCEL_OPEN의 실제 취소 로직은 이미 `trading.py`의 `kill_strategy()` 엔드포인트에 구현되어 있다.
엔진 레벨에서 동일한 취소 흐름을 트리거하면 된다.

**B. WS 복구 시 분봉 REST 보충**

BarBuilder는 WS가 끊긴 동안의 분봉을 복구하는 메서드가 없다.
P1이며, WS가 재연결되면 자연적으로 새 분봉이 쌓이기 시작한다.
정확한 REST 엔드포인트는 증권사 API에 따라 다르므로 v2에서 다루는 것이 적절할 수 있다.

---

## 2. 구현 순서

### Step 1: 최대 손실 발동 → 미체결 취소 + 알림

**목표**: `check_max_loss()` 반환값이 False일 때, 엔진이 미체결 취소 + WS 알림 + 로그 기록을 수행

**변경 파일**: `local_server/engine/engine.py`

**변경 내용**:

`evaluate_all()` 내 `check_max_loss()` 호출 이후 분기 추가:

```python
# 최대 손실 제한 체크 (당일 실현손익 from logs.db)
if self._safeguard.is_trading_enabled():
    from local_server.storage.log_db import get_log_db
    today_pnl = get_log_db().today_realized_pnl()
    loss_ok = self._safeguard.check_max_loss(today_pnl, balance.cash + balance.total_eval)
    if not loss_ok:
        # 미체결 전량 취소
        await self._cancel_open_orders()
        # WS 알림 + 로그
        self._notify_loss_lock(today_pnl)
```

새 메서드 2개:

1. `_cancel_open_orders()`: `self._broker.get_open_orders()` → 각 order에 `cancel_order()` 호출
2. `_notify_loss_lock(pnl)`: `_on_execution` 콜백 또는 직접 WS 브로드캐스트 + logs.db 기록

`_cancel_open_orders()`는 `trading.py`의 `kill_strategy()` 내 CANCEL_OPEN 로직과 동일한 패턴:
```python
async def _cancel_open_orders(self) -> int:
    cancelled = 0
    try:
        open_orders = await self._broker.get_open_orders()
        for order in open_orders:
            try:
                await self._broker.cancel_order(order.order_id)
                cancelled += 1
            except Exception as e:
                logger.error("미체결 취소 실패 (order_id=%s): %s", order.order_id, e)
    except Exception as e:
        logger.error("미체결 조회 실패: %s", e)
    return cancelled
```

**verify**:
- 테스트: `check_max_loss()` 반환 False 시 `broker.get_open_orders()` + `cancel_order()` 호출 확인
- 테스트: WS 브로드캐스트 메시지에 loss_lock 알림 포함 확인
- 테스트: logs.db에 `LOG_TYPE_STRATEGY` "최대 손실 제한 발동" 이벤트 기록 확인

---

### Step 2: WS 복구 시 누락 분봉 REST 보충 (P1)

**목표**: WS 재연결 시 끊긴 동안의 분봉을 REST로 보충

**변경 파일**: `local_server/engine/bar_builder.py`

**변경 내용**:

1. `BarBuilder`에 `last_quote_time` 추적 필드 추가
2. `fill_gap(symbol, broker)` 메서드 추가:
   - `last_quote_time`과 현재 시각 사이 간격 > 2분이면 gap으로 판단
   - `broker.get_quote(symbol)` (또는 차트 API)로 현재가 조회하여 누락 구간 보충
   - v1은 단순히 현재가를 하나의 분봉으로 채워 gap을 메우는 수준

3. `engine.py`의 `_on_quote()` 또는 WS 재연결 콜백에서 `fill_gap()` 호출

**주의**: 증권사 API별 차트/분봉 REST 엔드포인트가 다름. v1은 `get_quote()`로 최소한의 gap fill만 수행.

**verify**:
- 테스트: 3분 gap 이후 `fill_gap()` 호출 시 completed bar가 채워지는지 확인
- 테스트: gap 없을 때 `fill_gap()` 호출 시 아무 변경 없음 확인

---

### Step 3: 통합 테스트 보강

**목표**: E2E 파이프라인 (규칙 평가 → 주문 → 로그 + WS) 및 손실 락 시나리오 검증

**변경 파일**: `local_server/tests/test_engine.py`

**추가 테스트**:

1. **손실 락 → 미체결 취소 통합**:
   - MockBrokerAdapter에 `get_open_orders()`가 미체결 주문 2건 반환하도록 설정
   - `check_max_loss()` 임계값 초과 → `cancel_order()` 2회 호출 확인
   - WS/로그 알림 확인

2. **ONCE 정책 통합**:
   - `trigger_policy.frequency == "ONCE"` 규칙 체결 → deactivate 콜백 호출 확인

3. **E2E evaluate_all 흐름** (선택적):
   - StrategyEngine 인스턴스에 MockBrokerAdapter + 규칙 설정
   - BarBuilder에 시세 주입
   - `evaluate_all()` 호출
   - ExecutionResult가 `_on_execution` 콜백으로 전달되는지 확인

**verify**:
- `pytest local_server/tests/test_engine.py -v` 전체 통과

---

## 3. 수정 파일 목록

| 파일 | 변경 수준 | Step |
|------|----------|------|
| `local_server/engine/engine.py` | 수정 (메서드 2개 추가) | 1 |
| `local_server/engine/bar_builder.py` | 수정 (`fill_gap` 추가) | 2 |
| `local_server/tests/test_engine.py` | 수정 (테스트 추가) | 1, 2, 3 |

---

## 4. 검증 체크리스트

- [ ] Step 1: `check_max_loss()` False → `_cancel_open_orders()` 호출 → 미체결 취소
- [ ] Step 1: 손실 락 발동 → WS 브로드캐스트 알림 전송
- [ ] Step 1: 손실 락 발동 → logs.db `LOG_TYPE_STRATEGY` 이벤트 기록
- [ ] Step 2: WS gap > 2분 → `fill_gap()` → 현재가로 분봉 보충
- [ ] Step 2: gap 없으면 `fill_gap()` 무동작
- [ ] Step 3: 기존 41개 테스트 + 신규 테스트 전체 통과
- [ ] `pytest local_server/tests/test_engine.py -v` 전체 PASSED

---

## 참고

- 기존 plan v2 (2026-03-07): 8 Steps 대부분 완료 — 본 plan은 잔여분만
- `spec/strategy-engine/spec.md` §6 수용 기준
- `local_server/routers/trading.py` — CANCEL_OPEN 참조 구현 (kill_strategy 엔드포인트)
- `local_server/routers/ws.py` — ConnectionManager.broadcast() 참조

---

**마지막 갱신**: 2026-03-09
