# 전략 엔진 구현 계획서 (strategy-engine)

> 작성일: 2026-03-05 | 상태: 초안 | Unit 3 (Phase 3-A) | 위치: `local_server/engine/`

---

## 0. 현황 및 의존성

### 기존 코드 상태
- `spec/execution-engine/` 존재 (대체됨 — 클라우드 WS 신호 전송 방식)
- 로컬 서버 기반 구조로 전환됨 (spec/strategy-engine/spec.md)
- BrokerAdapter 인터페이스 준비 중 (Unit 1)
- 로컬 서버 코어 구조 초기화 필요 (Unit 2)

### 의존성 (Blocking)
1. **Unit 1 (kiwoom-integration)**: BrokerAdapter 인터페이스 + KiwoomAdapter 구현
   - `get_current_price()`, `send_order()`, `cancel_order()` 등
   - WS 실시간 시세 스트림
2. **Unit 2 (local-server-core)**: 로컬 서버 기반 구조
   - FastAPI 앱, 라우터 구조
   - logs.db (SQLite) 스키마
   - WS 통신 기반
   - JWT/Credential Manager 통합

### 참고 문서
- 아키텍처: `docs/architecture.md` §3.1 (주문 흐름), §4.4 (로컬 서버)
- 개발 계획: `docs/development-plan-v2.md` Unit 3
- spec: `spec/strategy-engine/spec.md` (본 문서의 기반)
- 규칙 데이터 모델: `spec/rule-model/spec.md` (매수/매도 분리, 조건 타입, 트리거 정책)

---

## 1. 구현 단계 (10 Steps)

### Step 1: EngineScheduler (APScheduler 1분 주기)

**목표**: 장 시간(월~금 09:00~15:30) 1분 주기로 `evaluate_all()` 호출

**파일**: `local_server/engine/scheduler.py`

**구현 내용**:
```python
class EngineScheduler:
    """장 시간 1분 주기로 규칙 평가 실행."""

    def __init__(self, engine):
        self._engine = engine
        self._scheduler = AsyncIOScheduler()
        self._running = False

    async def start(self):
        """엔진 시작. 장 시간에만 실행."""
        self._scheduler.add_job(
            self._engine.evaluate_all,
            trigger="cron",
            day_of_week="mon-fri",
            hour="9-15",
            minute="*",
            second=0,
            timezone="Asia/Seoul",
        )
        self._scheduler.start()
        self._running = True

    async def stop(self):
        """엔진 중지."""
        self._scheduler.shutdown(wait=False)
        self._running = False

    async def is_running(self) -> bool:
        return self._running
```

**검증**:
- [ ] 월~금 09:00~15:30에만 실행 확인
- [ ] 장외 시간에는 실행 안 됨
- [ ] 1분마다 정확히 호출
- [ ] `start()`, `stop()` API 정상 동작

---

### Step 2: RuleEvaluator (조건 평가: AND/OR, 매수/매도 분리)

> 규칙 데이터 모델: `spec/rule-model/spec.md` §4 참조

**목표**: 규칙의 buy_conditions / sell_conditions를 현재 데이터로 평가 → True/False 반환

**파일**: `local_server/engine/evaluator.py`

**구현 내용**:
```python
class RuleEvaluator:
    """규칙 조건을 현재 데이터로 평가. 매수/매도 조건을 분리 평가."""

    def evaluate_buy(self, rule: dict, market_data: dict, context: dict) -> bool:
        """
        rule의 buy_conditions 평가.
        rule: { buy_conditions: { operator: "AND", conditions: [...] }, ... }
        market_data: { price, volume, rsi_14, ... }  (BrokerAdapter WS에서)
        context: { market_kospi_rsi, ... }  (AI 컨텍스트 캐시에서)
        """
        buy_conds = rule.get("buy_conditions")
        if not buy_conds:
            return False
        return self._evaluate_group(buy_conds, market_data, context)

    def evaluate_sell(self, rule: dict, market_data: dict, context: dict) -> bool:
        """
        rule의 sell_conditions 평가.
        rule: { sell_conditions: { operator: "AND", conditions: [...] }, ... }
        """
        sell_conds = rule.get("sell_conditions")
        if not sell_conds:
            return False
        return self._evaluate_group(sell_conds, market_data, context)

    def _evaluate_group(self, group: dict, market_data: dict, context: dict) -> bool:
        """조건 그룹 (operator + conditions) 평가."""
        conditions = group.get("conditions", [])
        op = group.get("operator", "AND")

        results = [self._eval_single(c, market_data, context) for c in conditions]

        if op == "AND":
            return all(results) if results else False
        elif op == "OR":
            return any(results) if results else False
        else:
            return False

    def _eval_single(self, condition: dict, market_data: dict, context: dict) -> bool:
        """단일 조건 평가."""
        cond_type = condition.get("type")
        operator = condition.get("operator")

        # cross_above / cross_below는 별도 처리 (previous 데이터 필요)
        if operator in ("cross_above", "cross_below"):
            return self._eval_cross(condition, market_data)

        # 데이터 소스 선택
        if cond_type in ("price", "indicator", "volume"):
            value = market_data.get(condition["field"])
        elif cond_type == "context":
            value = context.get(condition["field"])
        else:
            return False

        if value is None:
            return False

        return self._compare(value, operator, condition["value"])

    def _eval_cross(self, condition: dict, market_data: dict) -> bool:
        """
        cross_above / cross_below 평가.
        previous 데이터는 BarBuilder에서 직전 분봉으로 제공.
        market_data: { "field": current_value, "_prev": { "field": prev_value } }
        """
        field = condition["field"]
        op = condition["operator"]
        value = condition["value"]

        current = market_data.get(field)
        previous = market_data.get("_prev", {}).get(field)

        if current is None or previous is None:
            return False

        if op == "cross_above":
            return previous < value and current >= value
        if op == "cross_below":
            return previous > value and current <= value
        return False

    def _compare(self, value, operator: str, expected: float) -> bool:
        """비교 연산자 수행."""
        ops = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
            "cross_above": None,  # _eval_cross에서 처리
            "cross_below": None,  # _eval_cross에서 처리
        }
        op_func = ops.get(operator)
        if not op_func:
            return False
        try:
            return op_func(value, expected)
        except (TypeError, ValueError):
            return False
```

