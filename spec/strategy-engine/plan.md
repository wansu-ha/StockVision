# 전략 엔진 구현 계획서 (strategy-engine)

> 작성일: 2026-03-05 | 갱신: 2026-03-07 | 상태: v2 | Unit 3 (Phase 3-A) | 위치: `local_server/engine/`
>
> **v1→v2 변경**: rule-model spec v2(DSL 기반) 반영. 모델/평가기는 rule-model plan에 위임, 본 plan은 엔진 인프라에 집중.

---

## 0. 현황 및 의존성

### 의존 Unit 상태

| Unit | 상태 | 산출 |
|------|------|------|
| Unit 1 (kiwoom-rest) | **완료** | `sv_core/broker/` — BrokerAdapter ABC + KiwoomAdapter |
| Unit 2 (local-server-core) | **완료** | `local_server/` — FastAPI, logs.db, WS, JWT, 트레이 |

> 블로킹 없음. 모든 의존 모듈이 구현되어 있으므로 바로 착수 가능.

### 기존 코드 상태

`local_server/engine/` 에 v1 코드가 존재:
- `models.py`: RuleConfig (side, operator, conditions — v1 JSON 기반)
- `evaluator.py`: `evaluate(rule, ...) -> bool` (단일 방향)
- `executor.py`: `execute(rule, ...) -> ExecutionResult` (side를 rule dict에서 읽음)
- `engine.py`: StrategyEngine (`evaluate_all` 메인 루프)
- `signal_manager.py`: `can_trigger(rule_id)` (매수/매도 미분리)
- 나머지: scheduler, safeguard, price_verifier, limit_checker, context_cache, bar_builder

### 참고 문서

- `spec/strategy-engine/spec.md` — 엔진 요구사항 (F1~F17)
- `spec/rule-model/spec.md` — DSL 규칙 모델 (v2)
- `spec/rule-model/grammar.md` — DSL 정형 문법 (EBNF)
- `spec/rule-model/plan.md` — DSL 파서 + 모델/평가기/실행기 구현 계획
- `sv_core/broker/base.py` — BrokerAdapter ABC 정본

### 역할 분담

| 영역 | 담당 plan | 파일 |
|------|----------|------|
| DSL 파서 (Lexer, Parser, Evaluator) | rule-model plan Step 1~4 | `sv_core/parsing/` |
| 클라우드 모델/API 갱신 | rule-model plan Step 5~6 | `cloud_server/` |
| RuleConfig 재구조 + 평가기 DSL 통합 | rule-model plan Step 7 | `local_server/engine/models.py`, `evaluator.py` |
| 실행기 인터페이스 변경 (side 파라미터, 매도 보호) | rule-model plan Step 8 | `local_server/engine/executor.py` |
| **엔진 인프라** (스케줄러, 신호, 안전장치 등) | **본 plan** | `local_server/engine/` 나머지 |

---

## 1. 구현 단계 (8 Steps)

### Step 1: SignalManager — 매수/매도 분리 + 트리거 정책

**목표**: 기존 단일 상태 → 매수/매도 독립 상태. trigger_policy(ONCE, ONCE_PER_DAY) 지원.

**파일**: `local_server/engine/signal_manager.py`

**변경 요약**:
- `can_trigger(rule_id)` → `can_trigger(rule_id, side)` (매수/매도 구분)
- `mark_triggered(rule_id)` → `mark_triggered(rule_id, side)`
- `mark_filled(rule_id)` → `mark_filled(rule_id, side, trigger_policy)`
- `mark_failed(rule_id)` → `mark_failed(rule_id, side)`
- `_states: dict[int, str]` → `_buy_states`, `_sell_states` 분리
- ONCE 정책: 체결 시 `rules_cache.deactivate(rule_id)` 호출

**검증**:
- [ ] 같은 규칙 매수/매도 각각 하루 1회 (ONCE_PER_DAY)
- [ ] 매수 실행 후에도 매도 독립 실행 가능
- [ ] 자정 리셋 → 다음날 재실행 가능
- [ ] ONCE 정책: 1회 체결 → 규칙 비활성화

---

### Step 2: PriceVerifier — BrokerAdapter ABC 정합

