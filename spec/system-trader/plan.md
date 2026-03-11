# System Trader Phase 1 구현 계획

> 작성일: 2026-03-11 | 상태: 초안 | spec: spec/system-trader/spec.md

---

## 범위

### Phase 1에서 구현할 것

- `CandidateSignal` 데이터 모델 추가 (`local_server/engine/trader_models.py`)
- `TradeDecisionBatch`, `BlockReason` 추가 (같은 파일)
- `SystemTrader.process_cycle` — 후보 수집 → 선택/차단 결정 (새 파일)
- `StrategyEngine.evaluate_all` 수정 — 즉시 주문 대신 candidate 수집 후 `process_cycle` 경유
- 차단 정책 3가지: 동일 종목 중복(`DUPLICATE_SYMBOL`), 최대 포지션 초과(`MAX_POSITIONS`), 일일 예산 초과(`DAILY_BUDGET_EXCEEDED`)
- 선택된 candidate만 기존 `executor.execute`로 넘기는 구조 유지

### Phase 1에서 하지 않을 것

- `OrderIntent` 모델 (Phase 2)
- `executor` 입력 변경 — rule dict 그대로 유지 (Phase 2)
- `SUBMITTED`/`FILLED` 분리 (Phase 2)
- `IntentStore`, inflight intent 저장소 (Phase 2)
- open order reconciliation (Phase 3)
- `REDUCING` 모드 (Phase 3)
- `ArmSession` 상태 전이 (Phase 3)
- 브로커 이벤트 훅 (`on_order_submitted`, `on_order_event`) (Phase 2~3)

---

## Step 1: trader_models.py — CandidateSignal 등 데이터 모델 추가

**파일**: `local_server/engine/trader_models.py` (신규)

**변경**: 아래 클래스를 새 파일에 정의

```python
# CandidateSignal
@dataclass
class CandidateSignal:
    signal_id: str        # uuid4 hex[:8]
    cycle_id: str
    rule_id: int
    symbol: str
    side: Literal["BUY", "SELL"]
    priority: int
    desired_qty: int
    detected_at: datetime
    latest_price: Decimal
    reason: str
    raw_rule: dict[str, Any]

# BlockReason
class BlockReason(str, Enum):
    DUPLICATE_SYMBOL = "DUPLICATE_SYMBOL"
    MAX_POSITIONS = "MAX_POSITIONS"
    DAILY_BUDGET_EXCEEDED = "DAILY_BUDGET_EXCEEDED"
    SELL_NO_HOLDING = "SELL_NO_HOLDING"
    UNKNOWN = "UNKNOWN"

# TradeDecisionBatch
@dataclass
class TradeDecisionBatch:
    cycle_id: str
    selected: list[CandidateSignal]
    dropped: list[tuple[CandidateSignal, BlockReason]]
```

`raw_rule`에는 해당 규칙 dict 전체를 담아 executor가 기존 인터페이스로 받을 수 있게 한다.

`desired_qty`는 `rule["execution"].get("qty_value", rule.get("qty", 1))`에서 추출한다.

---

## Step 2: system_trader.py — SystemTrader.process_cycle

**파일**: `local_server/engine/system_trader.py` (신규)

**변경**: `SystemTrader` 클래스 구현

### 인터페이스

```python
class SystemTrader:
    def __init__(
        self,
        max_positions: int,
        budget_ratio: Decimal,
    ) -> None: ...

    def process_cycle(
        self,
        *,
        cycle_id: str,
        candidates: list[CandidateSignal],
        current_positions: list,       # BalanceResult.positions
        cash: Decimal,
        today_executed: Decimal,
    ) -> TradeDecisionBatch: ...
```

### process_cycle 알고리즘

```
1. 입력 candidates를 priority 내림차순 정렬 (동점이면 detected_at 빠른 순)
2. 이 주기 내 이미 선택된 종목 추적용 set: selected_symbols = set()
3. 현재 포지션 종목: holding_symbols = {p.symbol for p in current_positions}
4. 현재 포지션 수: position_count = len(current_positions)

for candidate in sorted_candidates:
    side = candidate.side

    if side == "BUY":
        # 동일 종목 중복 방지
        if candidate.symbol in selected_symbols:
            drop(DUPLICATE_SYMBOL); continue
        # 동일 종목 이미 보유 (이 주기 이전)
        if candidate.symbol in holding_symbols:
            drop(DUPLICATE_SYMBOL); continue
        # 포지션 슬롯 확인
        if position_count >= max_positions:
            drop(MAX_POSITIONS); continue
        # 예산 확인
        order_amount = candidate.latest_price * candidate.desired_qty
        account_total = cash + sum(position 평가액)  # Phase 1: cash만 사용
        max_daily = account_total * budget_ratio
        if today_executed + 이번_주기_누적 + order_amount > max_daily:
            drop(DAILY_BUDGET_EXCEEDED); continue
        # 선택
        selected_symbols.add(candidate.symbol)
        position_count += 1
        이번_주기_누적 += order_amount
        select(candidate)

    if side == "SELL":
        # 미보유 종목 매도 차단
        if candidate.symbol not in holding_symbols:
            drop(SELL_NO_HOLDING); continue
        # SELL은 포지션/예산 제한 없음
        select(candidate)

5. return TradeDecisionBatch(cycle_id, selected, dropped)
```