**검증**:
- [ ] AND 조건: 모든 조건 True → True, 하나 False → False
- [ ] OR 조건: 하나 True → True, 모두 False → False
- [ ] 비교 연산자 정상 동작 (<, <=, >, >=, ==, !=)
- [ ] `cross_above`: 직전 < value AND 현재 >= value → True
- [ ] `cross_below`: 직전 > value AND 현재 <= value → True
- [ ] cross 연산자: previous 데이터 없으면 → False
- [ ] `evaluate_buy`: buy_conditions 평가, 없으면 False
- [ ] `evaluate_sell`: sell_conditions 평가, 없으면 False
- [ ] 없는 조건 타입 → False 반환
- [ ] 데이터 미존재 시 → False 반환

---

### Step 3: SignalManager (신호 상태 관리, 매수/매도 분리, 트리거 정책)

**목표**: 매수/매도별 독립 상태 관리, 트리거 정책(ONCE_PER_DAY, ONCE) 지원

**파일**: `local_server/engine/signal_manager.py`

**구현 내용**:
```python
from datetime import date

class SignalManager:
    """신호 상태 머신. 매수/매도 별도 트래킹."""

    # 상태: IDLE → TRIGGERED → FILLED/FAILED
    # ONCE_PER_DAY: 매일 자정에 IDLE로 리셋
    # ONCE: 1회 실행 후 규칙 비활성화

    def __init__(self, rule_cache=None):
        self._buy_states: dict[int, str] = {}   # rule_id → state (매수)
        self._sell_states: dict[int, str] = {}   # rule_id → state (매도)
        self._last_reset: date = date.today()
        self._rule_cache = rule_cache  # ONCE 정책 시 규칙 비활성화용

    def can_trigger_buy(self, rule_id: int) -> bool:
        """매수 실행 가능 여부."""
        self._check_daily_reset()
        return self._buy_states.get(rule_id, "IDLE") == "IDLE"

    def can_trigger_sell(self, rule_id: int) -> bool:
        """매도 실행 가능 여부."""
        self._check_daily_reset()
        return self._sell_states.get(rule_id, "IDLE") == "IDLE"

    def mark_triggered(self, rule_id: int, side: str):
        """신호 발생 마킹. side: 'BUY' | 'SELL'"""
        states = self._buy_states if side == "BUY" else self._sell_states
        states[rule_id] = "TRIGGERED"

    def mark_filled(self, rule_id: int, side: str, trigger_policy: str = "ONCE_PER_DAY"):
        """주문 체결 마킹. ONCE 정책이면 규칙 비활성화."""
        states = self._buy_states if side == "BUY" else self._sell_states
        states[rule_id] = "FILLED"

        if trigger_policy == "ONCE" and self._rule_cache:
            self._rule_cache.deactivate(rule_id)

    def mark_failed(self, rule_id: int, side: str):
        """주문 실패 마킹."""
        states = self._buy_states if side == "BUY" else self._sell_states
        states[rule_id] = "FAILED"

    def reset_all(self):
        """모든 규칙 리셋 (테스트용)."""
        self._buy_states.clear()
        self._sell_states.clear()
        self._last_reset = date.today()

    def _check_daily_reset(self):
        """자정 기준 일일 리셋 (ONCE_PER_DAY 정책)."""
        if date.today() > self._last_reset:
            self._buy_states.clear()
            self._sell_states.clear()
            self._last_reset = date.today()

    def get_state(self, rule_id: int, side: str) -> str:
        """현재 상태 조회."""
        self._check_daily_reset()
        states = self._buy_states if side == "BUY" else self._sell_states
        return states.get(rule_id, "IDLE")
```

**검증**:
- [ ] 같은 규칙 매수/매도 각각 하루 1회 실행 (ONCE_PER_DAY)
- [ ] 매수 실행 후에도 매도는 독립적으로 실행 가능
- [ ] 자정 기준 매수/매도 상태 모두 리셋 확인
- [ ] 상태 전이 정상 (IDLE → TRIGGERED → FILLED)
- [ ] ONCE 정책: 1회 체결 → RuleCache.deactivate() 호출 확인
- [ ] ONCE_PER_DAY 정책: 다음날 자정 리셋 후 재실행 가능
- [ ] 여러 규칙 독립 관리

---

### Step 4: PriceVerifier (가격 검증)

**목표**: 주문 전 BrokerAdapter로 현재가 재확인, WS 수신 가격과 비교

**파일**: `local_server/engine/price_verifier.py`