**목표**: 기존 코드 유지, ABC 메서드명 일치 확인

**파일**: `local_server/engine/price_verifier.py`

**확인 사항**:
기존 코드가 이미 `self._broker.get_quote(symbol)` 사용 중 → **변경 불필요**.
plan 문서의 `get_current_price()` 참조만 오류였으며, 코드는 정확함.

**검증**:
- [ ] `get_quote(symbol) -> QuoteEvent` 호출 확인
- [ ] 괴리 < 1% → OK, > 1% → 거부
- [ ] 조회 실패 → 보수적 거부

---

### Step 3: LimitChecker — 변경 없음 (확인만)

**파일**: `local_server/engine/limit_checker.py`

기존 코드 유지. `check_budget()`, `check_max_positions()` 인터페이스 변경 없음.

> `max_position_count`, `budget_ratio`는 rule-model spec §8에 따라
> 사용자 전역 설정(`config.json`)에서 읽음. 기존 LimitChecker의 config 주입 방식과 일치.

**검증**:
- [ ] 일일 예산 초과 → 스킵
- [ ] 최대 포지션 수 초과 → 스킵

---

### Step 4: Safeguard — BrokerAdapter ABC 정합

**목표**: 기존 코드의 BrokerAdapter 호출이 ABC와 일치하는지 확인, 필요시 수정.

**파일**: `local_server/engine/safeguard.py`

**확인/수정 사항**:
- Kill Switch CANCEL_OPEN 시 미체결 취소:
  ```python
  # 정본 ABC 기준
  for order in await self._broker.get_open_orders():
      await self._broker.cancel_order(order.order_id)
  ```
  - ~~`get_positions(account_no)`~~ → `get_open_orders()` (ABC 메서드)
  - ~~`get_balance(account_no)`~~ → `get_balance()` (파라미터 없음)
- `check_max_loss(today_realized_pnl, account_balance)` — 기존 시그니처 유지
  (호출자가 `balance.cash + balance.total_eval`로 계산하여 전달)

**검증**:
- [ ] Kill Switch STOP_NEW → Trading Enabled = OFF
- [ ] Kill Switch CANCEL_OPEN → `get_open_orders()` + `cancel_order()` 호출
- [ ] 최대 손실 발동 → loss_lock = true
- [ ] 분당 주문 한도 초과 → 차단
- [ ] 락 해제는 수동만

---

### Step 5: ContextCache — 변경 없음 (확인만)

**파일**: `local_server/engine/context_cache.py`

기존 코드 유지. `update()`, `get()`, `is_valid()` 인터페이스 변경 없음.

DSL 평가기가 context dict를 받아 내장 필드(`현재가`, `거래량` 등)를 resolve할 때,
ContextCache의 `get()` 반환값이 그대로 전달됨.

**검증**:
- [ ] TTL 기반 유효성 확인
- [ ] 평가 시 컨텍스트 사용 가능

---

### Step 6: BarBuilder — 변경 없음 (확인만)

**파일**: `local_server/engine/bar_builder.py`

기존 코드 유지. `on_quote()`, `get_latest()` 인터페이스 변경 없음.

DSL 평가기의 `상향돌파(A, B)` / `하향돌파(A, B)` 함수는 이전 평가 값을 `state` dict로 관리하며,
BarBuilder의 분봉 데이터와는 독립적. (rule-model spec §7.4 런타임 규칙 참조)

**검증**:
- [ ] WS 시세 → 1분 OHLCV 구성
- [ ] 분 경계 정확 인식
- [ ] 장 시작 (09:00~09:02) SYNCING 상태

---

### Step 7: EngineScheduler — 변경 없음 (확인만)

**파일**: `local_server/engine/scheduler.py`

기존 코드 유지. `start()`, `stop()` 인터페이스 변경 없음.
`evaluate_all()`을 1분 주기 cron으로 호출하는 역할만 담당.

**검증**:
- [ ] 월~금 09:00~15:30에만 실행
- [ ] 장외 시간 실행 안 됨

---

### Step 8: StrategyEngine 통합 — evaluate_all 재작성

**목표**: DSL 기반 양방향 평가 + 기존 인프라 모듈 연결

