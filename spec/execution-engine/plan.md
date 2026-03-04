# 실행 엔진 구현 계획서 (execution-engine)

> 작성일: 2026-03-04 | 상태: 초안 | 범위: 로컬 서버 규칙 평가 엔진 | 의존: kiwoom-integration

---

## 0. 전제 조건

- 로컬 서버에서 동작 (localhost:8765)
- 키움 COM API 연결 완료 (`spec/kiwoom-integration/plan.md` Step 1~4 완료 후)
- 컨텍스트 캐시 존재 (`spec/context-cloud/plan.md` Step 2 완료 후)

---

## 1. 구현 단계

### Step 1 — 규칙 데이터 모델

**목표**: 자동매매 규칙의 메모리 표현 정의

파일: `local_server/engine/models.py`

```python
from dataclasses import dataclass

@dataclass
class Condition:
    variable: str    # "kospi_rsi_14" | "price" | "volume" 등
    operator: str    # ">" | "<" | ">=" | "<=" | "=="
    value: float

@dataclass
class TradingRule:
    rule_id: int
    name: str
    symbol: str         # 종목 코드 (예: "005930")
    side: str           # "BUY" | "SELL"
    conditions: list[Condition]  # AND 조건 목록
    quantity: int
    is_active: bool
    last_executed: datetime | None = None
```

**검증:**
- [ ] JSON → TradingRule 파싱 단위 테스트
- [ ] 유효하지 않은 규칙 구조 → ValueError 발생

### Step 2 — 조건 평가기

**목표**: 규칙 조건을 시장 데이터 + 컨텍스트 기반으로 평가

파일: `local_server/engine/evaluator.py`

```python
class RuleEvaluator:
    def __init__(self, context: dict, price_cache: dict):
        self.ctx = context      # ContextClient.get_cached()
        self.prices = price_cache  # 종목별 현재가 (키움 실시간)

    def evaluate(self, rule: TradingRule) -> bool:
        """모든 조건이 True인 경우만 True 반환 (AND 논리)"""
        for condition in rule.conditions:
            val = self._resolve(condition.variable)
            if val is None:
                return False   # 데이터 없으면 실행 스킵
            if not self._compare(val, condition.operator, condition.value):
                return False
        return True

    def _resolve(self, variable: str) -> float | None:
        """변수명 → 실제 값 (컨텍스트 or 실시간 가격)"""
        ...
```

**검증:**
- [ ] 조건 충족 케이스 → True 반환
- [ ] 조건 미충족 케이스 → False 반환
- [ ] 데이터 없는 변수 → False (에러 아님)

### Step 3 — 신호 생성 + 중복 방지

**목표**: 조건 충족 시 주문 신호 발생 + 중복 실행 방지

파일: `local_server/engine/signal.py`

```python
class SignalManager:
    _state: dict[int, str] = {}  # rule_id → "PENDING" | "SENT" | "FILLED"

    def should_execute(self, rule: TradingRule) -> bool:
        """같은 규칙 연속 실행 방지"""
        state = self._state.get(rule.rule_id)
        if state in ("PENDING", "SENT"):
            return False
        # 당일 중복 체결 방지
        if rule.last_executed and rule.last_executed.date() == date.today():
            return False
        return True

    def mark_sent(self, rule_id: int):
        self._state[rule_id] = "SENT"

    def mark_filled(self, rule_id: int):
        self._state[rule_id] = "FILLED"
        # logs.db에 상태 업데이트
```

**검증:**
- [ ] 동일 규칙 1분 내 재실행 → 스킵
- [ ] 당일 이미 체결된 규칙 → 스킵
- [ ] 상태 머신 전환 순서 테스트

### Step 4 — 스케줄러 (1분 주기 루프)

**목표**: 1분마다 모든 활성 규칙 평가 → 신호 발생 시 키움 주문

파일: `local_server/engine/scheduler.py`

```python
class TradingScheduler:
    def __init__(self, evaluator, signal_mgr, kiwoom_order, log_db):
        ...

    def start(self):
        schedule.every(1).minutes.do(self._tick)
        schedule.run_continuously()

    def _tick(self):
        rules = config_manager.get_active_rules()
        ctx = context_client.get_cached()
        prices = kiwoom_client.get_prices([r.symbol for r in rules])

        evaluator = RuleEvaluator(ctx, prices)
        for rule in rules:
            try:
                if evaluator.evaluate(rule) and signal_mgr.should_execute(rule):
                    self._execute(rule)
            except Exception as e:
                log_db.error(rule.rule_id, str(e))
                # 해당 규칙만 비활성화 (다른 규칙 계속 실행)

    def _execute(self, rule: TradingRule):
        signal_mgr.mark_sent(rule.rule_id)
        order_no = kiwoom_order.send_order(
            account_no=local_secrets.account_no,
            symbol=rule.symbol,
            side=rule.side,
            qty=rule.quantity,
            price=0,  # 시장가
            order_type="03"
        )
        log_db.execution(rule.rule_id, order_no)
```

**장 중 시간 제한**: 09:00~15:30 KST 외 평가 스킵

**검증:**
- [ ] 1분 주기 실행 확인
- [ ] 조건 충족 규칙 → 키움 주문 호출
- [ ] 규칙 평가 오류 → 해당 규칙만 비활성화 (다른 규칙 계속)
- [ ] 장 외 시간 → 평가 스킵

### Step 5 — 실시간 규칙 갱신 (재시작 없이)

**목표**: UI에서 규칙 변경 → 스케줄러 즉시 반영

파일: `local_server/engine/scheduler.py`, `routers/trading.py`

```python
# WS 메시지 "strategy_toggle" 수신 시
scheduler.reload_rules()  # 다음 틱부터 새 규칙 반영
```

**검증:**
- [ ] 규칙 ON/OFF → 다음 1분 틱에 반영
- [ ] 새 규칙 추가 → 재시작 없이 평가 시작

---

## 2. 파일 목록

| 파일 | 내용 |
|------|------|
| `local_server/engine/models.py` | TradingRule, Condition 데이터 모델 |
| `local_server/engine/evaluator.py` | 조건 평가 로직 |
| `local_server/engine/signal.py` | 중복 방지 + 상태 머신 |
| `local_server/engine/scheduler.py` | 1분 주기 루프 + reload |
| `local_server/routers/trading.py` | `POST /api/strategy/start|stop` |

---

## 3. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — 규칙 데이터 모델 (TradingRule, Condition)` |
| 2 | `feat: Step 2 — 조건 평가기 (RuleEvaluator)` |
| 3 | `feat: Step 3 — 신호 생성 + 중복 방지 (SignalManager)` |
| 4 | `feat: Step 4 — 1분 주기 스케줄러 (TradingScheduler)` |
| 5 | `feat: Step 5 — 실시간 규칙 갱신 (reload_rules)` |