**구현 내용**:
```python
from dataclasses import dataclass

@dataclass
class VerifyResult:
    ok: bool
    actual_price: int
    expected_price: int
    diff_pct: float

class PriceVerifier:
    """주문 전 BrokerAdapter로 현재가를 재확인."""

    TOLERANCE_PCT = 1.0  # 1% 괴리 허용

    def __init__(self, broker_adapter):
        self._broker = broker_adapter

    async def verify(self, symbol: str, expected_price: int) -> VerifyResult:
        """
        BrokerAdapter로 현재가 조회 → WS 수신 가격과 비교.
        괴리 > TOLERANCE_PCT → 거부.
        """
        try:
            actual_price = await self._broker.get_current_price(symbol)
        except Exception as e:
            # 조회 실패 → 보수적으로 거부
            return VerifyResult(
                ok=False,
                actual_price=0,
                expected_price=expected_price,
                diff_pct=999.0,
            )

        if expected_price == 0:
            return VerifyResult(
                ok=False,
                actual_price=actual_price,
                expected_price=expected_price,
                diff_pct=999.0,
            )

        diff_pct = abs(actual_price - expected_price) / expected_price * 100

        ok = diff_pct <= self.TOLERANCE_PCT

        return VerifyResult(
            ok=ok,
            actual_price=actual_price,
            expected_price=expected_price,
            diff_pct=diff_pct,
        )
```

**검증**:
- [ ] WS 가격과 REST 가격 괴리 < 1% → OK
- [ ] 괴리 > 1% → 거부
- [ ] BrokerAdapter 조회 실패 시 → 거부 (보수적)
- [ ] 가격 0인 경우 → 거부

---

### Step 5: LimitChecker (한도 체크: 일일 예산, 포지션 수)

**목표**: 일일 거래 예산, 최대 포지션 수 체크

**파일**: `local_server/engine/limit_checker.py`

**구현 내용**:
```python
from dataclasses import dataclass
from datetime import date

@dataclass
class CheckResult:
    ok: bool
    reason: str = ""

class LimitChecker:
    """일일 한도, 포지션 수 체크."""

    def __init__(self, logs_db, config: dict):
        self._logs = logs_db
        self._budget_ratio = config.get("budget_ratio", 0.1)  # 계좌의 10%
        self._max_positions = config.get("max_positions", 5)

    async def check_budget(self, account_balance: float, order_amount: float) -> CheckResult:
        """일일 예산 체크."""
        max_daily_budget = account_balance * self._budget_ratio

        # 오늘 이미 체결된 주문 금액 합산
        today_executed = await self._logs.get_today_executed_amount()

        if today_executed + order_amount > max_daily_budget:
            return CheckResult(
                ok=False,
                reason=f"일일 예산 초과 ({today_executed + order_amount:.0f} > {max_daily_budget:.0f})"
            )

        return CheckResult(ok=True)

    async def check_max_positions(self, current_positions: int) -> CheckResult:
        """최대 포지션 수 체크."""
        if current_positions >= self._max_positions:
            return CheckResult(
                ok=False,
                reason=f"포지션 수 초과 ({current_positions} >= {self._max_positions})"
            )

        return CheckResult(ok=True)
```

**검증**:
- [ ] 일일 예산(budget_ratio) 초과 시 스킵
- [ ] 최대 포지션 수 초과 시 스킵
- [ ] 정상 범위 내 → OK 반환

---

### Step 6: Safeguard (안전장치: Kill Switch + 손실 제한 + 주문 속도 제한)

**목표**: Kill Switch 2단계, 최대 손실 제한, 주문 속도 제한

**파일**: `local_server/engine/safeguard.py`

**구현 내용**:
```python
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass

class KillSwitchLevel(Enum):
    OFF = 0
    STOP_NEW = 1  # 신규 주문 차단
    CANCEL_OPEN = 2  # 신규 차단 + 미체결 취소

@dataclass
class SafeguardState:
    kill_switch: KillSwitchLevel = KillSwitchLevel.OFF
    loss_lock: bool = False  # 최대 손실 제한 락
    orders_this_minute: int = 0
    last_minute_reset: datetime = None

class Safeguard:
    """Kill Switch + 최대 손실 제한 + 주문 속도 제한."""

    DEFAULT_LOSS_THRESHOLD_PCT = 5.0  # 5%
    DEFAULT_MAX_ORDERS_PER_MINUTE = 10  # 10건/분

    def __init__(self, logs_db, config: dict):
        self._logs = logs_db
        self._loss_threshold = config.get("max_loss_pct", self.DEFAULT_LOSS_THRESHOLD_PCT)
        self._max_orders_per_min = config.get("max_orders_per_minute", self.DEFAULT_MAX_ORDERS_PER_MINUTE)
        self._state = SafeguardState()

    async def check_trading_enabled(self) -> bool:
        """Trading Enabled 여부 확인."""
        if self._state.kill_switch != KillSwitchLevel.OFF:
            return False
        if self._state.loss_lock:
            return False
        return True

    async def check_order_speed(self) -> bool:
        """주문 속도 제한 체크."""
        now = datetime.now()

        if self._state.last_minute_reset is None or \
           (now - self._state.last_minute_reset).total_seconds() > 60:
            self._state.orders_this_minute = 0
            self._state.last_minute_reset = now

        if self._state.orders_this_minute >= self._max_orders_per_min:
            return False

        return True

    def increment_order_count(self):
        """주문 카운트 증가."""
        self._state.orders_this_minute += 1

    async def check_max_loss(self, account_balance: float) -> bool:
        """최대 손실 제한 체크."""
        today_realized_pnl = await self._logs.get_today_realized_pnl()
        loss_pct = abs(today_realized_pnl) / account_balance * 100 if account_balance > 0 else 0

        if today_realized_pnl < 0 and loss_pct > self._loss_threshold:
            self._state.loss_lock = True
            return False

        return True

    def set_kill_switch(self, level: KillSwitchLevel):
        """Kill Switch 설정."""
        self._state.kill_switch = level

    def unlock_loss_lock(self):
        """손실 락 해제."""
        self._state.loss_lock = False

    def is_loss_locked(self) -> bool:
        """손실 락 상태 확인."""
        return self._state.loss_lock

    def get_state(self) -> SafeguardState:
        """안전장치 상태 조회."""
        return self._state
```