**파일**: `local_server/engine/engine.py`

**변경 요약**:

| 항목 | v1 (현재) | v2 (변경) |
|------|----------|----------|
| evaluator 호출 | `evaluate(rule, ...) -> bool` | `evaluate(rule, ...) -> tuple[bool, bool]` |
| side 결정 | rule dict에서 `side` 필드 읽음 | evaluator가 (buy, sell) 반환 |
| executor 호출 | `execute(rule, market_data, ...)` | `execute(rule, side, market_data, ...)` |
| 잔고 조회 | `get_balance(account_no)` | `get_balance()` (파라미터 없음) |
| 포지션 조회 | `get_positions(account_no)` | `balance.positions` (BalanceResult 내장) |
| 보유 판단 | executor `_holdings` 메모리 | `balance.positions`에서 symbol 조회 |

**evaluate_all 핵심 흐름**:
```python
async def evaluate_all(self):
    # [0] Kill Switch 체크
    trading_enabled = self._safeguard.is_trading_enabled()

    # [0.5] SYNCING 체크 (09:00~09:02)
    if _is_syncing():
        return

    # [1] 규칙 로드 (priority 내림차순)
    rules = self._rule_cache.get_rules()
    active_rules = sorted(
        [r for r in rules if r.get("is_active")],
        key=lambda r: r.get("priority", 0),
        reverse=True,
    )

    # [1.5] 잔고 조회
    balance = await self._broker.get_balance()
    holding_symbols = {p.symbol for p in balance.positions}

    # [2] 각 규칙 평가
    for rule in active_rules:
        symbol = rule.get("symbol")
        market_data = self._bar_builder.get_latest(symbol)
        if not market_data:
            continue

        context = self._context_cache.get()

        # evaluator: DSL이면 DSL 경로, 아니면 JSON 경로 (rule-model plan Step 7)
        buy_result, sell_result = self._evaluator.evaluate(rule, market_data, context)

        # 매수: 조건 충족 + 미보유
        if buy_result and symbol not in holding_symbols and trading_enabled:
            result = await self._executor.execute(rule, "BUY", market_data, balance)

        # 매도: 조건 충족 + 보유 중
        if sell_result and symbol in holding_symbols and trading_enabled:
            result = await self._executor.execute(rule, "SELL", market_data, balance)
```

**검증**:
- [ ] DSL 규칙: 매수/매도 동시 평가 → 각각 독립 실행
- [ ] JSON 규칙 (하위 호환): 기존 동작 유지
- [ ] priority 내림차순 정렬 확인
- [ ] Kill Switch OFF → 평가만 실행 (주문 스킵)
- [ ] SYNCING 상태 → 평가 보류
- [ ] 규칙 평가 오류 → 해당 규칙만 스킵 + 로그
- [ ] 잔고 조회: `get_balance()` (파라미터 없음)
- [ ] 보유 판단: `balance.positions` 기반

---

## 2. 파일 목록 및 변경 수준

| 파일 | 변경 수준 | 담당 |
|------|----------|------|
| `signal_manager.py` | **수정** (매수/매도 분리) | 본 plan Step 1 |
| `safeguard.py` | **수정** (ABC 메서드명 정합) | 본 plan Step 4 |
| `engine.py` | **재작성** (evaluate_all) | 본 plan Step 8 |
| `price_verifier.py` | 확인만 | 본 plan Step 2 |
| `limit_checker.py` | 확인만 | 본 plan Step 3 |
| `context_cache.py` | 확인만 | 본 plan Step 5 |
| `bar_builder.py` | 확인만 | 본 plan Step 6 |
| `scheduler.py` | 확인만 | 본 plan Step 7 |
| `models.py` | **재구조** | rule-model plan Step 7 |
| `evaluator.py` | **재작성** (DSL 통합) | rule-model plan Step 7 |
| `executor.py` | **수정** (side 파라미터, 매도 보호) | rule-model plan Step 8 |

---

## 3. BrokerAdapter ABC 정본 참조

> `sv_core/broker/base.py` 기준. plan 내 코드 예시는 이 시그니처를 따른다.