**설계 노트**:
- Phase 1에서 `daily_budget_used`는 `LimitChecker._today_executed`를 외부에서 받는 방식 대신 `SystemTrader`가 `LimitChecker` 인스턴스를 직접 참조하지 않는다.
  대신 `StrategyEngine`이 `self._limit_checker.today_executed`를 `today_executed` 파라미터로 넘기고, 선택 후 `self._limit_checker.record_execution()`을 호출한다.
  (책임 분리 유지, Phase 2에서 `PortfolioSnapshot`으로 통합)
- 예산 계산에서 account_total은 Phase 1에서는 `cash`만 사용 (position 평가액 합산은 Phase 2에서 `PortfolioSnapshot.positions` 도입 시 추가)

---

## Step 3: StrategyEngine.evaluate_all 수정

**파일**: `local_server/engine/engine.py`

### 변경 전 흐름

```
for rule in active_rules:
    await self._evaluate_rule(rule, balance, holding_symbols, trading_enabled)
    # _evaluate_rule 내부에서 즉시 executor.execute() 호출
```

### 변경 후 흐름

```
# 1. 잔고 조회 (기존과 동일)
balance = await self._broker.get_balance()
holding_symbols = {p.symbol for p in balance.positions}

# 1.5. trading_enabled=false이면 수집 건너뜀
if not trading_enabled:
    logger.debug("거래 불가 — 수집 생략")
    return

# 2. 모든 규칙 평가 → candidates 수집 (tuple: candidate + market_data)
cycle_id = uuid4().hex[:12]
collected: list[tuple[CandidateSignal, dict]] = []
for rule in active_rules:
    pair = await self._collect_candidate(rule, balance, holding_symbols)
    if pair:
        collected.append(pair)

candidates = [c for c, _ in collected]
market_data_map = {c.signal_id: md for c, md in collected}

# 3. SystemTrader.process_cycle → 선택/차단 결정
batch = self._system_trader.process_cycle(
    cycle_id=cycle_id,
    candidates=candidates,
    current_positions=balance.positions,
    cash=balance.cash,
    today_executed=self._limit_checker.today_executed,
)

# 4. 선택된 candidates만 executor 호출
for candidate in batch.selected:
    md = market_data_map[candidate.signal_id]
    result = await self._executor.execute(
        candidate.raw_rule, candidate.side, md, balance
    )
    ...

# 5. 차단 로그
for candidate, reason in batch.dropped:
    logger.info("Rule %d (%s) 차단: %s", candidate.rule_id, candidate.symbol, reason)
```

### 신규 메서드: `_collect_candidate`

기존 `_evaluate_rule`에서 executor 호출 부분을 제거하고 `CandidateSignal` 반환으로 변경.

```python
async def _collect_candidate(
    self,
    rule: dict,
    balance: BalanceResult,
    holding_symbols: set[str],
) -> tuple[CandidateSignal, dict] | None:
    """규칙 평가 → CandidateSignal 생성. 조건 미충족이면 None."""
    rule_id = rule.get("id", 0)
    symbol = rule.get("symbol", "")

    latest = self._bar_builder.get_latest(symbol)
    if not latest:
        return None
    latest["indicators"] = self._indicator_provider.get(symbol)
    context = self._context_cache.get()

    buy_result, sell_result = self._evaluator.evaluate(rule, latest, context)

    side: str | None = None
    if buy_result and symbol not in holding_symbols:
        side = "BUY"
    elif sell_result and symbol in holding_symbols:
        side = "SELL"

    if not side:
        return None

    execution = rule.get("execution") or {}
    qty = int(execution.get("qty_value", rule.get("qty", 1)))
    price = Decimal(str(latest.get("price", 0)))

    return (CandidateSignal(
        signal_id=uuid4().hex[:8],
        cycle_id="",  # evaluate_all에서 채움
        rule_id=rule_id,
        symbol=symbol,
        side=side,
        priority=int(rule.get("priority", 0)),
        desired_qty=qty,
        detected_at=datetime.now(),
        latest_price=price,
        reason="조건 충족",
        raw_rule=rule,
    ), latest)
```