**검증**:
- [ ] Kill Switch STOP_NEW → Trading Enabled = OFF
- [ ] Kill Switch CANCEL_OPEN → 미체결 주문 취소 + Trading OFF
- [ ] 최대 손실 제한 발동 시 CANCEL_OPEN 실행 + 락
- [ ] 분당 주문 수 > 한도 → 주문 차단
- [ ] 락 해제는 수동만 (자동 해제 불가)

---

### Step 7: OrderExecutor (주문 실행 파이프라인, 매수/매도 분리)

**목표**: buy_conditions/sell_conditions 기반 주문 실행, 보유 여부 판단, 결과 로그, WS 알림

**파일**: `local_server/engine/executor.py`

**변경 요약** (기존 대비):
- `rule.get("side")` → buy_conditions/sell_conditions 충족 결과에 따라 side 결정
- `rule.get("qty")` → `rule["execution"]["qty_value"]`
- `rule.get("order_type")` → `rule["execution"]["order_type"]`
- 매수: buy_conditions 충족 + 미보유 → BUY
- 매도: sell_conditions 충족 + 보유 중 → SELL
- 보유 여부 판단: 당일 체결 로그(logs.db) + 엔진 내 메모리 상태(`_holdings`)

**구현 내용**:
```python
from dataclasses import dataclass
from enum import Enum

class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    REJECTED = "rejected"

@dataclass
class ExecutionResult:
    status: ExecutionStatus
    rule_id: int
    symbol: str
    side: str
    message: str
    order_id: str = None

class OrderExecutor:
    """조건 충족 → 가격 검증 → BrokerAdapter 주문."""

    def __init__(self, broker, signal_manager, price_verifier, limit_checker,
                 safeguard, logs_db, ws_manager):
        self._broker = broker
        self._signal_manager = signal_manager
        self._price_verifier = price_verifier
        self._limit_checker = limit_checker
        self._safeguard = safeguard
        self._logs = logs_db
        self._ws = ws_manager
        self._holdings: dict[str, int] = {}  # symbol → 보유 수량 (당일 메모리)

    def is_holding(self, symbol: str) -> bool:
        """해당 종목 보유 여부."""
        return self._holdings.get(symbol, 0) > 0

    def update_holding(self, symbol: str, qty_delta: int):
        """보유 상태 업데이트. 매수: +qty, 매도: -qty."""
        current = self._holdings.get(symbol, 0)
        self._holdings[symbol] = max(0, current + qty_delta)

    async def execute(self, rule: dict, side: str, market_data: dict,
                      account_state: dict) -> ExecutionResult:
        """
        주문 실행 파이프라인:
        1. 중복 체크 (SignalManager, 매수/매도 분리)
        2. 한도 체크 (LimitChecker)
        3. 안전장치 체크 (Safeguard)
        4. 가격 검증 (PriceVerifier)
        5. 주문 실행 (BrokerAdapter)
        6. 보유 상태 업데이트
        7. 결과 로그 (logs.db)
        8. WS 알림 (프론트엔드)

        side: 'BUY' | 'SELL' — 호출측(StrategyEngine)에서 결정
        """
        rule_id = rule.get("id")
        symbol = rule.get("symbol")
        execution = rule.get("execution", {})
        qty = execution.get("qty_value", 1)
        order_type = execution.get("order_type", "MARKET")
        trigger_policy = rule.get("trigger_policy", {}).get("frequency", "ONCE_PER_DAY")

        # 1. 중복 체크 (매수/매도 분리)
        if side == "BUY" and not self._signal_manager.can_trigger_buy(rule_id):
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id, symbol=symbol, side=side,
                message="오늘 이미 매수 실행된 규칙"
            )
        if side == "SELL" and not self._signal_manager.can_trigger_sell(rule_id):
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id, symbol=symbol, side=side,
                message="오늘 이미 매도 실행된 규칙"
            )

        # 2. 한도 체크
        order_amount = market_data.get("price", 0) * qty
        budget_check = await self._limit_checker.check_budget(
            account_state.get("balance", 0),
            order_amount
        )
        if not budget_check.ok:
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id, symbol=symbol, side=side,
                message=budget_check.reason
            )

        positions_check = await self._limit_checker.check_max_positions(
            len(account_state.get("positions", []))
        )
        if side == "BUY" and not positions_check.ok:
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id, symbol=symbol, side=side,
                message=positions_check.reason
            )

        # 3. 안전장치 체크
        if not await self._safeguard.check_trading_enabled():
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id, symbol=symbol, side=side,
                message="Trading Enabled = OFF (Kill Switch 또는 손실 락)"
            )

        if not await self._safeguard.check_order_speed():
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id, symbol=symbol, side=side,
                message="주문 속도 제한 초과"
            )

        balance = await self._broker.get_balance(self._account_no)
        if not await self._safeguard.check_max_loss(balance.total_balance):
            await self._safeguard.set_kill_switch(KillSwitchLevel.CANCEL_OPEN)
            for pos in await self._broker.get_positions(self._account_no):
                if pos.open_order_no:
                    await self._broker.cancel_order(pos.open_order_no)
            message = "최대 손실 제한 발동 — CANCEL_OPEN 실행"
            await self._logs.record_safeguard_event("max_loss_trigger", message)
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id, symbol=symbol, side=side,
                message=message
            )

        # 4. 가격 검증
        self._signal_manager.mark_triggered(rule_id, side)

        ws_price = market_data.get("price", 0)
        verify_result = await self._price_verifier.verify(symbol, ws_price)

        if not verify_result.ok:
            self._signal_manager.mark_failed(rule_id, side)
            message = f"가격 검증 실패 (WS: {ws_price}, REST: {verify_result.actual_price}, 괴리: {verify_result.diff_pct:.2f}%)"
            await self._logs.record_execution_log(rule_id, symbol, "PRICE_MISMATCH", message)
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                rule_id=rule_id, symbol=symbol, side=side,
                message=message
            )

        # 5. 주문 실행
        try:
            order_result = await self._broker.send_order(
                symbol=symbol,
                side=side,
                qty=qty,
                price=verify_result.actual_price,
                order_type=order_type
            )

            # 6. 보유 상태 업데이트
            if side == "BUY":
                self.update_holding(symbol, qty)
            else:
                self.update_holding(symbol, -qty)

            # 7. 결과 로그
            self._safeguard.increment_order_count()
            self._signal_manager.mark_filled(rule_id, side, trigger_policy)

            await self._logs.record_execution_log(
                rule_id, symbol, "ORDER_SENT",
                f"Side: {side}, Order ID: {order_result.order_id}, Price: {verify_result.actual_price}"
            )

            # 8. WS 알림
            await self._ws.broadcast({
                "type": "execution",
                "status": "success",
                "rule_id": rule_id,
                "symbol": symbol,
                "side": side,
                "order_id": order_result.order_id,
            })

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                rule_id=rule_id, symbol=symbol, side=side,
                order_id=order_result.order_id,
                message="주문 성공"
            )

        except Exception as e:
            self._signal_manager.mark_failed(rule_id, side)
            await self._logs.record_execution_log(
                rule_id, symbol, "ORDER_FAILED", str(e)
            )
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                rule_id=rule_id, symbol=symbol, side=side,
                message=f"주문 실행 실패: {str(e)}"
            )
```