| 메서드 | 시그니처 | 반환 |
|--------|---------|------|
| `get_balance()` | 파라미터 없음 | `BalanceResult(cash, total_eval, positions)` |
| `get_quote(symbol)` | `str` | `QuoteEvent(symbol, price, volume, ...)` |
| `place_order(...)` | `client_order_id, symbol, side, order_type, qty, limit_price` | `OrderResult` |
| `cancel_order(order_id)` | `str` | `OrderResult` |
| `get_open_orders()` | 파라미터 없음 | `list[OrderResult]` |
| `subscribe_quotes(symbols, callback)` | `list[str], Callable` | `None` |
| `unsubscribe_quotes(symbols)` | `list[str]` | `None` |

---

## 4. 커밋 계획

| 커밋 | 단계 | 메시지 |
|------|------|--------|
| 1 | rule-model Step 1~4 | `feat: DSL 파서 — Lexer, Parser, Evaluator (sv_core/parsing)` |
| 2 | rule-model Step 5~6 | `feat: 클라우드 규칙 모델/API DSL 통합` |
| 3 | rule-model Step 7~8 + 본 plan Step 1~8 | `feat: 전략 엔진 v2 — DSL 평가 + 엔진 인프라 갱신` |
| 4 | rule-model Step 9~10 | `feat: 프론트엔드 타입/폼 DSL 변환` |
| 5 | rule-model Step 11 | `feat: JSON→DSL 마이그레이션 스크립트` |

---

## 5. 테스트 전략

### 단위 테스트

| 대상 | 테스트 항목 | 위치 |
|------|-----------|------|
| SignalManager | 매수/매도 분리, 일일 리셋, ONCE 정책 | `local_server/tests/test_engine.py` |
| Safeguard | Kill Switch, 손실 락, 주문 속도 | `local_server/tests/test_engine.py` |
| StrategyEngine | evaluate_all 흐름, DSL/JSON 분기 | `local_server/tests/test_engine.py` |

### 통합 테스트 (MockBrokerAdapter)

```python
class MockBrokerAdapter(BrokerAdapter):
    async def connect(self): pass
    async def disconnect(self): pass

    @property
    def is_connected(self) -> bool:
        return True

    async def get_balance(self) -> BalanceResult:
        return BalanceResult(cash=Decimal("10000000"), total_eval=Decimal("10000000"))

    async def get_quote(self, symbol: str) -> QuoteEvent:
        return QuoteEvent(symbol=symbol, price=Decimal("50000"), volume=1000)

    async def place_order(self, client_order_id, symbol, side, order_type, qty, limit_price=None) -> OrderResult:
        return OrderResult(
            order_id="ORD001", client_order_id=client_order_id,
            symbol=symbol, side=side, order_type=order_type,
            qty=qty, limit_price=limit_price, status=OrderStatus.FILLED,
        )

    async def cancel_order(self, order_id) -> OrderResult: ...
    async def get_open_orders(self) -> list[OrderResult]: return []
    async def subscribe_quotes(self, symbols, callback): pass
    async def unsubscribe_quotes(self, symbols): pass
```

---

## 6. 미결 사항

| 항목 | 상태 | 결정 |
|------|------|------|
| 가격 검증 괴리 임계값 | 결정 | 1% 유지 |
| 시세 우선순위 | 결정 | WS 우선, REST는 검증용 |
| custom_formula 조건 | **해결** | DSL 파서가 대체 (rule-model) |
| SYNCING 구간 | 미결 | 09:00~09:02 (데이터 안정성 확인 후 조정) |
| 최대 손실 임계값 | 결정 | 사용자 설정 가능 (기본 5%) |
| 주문 속도 제한 | 결정 | 사용자 설정 가능 (기본 10건/분) |

---

## 참고

- `spec/strategy-engine/spec.md` — 엔진 요구사항 F1~F17
- `spec/rule-model/spec.md` — DSL 규칙 모델
- `spec/rule-model/plan.md` — DSL 파서 + 모델/평가기/실행기 구현 계획
- `sv_core/broker/base.py` — BrokerAdapter ABC 정본
- `docs/architecture.md` §3.1, §4.4

---

**마지막 갱신**: 2026-03-07
