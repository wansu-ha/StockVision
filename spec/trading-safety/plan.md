# Trading Safety — 구현 계획

> 작성일: 2026-03-13 | 상태: 초안

---

## 아키텍처

```
트레이 (_on_kill_switch)
  → HTTP POST /api/strategy/kill    ← TS-1: 기존 엔드포인트 활용
    → safeguard.set_kill_switch()

엔진 (evaluate_all, 1회/분)
  → LimitChecker.check()            ← TS-4: 재시작 복원, TS-5: 자정 리셋
  → _collect_candidates()
  → executor.execute()
    → safeguard.is_trading_enabled() ← TS-7: 수동 주문에도 적용
    → broker.place_order()
      → KisOrder._get_tr_id()       ← TS-8: is_mock 분기
    → log_db.write(LOG_TYPE_ORDER)   ← TS-3: 제출 시 ORDER 기록
  → Reconciler.reconcile_once()
    → 체결 감지 → log_db.write(LOG_TYPE_FILL)  ← TS-3: 체결 시 FILL 기록
```

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `local_server/tray/tray_app.py` | `_on_kill_switch()` → `_call_engine_api("kill")` 호출 |
| `local_server/routers/alerts.py` | GET/PUT에 `Depends(require_local_secret)` 추가 |
| `local_server/routers/trading.py` | `place_order()`에 safeguard 체크 추가, `start_strategy()`에 watchdog 주입 |
| `local_server/engine/health_watchdog.py` | (변경 없음 — 주입만 하면 동작) |
| `local_server/engine/executor.py` | (변경 없음 — 이미 ORDER/FILL 분리 기록 중) |
| `local_server/broker/kis/reconciler.py` | (변경 없음 — 이미 체결 감지 로직 존재) |
| `local_server/engine/limit_checker.py` | `restore_from_db()` 메서드 추가, `_last_date` 필드 추가 |
| `local_server/engine/engine.py` | 평가 루프 진입부에 날짜 경계 체크 + LimitChecker 복원 호출 |
| `local_server/storage/log_db.py` | `today_executed_amount()` 신규 쿼리 메서드 추가 (TS-4 복원용) |
| `local_server/broker/kis/order.py` | `place_order()` 내 TR ID 조회에 `is_mock` 분기 추가 |

---

## 구현 순서

### Step 1: alerts 인증 추가 (TS-2)

`alerts.py`의 GET/PUT 엔드포인트에 `Depends(require_local_secret)` 추가.

```python
# 실제 함수명: get_alert_settings(), update_alert_settings()
async def get_alert_settings(..., _: None = Depends(require_local_secret)):
async def update_alert_settings(..., _: None = Depends(require_local_secret)):
```

**verify**: curl로 인증 없이 호출 → 403

### Step 2: Watchdog 엔진 주입 (TS-6)

`trading.py` `start_strategy()` — `engine.start()` 호출 이후 (line 133 이후)에 한 줄 추가:

```python
request.app.state.watchdog.set_engine(engine)
```

**verify**: 엔진 시작 후 watchdog._engine is not None

### Step 3: 수동 주문 safeguard (TS-7)

`trading.py` `place_order()` (line 249에서 시작, 실제 삽입은 line 255 이후) 진입부에 safeguard 체크:

```python
engine = request.app.state.engine
if engine and not engine.safeguard.is_trading_enabled():
    raise HTTPException(400, "Kill Switch 활성 — 주문 불가")
```

**verify**: Kill Switch 활성 → POST /api/trading/order → 400

### Step 4: Kill Switch 트레이 연동 (TS-1)

`/api/strategy/kill` 엔드포인트가 이미 존재 (trading.py:169-219). `_on_kill_switch()`를 수정:

```python
def _on_kill_switch(self, *_args):
    """긴급 정지 — 엔진 API를 통해 safeguard 활성화"""
    threading.Thread(
        target=self._call_engine_api,
        args=("kill",),
        kwargs={"json_body": {"mode": "stop_new"}},
        daemon=True,
    ).start()
```