**검증**:
- [ ] 매수: buy_conditions 충족 + 미보유 → BUY 주문 성공
- [ ] 매도: sell_conditions 충족 + 보유 중 → SELL 주문 성공
- [ ] 매수 후 `_holdings` 에 보유 수량 추가 확인
- [ ] 매도 후 `_holdings` 에서 보유 수량 제거 확인
- [ ] `execution.qty_value`, `execution.order_type` 필드 참조 확인
- [ ] 체결 결과 → logs.db 기록
- [ ] 체결 알림 → localhost WS로 프론트엔드 전송 (side 포함)
- [ ] 각 검증 단계에서 거부 시 로그 기록
- [ ] ONCE 트리거 정책: 체결 후 규칙 비활성화 확인

---

### Step 8: ContextCache (AI 컨텍스트 인메모리 캐시)

**목표**: 클라우드 서버에서 주기적으로 fetch한 AI 컨텍스트를 메모리에 캐싱

**파일**: `local_server/engine/context_cache.py`

**구현 내용**:
```python
from datetime import datetime, timedelta
from typing import Optional

class ContextCache:
    """AI 컨텍스트 인메모리 캐시."""

    def __init__(self, ttl_seconds: int = 3600):
        """ttl_seconds: 캐시 유효 시간 (기본 1시간)"""
        self._cache: dict = {}
        self._last_update: Optional[datetime] = None
        self._ttl = timedelta(seconds=ttl_seconds)

    def update(self, context: dict):
        """캐시 갱신."""
        self._cache = context
        self._last_update = datetime.now()

    def get(self) -> dict:
        """캐시 조회."""
        if self._last_update and datetime.now() - self._last_update > self._ttl:
            # TTL 만료 → 최근 데이터 필요 (프론트에서 경고)
            return self._cache  # 하지만 반환 (폴백)
        return self._cache

    def get_field(self, field: str, default=None):
        """특정 필드 조회."""
        return self._cache.get(field, default)

    def is_valid(self) -> bool:
        """캐시 유효 여부."""
        if not self._last_update:
            return False
        return datetime.now() - self._last_update <= self._ttl

    def clear(self):
        """캐시 초기화."""
        self._cache = {}
        self._last_update = None
```

**검증**:
- [ ] 컨텍스트 데이터 저장/조회
- [ ] TTL 기반 유효성 확인
- [ ] 평가 시 컨텍스트 사용 가능

---

### Step 9: BarBuilder (분봉 구성: WS→OHLCV, REST 보충)

**목표**: WS 시세로 1분 OHLCV 구성, 누락 시 REST로 보충

**파일**: `local_server/engine/bar_builder.py`

**구현 내용**:
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