**중요**: `_evaluate_rule` 메서드는 삭제하고 `_collect_candidate`로 교체한다. 반환 타입은 `tuple[CandidateSignal, dict] | None`으로, market_data를 함께 돌려줘 executor 호출 시 사용한다.

### StrategyEngine.__init__ 변경

`SystemTrader` 인스턴스를 `self._system_trader`로 추가:

```python
from local_server.engine.system_trader import SystemTrader

self._system_trader = SystemTrader(
    max_positions=int(cfg.get("max_positions", 5)),
    budget_ratio=Decimal(str(cfg.get("budget_ratio", "0.1"))),
)
```

### LimitChecker 변경 (소규모)

`today_executed` 프로퍼티를 외부에서 읽을 수 있도록 추가:

**파일**: `local_server/engine/limit_checker.py`

```python
@property
def today_executed(self) -> Decimal:
    return self._today_executed
```

---

## Step 4: 기존 executor 연결 확인

**파일**: `local_server/engine/executor.py`

**변경 없음**. Phase 1에서는 `executor.execute(rule, side, market_data, balance)` 시그니처를 그대로 유지한다.

`candidate.raw_rule`에 원본 rule dict가 있으므로 그대로 전달 가능.

`market_data`는 `_collect_candidate`에서 읽은 `latest`를 executor 호출 시 함께 전달해야 한다. `CandidateSignal`에 `latest_price`만 있으므로, `StrategyEngine`이 선택된 candidate에 대해 `self._bar_builder.get_latest(candidate.symbol)`을 다시 호출하거나, `_collect_candidate`에서 `market_data`를 함께 반환하도록 반환 타입을 `tuple[CandidateSignal, dict] | None`으로 조정한다.

**결정**: `_collect_candidate`를 `tuple[CandidateSignal, dict] | None` 반환으로 설계한다. `evaluate_all`은 `(candidate, market_data)` 쌍을 수집하고, executor 호출 시 저장한 `market_data`를 사용한다.

---

## Step 5: 로깅

**파일**: `local_server/engine/engine.py`

평가 주기마다 아래 형태로 로그 출력:

```
[Cycle abc123] 후보 5개 → 선택 2개, 차단 3개
[Cycle abc123] 선택: Rule 3 (005930) BUY
[Cycle abc123] 선택: Rule 7 (000660) SELL
[Cycle abc123] 차단: Rule 5 (005930) BUY — DUPLICATE_SYMBOL
[Cycle abc123] 차단: Rule 9 (035720) BUY — MAX_POSITIONS
[Cycle abc123] 차단: Rule 11 (035420) BUY — DAILY_BUDGET_EXCEEDED
```

`logger.info`로 출력. `batch.dropped`에 `(CandidateSignal, BlockReason)` 쌍이 있으므로 순회하여 출력한다.

---

## 파일 변경 요약

| 파일 | 상태 | 내용 |
|------|------|------|
| `local_server/engine/trader_models.py` | 신규 | CandidateSignal, BlockReason, TradeDecisionBatch |
| `local_server/engine/system_trader.py` | 신규 | SystemTrader.process_cycle |
| `local_server/engine/engine.py` | 수정 | evaluate_all 재작성, _evaluate_rule → _collect_candidate, SystemTrader 주입 |
| `local_server/engine/limit_checker.py` | 수정 | today_executed 프로퍼티 추가 |
| `local_server/engine/executor.py` | 변경 없음 | Phase 1에서 시그니처 유지 |

---

## 검증

### 단위 검증 (수동)

1. `SystemTrader.process_cycle` 독립 테스트
   - 동일 종목 2개 BUY candidate 입력 → 첫 번째 선택, 두 번째 `DUPLICATE_SYMBOL` 차단 확인
   - `max_positions=2`, 현재 포지션 2개 → 모든 BUY candidate `MAX_POSITIONS` 차단 확인
   - 예산 초과 candidate → `DAILY_BUDGET_EXCEEDED` 차단 확인
   - 미보유 종목 SELL candidate → `SELL_NO_HOLDING` 차단 확인
   - priority 높은 candidate가 먼저 처리되어 슬롯을 차지하는지 확인

2. `StrategyEngine.evaluate_all` 흐름 확인 (로그)
   - 엔진 실행 후 로그에서 `[Cycle ...]` 라인 확인
   - 조건 미충족 시 candidate 없이 주기 완료 (오류 없음) 확인

### 기존 동작 회귀 확인

- executor.execute 시그니처 변경 없음 → 기존 단위 테스트 통과 유지
- safeguard, signal_manager는 executor 내부에서 기존과 동일하게 동작
- 선택된 candidate는 결국 기존 executor 경로를 타므로 주문 실행 결과는 동일