`_call_engine_api()` (tray_app.py:112-132) 시그니처 변경 필요:
- 현재: `_call_engine_api(self, action: str)` → `httpx.post(url)` (빈 body)
- 수정: `_call_engine_api(self, action: str, json_body: dict | None = None)` → `httpx.post(url, json=json_body)`

**verify**: 트레이 Kill Switch 클릭 → safeguard 활성 확인

### Step 5: LimitChecker 복원 + 자정 리셋 (TS-4, TS-5)

`limit_checker.py`에 추가:

```python
def restore_from_db(self, log_db: LogDB):
    """당일 체결 금액 복원 (주문 실행 금액 기준, P&L 아님)"""
    # today_realized_pnl()은 손익 금액이므로 사용 불가
    # 당일 LOG_TYPE_ORDER 로그에서 실행 금액(price × qty) 합산하는 전용 쿼리 필요
    today_total = log_db.today_executed_amount()  # 신규 메서드
    self._today_executed = today_total

def check_date_boundary(self):
    """날짜 경계 감지 시 리셋"""
    today = date.today()
    if self._last_date and self._last_date != today:
        self.reset_daily()
    self._last_date = today
```

`engine.py` `evaluate_all()` 진입부 (line 171 이후):

```python
self._limit_checker.check_date_boundary()
```

엔진 생성 시 `restore_from_db()` 호출.

**verify**: 엔진 재시작 후 `_today_executed` ≠ 0 (당일 체결 있을 때)

### Step 6: FILL 로그 타이밍 검증 (TS-3)

**1차 리뷰**: executor.py에 ORDER/FILL 분리 기록이 존재하지만, `LOG_TYPE_FILL`은 `place_order()` 반환 직후(line 233) 기록됨. 이 시점의 `result.status`는 `SUBMITTED`이지 `FILLED`가 아님.

**결정 필요**: Reconciler가 실체결을 감지한 후 FILL을 기록하도록 변경할지, 현재 구조를 "제출 완료 = FILL"로 재정의할지 구현 시 판단.

Option A: Reconciler 콜백 방식 (spec 원안)
- `executor.py:233`의 `LOG_TYPE_FILL` 제거
- Reconciler의 FILLED 감지 시 콜백으로 FILL 기록

Option B: 현행 유지 + 용어 재정의
- `LOG_TYPE_FILL`의 의미를 "주문 제출 완료"로 명시
- `today_realized_pnl()` 계산이 이 기준으로 동작하는지 확인

**verify**: 선택한 옵션에 따라 FILL 로그 시점 확인

### Step 7: KIS 모의투자 TR ID (TS-8)

`order.py` TR_ID_MAP에 mock 버전 추가:

```python
MOCK_TR_ID_MAP = {
    (OrderSide.BUY, OrderType.LIMIT): "VTTC0802U",
    (OrderSide.BUY, OrderType.MARKET): "VTTC0802U",
    (OrderSide.SELL, OrderType.LIMIT): "VTTC0801U",
    (OrderSide.SELL, OrderType.MARKET): "VTTC0801U",
}
```

`KisOrder`에는 `_get_tr_id()` 메서드가 없음. `place_order()` 내부(order.py:99)에서 `_ORDER_TR_ID[(side, order_type)]`를 직접 조회.
수정: `is_mock` 분기를 `place_order()` 내부에 추가하거나, `_get_tr_id()` 헬퍼 메서드를 추출.

**verify**: `is_mock=True`로 주문 → `V` 접두어 TR ID 사용 확인

### Step 8: KIS 매도 시장가 TR ID 검증 (TS-9)

KIS 공식 API 문서 대조. `TTTC0801U`가 매수/매도 공용이고 `ORD_DVSN`으로 구분하는 구조이면 이슈 해제.

**verify**: KIS API 문서 확인 또는 모의투자에서 매도 시장가 주문 성공

---

## 검증 방법

1. **빌드**: `python -c "from local_server.main import app"` — import 에러 없음
2. **기존 테스트**: `pytest local_server/tests/ -q` — 전체 통과
3. **수동 확인**:
   - alerts API 인증 차단
   - Kill Switch → safeguard 활성
   - 수동 주문 → safeguard 차단
   - LimitChecker 복원/리셋