class BarBuilder:
    """WS 시세로 1분 OHLCV 구성."""

    def __init__(self, broker_adapter):
        self._broker = broker_adapter
        self._current_bars: dict[str, dict] = {}  # symbol → bar in construction

    def on_quote(self, symbol: str, price: float, volume: int, timestamp: datetime):
        """WS 시세 수신 시 호출."""
        # 분 경계 확인
        minute_key = timestamp.replace(second=0, microsecond=0)

        if symbol not in self._current_bars:
            self._current_bars[symbol] = {
                "timestamp": minute_key,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": volume,
            }
        else:
            bar = self._current_bars[symbol]
            if bar["timestamp"] == minute_key:
                # 같은 분 → 업데이트
                bar["high"] = max(bar["high"], price)
                bar["low"] = min(bar["low"], price)
                bar["close"] = price
                bar["volume"] += volume
            else:
                # 분 경계 넘음 → 새 분봉 시작
                self._current_bars[symbol] = {
                    "timestamp": minute_key,
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": volume,
                }

    async def get_current_bar(self, symbol: str) -> Optional[Bar]:
        """현재 구성 중인 분봉 조회."""
        if symbol in self._current_bars:
            bar_dict = self._current_bars[symbol]
            return Bar(
                timestamp=bar_dict["timestamp"],
                open=bar_dict["open"],
                high=bar_dict["high"],
                low=bar_dict["low"],
                close=bar_dict["close"],
                volume=bar_dict["volume"],
            )
        return None

    async def get_completed_bar(self, symbol: str) -> Optional[Bar]:
        """완성된 직전 분봉 조회."""
        # 장 시작 직후 (09:00~09:02) → SYNCING 상태, 조회 보류
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        if current_hour == 9 and current_minute < 2:
            return None  # SYNCING 상태

        # 현재 분봉이 아직 완성되지 않았으므로, 이전 분봉 반환
        if symbol in self._current_bars:
            return self._current_bars[symbol]
        return None

    async def sync_missing_bars(self, symbol: str, start_time: datetime, end_time: datetime):
        """누락 분봉 REST로 보충."""
        # BrokerAdapter의 시간대별 분봉 조회 메서드 활용
        bars = await self._broker.get_bars(symbol, start_time, end_time, interval="1m")
        # 반환된 bars를 _current_bars에 병합 (필요시)
        pass
```

**검증**:
- [ ] WS 시세로 1분 OHLCV 구성
- [ ] 분 경계 정확히 인식
- [ ] 장 시작 (09:00~09:02) SYNCING 상태 처리
- [ ] WS 끊김 복구 시 REST 보충

---

### Step 10: StrategyEngine 통합 (evaluate_all 메인 루프)

**목표**: 전체 엔진 통합, evaluate_all 메인 루프 구현

**파일**: `local_server/engine/engine.py` (또는 `__init__.py`)

**구현 내용**:
```python
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class StrategyEngine:
    """전략 엔진 통합."""

    def __init__(self,
                 broker_adapter,
                 logs_db,
                 scheduler: EngineScheduler,
                 evaluator: RuleEvaluator,
                 signal_manager: SignalManager,
                 price_verifier: PriceVerifier,
                 limit_checker: LimitChecker,
                 safeguard: Safeguard,
                 executor: OrderExecutor,
                 context_cache: ContextCache,
                 bar_builder: BarBuilder,
                 rule_cache,  # 규칙 JSON 캐시
                 ws_manager,
                 config: dict):

        self._broker = broker_adapter
        self._logs = logs_db
        self._scheduler = scheduler
        self._evaluator = evaluator
        self._signal_manager = signal_manager
        self._price_verifier = price_verifier
        self._limit_checker = limit_checker
        self._safeguard = safeguard
        self._executor = executor
        self._context_cache = context_cache
        self._bar_builder = bar_builder
        self._rule_cache = rule_cache
        self._ws = ws_manager
        self._config = config
        self._account_no = config.get("account_no")
        self._running = False

    async def start(self):
        """엔진 시작."""
        logger.info("StrategyEngine 시작")
        self._running = True
        await self._scheduler.start()

    async def stop(self):
        """엔진 중지."""
        logger.info("StrategyEngine 중지")
        self._running = False
        await self._scheduler.stop()

    async def evaluate_all(self):
        """
        1분마다 호출되는 메인 루프.

        [0] Kill Switch 체크
        [0.5] 분봉 유효성 확인
        [1] 규칙 로드 (priority 내림차순 정렬)
        [2] 각 규칙 매수/매도 분리 평가
        [3] 안전장치 체크
        [4] 가격 검증
        [5] 주문 실행
        """
        if not self._running:
            return

        try:
            # [0] Kill Switch 체크
            trading_enabled = await self._safeguard.check_trading_enabled()
            logger.debug(f"Trading Enabled: {trading_enabled}")

            if not trading_enabled:
                logger.info("평가 실행 (주문 스킵): Trading Enabled = OFF")

            # [0.5] 분봉 유효성 확인
            # 장 시작 직후 (09:00~09:02) → SYNCING 상태, 평가 보류
            now = datetime.now()
            if now.hour == 9 and now.minute < 2:
                logger.debug("SYNCING 상태 — 평가 보류")
                return

            # WS 끊김 복구 시 누락 분봉 보충 (필요시)
            # TODO: WS 상태 확인 로직 추가

            # [1] 규칙 로드 — priority 내림차순 정렬 (높은 순위 먼저 주문)
            rules = self._rule_cache.load()
            if not rules:
                logger.warning("캐시된 규칙 없음 — 평가 보류")
                return

            active_rules = [r for r in rules if r.get("is_active", False)]
            active_rules.sort(key=lambda r: r.get("priority", 0), reverse=True)
            logger.debug(f"활성 규칙: {len(active_rules)}개")

            # 계좌 상태 조회 (BrokerAdapter ABC: get_balance + get_positions)
            balance = await self._broker.get_balance(self._account_no)
            positions = await self._broker.get_positions(self._account_no)
            account_state = {
                "balance": balance.total_balance,
                "positions": positions,
            }

            # [2] 각 규칙 매수/매도 분리 평가
            for rule in active_rules:
                try:
                    rule_id = rule.get("id")
                    symbol = rule.get("symbol")

                    # 시세 데이터: WS listen() 캐시(BarBuilder)에서 조회
                    market_data = self._bar_builder.get_latest(symbol)
                    if not market_data:
                        logger.warning(f"Rule {rule_id} ({symbol}): 시세 데이터 미수신")
                        continue

                    # AI 컨텍스트
                    context = self._context_cache.get()

                    # 매수 평가: buy_conditions 존재 + 미보유 → evaluate_buy
                    if rule.get("buy_conditions") and not self._executor.is_holding(symbol):
                        buy_met = self._evaluator.evaluate_buy(rule, market_data, context)
                        if buy_met:
                            logger.info(f"Rule {rule_id} ({symbol}): 매수 조건 충족 → 매수 주문")
                            result = await self._executor.execute(
                                rule, "BUY", market_data, account_state
                            )
                            logger.info(f"Rule {rule_id} BUY: {result.status.value}, {result.message}")

                    # 매도 평가: sell_conditions 존재 + 보유 중 → evaluate_sell
                    if rule.get("sell_conditions") and self._executor.is_holding(symbol):
                        sell_met = self._evaluator.evaluate_sell(rule, market_data, context)
                        if sell_met:
                            logger.info(f"Rule {rule_id} ({symbol}): 매도 조건 충족 → 매도 주문")
                            result = await self._executor.execute(
                                rule, "SELL", market_data, account_state
                            )
                            logger.info(f"Rule {rule_id} SELL: {result.status.value}, {result.message}")

                    # 조건 미충족 시 디버그 로그
                    if not rule.get("buy_conditions") and not rule.get("sell_conditions"):
                        logger.debug(f"Rule {rule_id} ({symbol}): 매수/매도 조건 미정의")

                except Exception as e:
                    logger.error(f"Rule {rule.get('id')} 평가 오류: {str(e)}")
                    await self._logs.record_error_log(rule.get("id"), str(e))
                    # 해당 규칙만 비활성화 (선택사항)

        except Exception as e:
            logger.error(f"evaluate_all 오류: {str(e)}")
            await self._logs.record_error_log(-1, f"evaluate_all: {str(e)}")
```

**검증**:
- [ ] 1분마다 정확히 호출
- [ ] 규칙 평가 → 조건 충족 → 주문 실행 흐름 동작
- [ ] 각 단계의 검증 기준 만족
- [ ] 오류 발생 시 로그 기록 + 해당 규칙만 비활성화
- [ ] WS 끊김 시 복구 로직 동작

---

## 2. 파일 목록 및 의존성

| 파일 | 의존성 | 설명 |
|------|--------|------|
| `local_server/engine/__init__.py` | — | 패키지 초기화 |
| `local_server/engine/scheduler.py` | APScheduler | 1분 주기 스케줄러 |
| `local_server/engine/evaluator.py` | — | 조건 평가 로직 |
| `local_server/engine/signal_manager.py` | — | 신호 상태 관리 |
| `local_server/engine/price_verifier.py` | BrokerAdapter | 가격 검증 |
| `local_server/engine/limit_checker.py` | logs.db | 한도 체크 |
| `local_server/engine/safeguard.py` | logs.db, BrokerAdapter | 안전장치 |
| `local_server/engine/executor.py` | 모든 모듈 | 주문 실행 파이프라인 |
| `local_server/engine/context_cache.py` | — | AI 컨텍스트 캐시 |
| `local_server/engine/bar_builder.py` | BrokerAdapter | 분봉 구성 |
| `local_server/engine/engine.py` | 모든 모듈 | 통합 엔진 |

---

## 3. 의존성 및 블로킹 이슈

### 블로킹 (구현 불가)
1. **Unit 1 (BrokerAdapter)**: 아직 미구현
   - `get_current_price()`, `send_order()`, `cancel_order()`
   - `get_balance()`, `get_positions()`
   - `subscribe()`, `listen()` (WS 시세 스트림)
   - 상태: 필수 (mock 개발 시작 가능)

2. **Unit 2 (로컬 서버 코어)**: 아직 미구현
   - FastAPI 라우터, logs.db 스키마
   - JWT 토큰 관리, Credential Manager 통합
   - WS 브로드캐스트
   - 상태: 필수 (mock 개발 시작 가능)

3. **규칙 캐시**: 프론트엔드에서 sync 또는 WS push
   - 로컬에 strategies.json 저장 후 로드
   - 상태: 선택사항 (mock JSON 파일로 개발 가능)

### 논블로킹 (BrokerAdapter mock으로 개발 가능)
- EngineScheduler (APScheduler 자체 라이브러리)
- RuleEvaluator (순수 로직)
- SignalManager (순수 상태 관리)
- ContextCache (순수 캐시)

---

## 4. 커밋 계획

| 커밋 | 단계 | 메시지 |
|------|------|--------|
| 1 | Step 1-3 | `feat: Unit 3 Step 1-3 — EngineScheduler, RuleEvaluator, SignalManager` |
| 2 | Step 4-6 | `feat: Unit 3 Step 4-6 — PriceVerifier, LimitChecker, Safeguard` |
| 3 | Step 7-10 | `feat: Unit 3 Step 7-10 — OrderExecutor, ContextCache, BarBuilder, StrategyEngine 통합` |
| 4 (선택) | 통합 테스트 | `test: Unit 3 통합 테스트 (mock BrokerAdapter)` |

---

## 5. 테스트 전략

### Step별 단위 테스트
- EngineScheduler: APScheduler cron 정상 동작
- RuleEvaluator: AND/OR 조건, 비교 연산자
- SignalManager: 중복 방지, 일일 리셋
- PriceVerifier: 괴리 판정, 조회 실패
- LimitChecker: 예산/포지션 체크
- Safeguard: Kill Switch, 손실 락, 주문 속도
- OrderExecutor: 파이프라인 각 단계
- ContextCache: 캐시 갱신/조회
- BarBuilder: OHLCV 구성, 분 경계

### 통합 테스트 (mock BrokerAdapter)
```python
# local_server/tests/test_engine_integration.py

class MockBrokerAdapter:
    async def get_current_price(self, symbol): return 50000
    async def send_order(self, **kwargs): return OrderResult(order_id="ORDER123")
    async def cancel_order(self, order_no): return OrderResult(success=True, order_no=order_no)
    async def get_balance(self, account_no): return BalanceResult(
        total_balance=10_000_000, available=10_000_000, positions=[]
    )
    async def get_positions(self, account_no): return []
    async def subscribe(self, symbols, data_type): pass
    async def unsubscribe(self, symbols, data_type): pass
    async def listen(self):
        while True:
            yield QuoteEvent(symbol="005930", price=50000, volume=100)

class TestStrategyEngine:
    async def test_evaluate_all_success(self):
        """정상 흐름: 조건 충족 → 주문 성공"""
        # mock 규칙, 계정 설정
        # evaluate_all() 호출
        # 결과 검증: 주문 체결, logs.db 기록, WS 알림
        pass

    async def test_evaluate_all_price_mismatch(self):
        """가격 불일치 시 주문 거부"""
        # mock에서 실시간 50000, REST 51000 반환
        # 평가 후 주문 거부 확인
        pass

    async def test_evaluate_all_duplicate_prevention(self):
        """같은 규칙 하루에 2회 차단"""
        # 첫 실행: 성공
        # 두 번째 실행: 거부
        pass
```

---

## 6. 미결 사항 처리

### (해결) 규칙 데이터 모델 분리
- [x] 규칙 데이터 모델 분리 → `spec/rule-model/spec.md`로 분리 완료
- 매수/매도 조건 분리, 조건 타입 확장(cross_above/cross_below), 트리거 정책(ONCE_PER_DAY/ONCE) 포함

### (미결) 가격 검증 괴리 임계값
- 현재: 1%
- 검토: 0.5% (더 엄격) vs 2% (더 관대)
- **결정**: 1% 유지 (일반적 기준)

### (미결) 규칙 평가 시 실시간 시세 우선순위
- WS 시세 vs REST 시세
- **결정**: WS 시세 우선, REST는 검증용 (가격 검증에서만 사용)

### (미결) custom_formula 조건 타입
- eval() 사용 시 보안 위험
- **현재**: 미포함 (v1)
- **v2+**: 안전한 수식 파서 (sympy, numexpr 등)

### (미결) 장 시작 직후 SYNCING 구간
- 09:00~09:02 설정
- **검토**: 데이터 안정성 확인 후 조정 필요

### (미결) 최대 손실 제한 임계값
- 기본값: 5%
- **결정**: 사용자 설정 가능 (기본 5%)

### (미결) 주문 속도 제한 기본값
- 기본값: 10건/분
- **결정**: 사용자 설정 가능 (기본 10건/분)

---

## 7. 다음 단계

1. **Unit 1 (BrokerAdapter)** 구현 시작 (병렬 진행 가능)
   - spec: `spec/kiwoom-integration/spec.md`
   - plan: `spec/kiwoom-integration/plan.md`

2. **Unit 2 (로컬 서버 코어)** 구현 (Unit 1 후)
   - FastAPI 라우터, logs.db 스키마
   - JWT 통합

3. **Unit 3 (본 plan)** 구현
   - Step 1-3: 스케줄러, 평가, 신호 관리
   - Step 4-6: 검증, 한도, 안전장치
   - Step 7-10: 실행, 캐시, 분봉, 통합

4. **통합 테스트 + mock 개발**
   - BrokerAdapter mock으로 엔진 검증
   - 실제 키움 연동 전 동작 확인

---

## 참고

- 기술 스택: Python 3.13, FastAPI, APScheduler, SQLAlchemy
- 아키텍처 문서: `docs/architecture.md`
- 개발 계획: `docs/development-plan-v2.md`
- spec: `spec/strategy-engine/spec.md`
- 기존 데이터 소스 계획: `spec/data-source/plan.md`

---

**마지막 갱신**: 2026-03-05
