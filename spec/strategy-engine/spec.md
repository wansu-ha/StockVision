# 전략 엔진 명세서 (strategy-engine)

> 작성일: 2026-03-04 | 상태: 초안 | Unit 3 (Phase 3-A)
>
> **이전 spec**: `spec/execution-engine/` → 본 spec으로 대체.
> 클라우드 WS 신호 전송 구조에서 **로컬 서버 직접 실행** 구조로 전환.
> **의존**: Unit 1 (BrokerAdapter), Unit 2 (로컬 서버 코어)

---

## 1. 목표

로컬 서버에서 사용자 정의 규칙을 주기적으로 평가하고,
조건 충족 시 BrokerAdapter를 통해 주문을 직접 실행하는 전략 엔진을 구현한다.

**법적 포지션:**
- 사용자가 미리 정의한 규칙 → 로컬에서 자동 실행 = 시스템매매
- 클라우드가 매매 판단/명령을 내리지 않음
- 엔진이 로컬에 있어야 하는 이유: 투자일임 소지 회피

---

## 2. 요구사항

### 2.1 기능적 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| F1 | 장 시간(09:00~15:30) 1분 주기로 규칙을 평가한다 | P0 |
| F2 | 규칙 조건(가격, 지표, 컨텍스트) → True/False 평가 | P0 |
| F3 | 조건 충족 시 주문 전 가격 검증 (BrokerAdapter 현재가 조회) | P0 |
| F4 | 가격 일치 시 BrokerAdapter로 주문 실행 | P0 |
| F5 | 신호 상태 관리 (NEW → SENT → FILLED, 중복 방지) | P0 |
| F6 | 체결 결과를 logs.db에 기록 | P0 |
| F7 | 프론트엔드에 체결 알림 전송 (localhost WS) | P0 |
| F8 | JSON 캐시된 규칙 사용 (프론트 sync 또는 WS push로 갱신) | P0 |
| F9 | 로컬 서버가 직접 fetch한 AI 컨텍스트 캐시 사용 | P1 |
| F10 | 일일 거래 한도 체크 (금액, 종목 수) | P1 |
| F11 | 전략 엔진 시작/중지 API | P1 |
| F12 | 규칙 평가 오류 시 해당 규칙만 비활성화 | P1 |
| F13 | Kill Switch — STOP_NEW(신규 차단) + CANCEL_OPEN(미체결 취소) 2단계 | P0 |
| F14 | 최대 손실 제한 — 당일 실현손익 > 임계값 시 CANCEL_OPEN + 수동 해제 필수 | P0 |
| F15 | 주문 속도 제한 — N건/분 초과 시 주문 차단 (버그 폭주 방지) | P0 |
| F16 | 분봉 구성 — WS 시세로 OHLCV 구성, 키움 서버 시간 기준 분 경계 | P0 |
| F17 | WS 복구 시 누락 분봉 REST 보충 | P1 |

### 2.2 비기능적 요구사항

| 항목 | 목표 |
|------|------|
| 규칙 평가 주기 | 1분 |
| 신호 → 주문 실행 지연 | < 500ms (가격 검증 포함) |
| 동시 평가 규칙 수 | 100개 (v1), 1000개 (확장) |
| 중복 실행 방지 | 100% |
| 메모리 사용 (엔진) | < 50MB |

---

## 3. 아키텍처

### 3.0 용어 정의

| 용어 | 의미 | 예시 |
|------|------|------|
| **Engine Running** | 프로세스 실행 (트레이 상주) | .exe 실행 중 |
| **Strategy Active** | 평가 루프 실행 | 장 시간 1분 주기 cron 동작 중 |
| **Trading Enabled** | 주문 전송 허용 | READY & Kill Switch OFF & 손실 미초과 |

**상태 조합:**

| 상황 | Engine | Strategy | Trading |
|------|--------|----------|---------|
| 정상 운영 | ON | ON | ON |
| Kill Switch STOP_NEW | ON | ON | **OFF** |
| Kill Switch CANCEL_OPEN | ON | ON | **OFF** + 미체결 취소 |
| 손실 제한 발동 | ON | ON | **OFF** + 락 |
| DEGRADED | ON | ON | **OFF** |
| 장외 시간 | ON | OFF | OFF |
| 사용자 수동 중지 | ON | OFF | OFF |

> **핵심 원칙**: 상태 파악을 위해 평가(Strategy)는 가능한 한 계속 돌린다.
> 주문(Trading)만 차단하면 로그/모니터링이 유지된다.

### 3.1 엔진 흐름

```
매 1분 (장 시간)
    ↓
[0] Kill Switch 체크
    └── Trading Enabled == false → 평가만 실행 (주문 스킵) + 로그
    ↓
[0.5] 분봉 유효성 확인
    ├── 직전 1분봉 완성 여부 (키움 서버 시간 기준)
    ├── 누락 분봉 있으면 → REST로 보충
    └── 장 시작 직후 (09:00~09:02) → SYNCING 상태, 평가 보류
    ↓
[1] 규칙 로드 (JSON 캐시에서)
    ├── is_active == true 인 규칙만
    └── 캐시 없으면 → 대기 (프론트 sync 또는 WS push 대기)
    ↓
[2] 각 규칙 평가
    ├── 시세 데이터 (BrokerAdapter 실시간)
    ├── AI 컨텍스트 (메모리 캐시)
    └── 조건 비교 → True/False
    ↓
[3] 안전장치 체크
    ├── 오늘 이미 실행한 규칙? → skip
    ├── 일일 예산 초과? → skip
    ├── 최대 포지션 수 초과? → skip
    ├── 당일 실현 손실 > 임계값? → Trading Enabled=OFF + 락 + 알림
    └── 분당 주문 수 > 한도? → 주문 차단 + 경고 로그
    ↓
[4] 가격 검증
    ├── BrokerAdapter로 현재가 직접 조회
    ├── WS 수신 가격과 비교
    └── 괴리 > 임계값 → 거부 + 로그
    ↓
[5] 주문 실행
    ├── BrokerAdapter → send_order()
    ├── 결과 → logs.db 기록
    └── WS → 프론트엔드 알림
```

### 3.2 모듈 구조

```
local_server/engine/
├── __init__.py
├── scheduler.py       # APScheduler 기반 1분 주기 스케줄러
├── evaluator.py       # 조건 평가 로직
├── signal_manager.py  # 신호 상태 관리 (중복 방지)
├── price_verifier.py  # 주문 전 가격 검증
├── executor.py        # 주문 실행 (BrokerAdapter 호출)
├── limit_checker.py   # 한도 체크 (일일, 종목별)
├── safeguard.py       # Kill Switch + 최대 손실 제한 + 주문 속도 제한
└── context_cache.py   # AI 컨텍스트 인메모리 캐시
```

---

## 4. 상세 설계

### 4.1 스케줄러

```python
class EngineScheduler:
    """장 시간 1분 주기로 규칙 평가 실행."""

    def __init__(self, engine: StrategyEngine):
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
```

### 4.2 조건 평가 (DSL 파서)

> 규칙 데이터 모델 상세: `spec/rule-model/spec.md` 참조
> DSL 파서 구현: `sv_core/parsing/` (lexer → parser → AST → evaluator)

```python
from sv_core.parsing import parse, evaluate as dsl_evaluate

class RuleEvaluator:
    """규칙 조건을 현재 데이터로 평가.

    v2: DSL script → sv_core.parsing.evaluate → (buy, sell)
    v1 폴백: JSON conditions → 기존 AND/OR 평가 → (buy, sell)
    """

    def __init__(self) -> None:
        self._ast_cache: dict[int, tuple[str, Script]] = {}  # {rule_id: (hash, ast)}
        self._cross_states: dict[int, dict] = {}  # 상향돌파/하향돌파 state

    def evaluate(self, rule: dict, market_data: dict, context: dict) -> tuple[bool, bool]:
        """규칙 평가 → (매수 결과, 매도 결과).

        DSL script가 있으면 파싱 → AST 캐시 → 평가.
        없으면 JSON conditions 폴백.
        context: {"현재가": float, "거래량": int, "RSI": Callable, "MA": Callable, ...}
        """
        ...
```

**DSL 파서 모듈 구조** (`sv_core/parsing/`):
- `lexer.py` — 토큰화
- `parser.py` — 토큰 → AST
- `ast_nodes.py` — AST 노드 (Script, BuyBlock, SellBlock, Comparison, FuncCall 등)
- `evaluator.py` — AST를 시세 컨텍스트에서 평가
- `builtins.py` — 내장 필드/함수/패턴 (RSI, MA, 상향돌파 등)

### 4.3 신호 관리 (중복 방지)

**주문 상태머신** (R5 idempotency의 기반):

```
SIGNAL_CREATED → ORDER_SENT → ACCEPTED → FILLED
                           ↘ REJECTED   ↘ PARTIAL → FILLED
                                         ↘ CANCELLED
                                         ↘ EXPIRED

ORDER_SENT + 10초 미수신 → reconcile() 트리거
```

```python
class SignalManager:
    """신호 상태 머신. 규칙당 하루 1회 실행 보장."""

    # 상태: IDLE → ARMED → TRIGGERED → FILLED/FAILED
    # 매일 자정에 IDLE로 리셋

    def __init__(self):
        self._states: dict[int, str] = {}  # rule_id → state
        self._last_reset: date = date.today()

    def can_trigger(self, rule_id: int) -> bool:
        """실행 가능 여부."""
        self._check_daily_reset()
        return self._states.get(rule_id, "IDLE") == "IDLE"

    def mark_triggered(self, rule_id: int):
        self._states[rule_id] = "TRIGGERED"

    def mark_filled(self, rule_id: int):
        self._states[rule_id] = "FILLED"

    def mark_failed(self, rule_id: int):
        self._states[rule_id] = "FAILED"

    def _check_daily_reset(self):
        if date.today() > self._last_reset:
            self._states.clear()
            self._last_reset = date.today()
```

### 4.4 가격 검증

```python
class PriceVerifier:
    """주문 전 BrokerAdapter로 현재가를 재확인."""

    TOLERANCE_PCT = 1.0  # 1% 괴리 허용

    def __init__(self, kiwoom_client):
        self._client = kiwoom_client

    async def verify(self, symbol: str, expected_price: int) -> VerifyResult:
        """
        BrokerAdapter로 현재가 조회 → WS 수신 가격과 비교.
        괴리 > TOLERANCE_PCT → 거부.
        """
        actual_price = await self._client.get_current_price(symbol)
        diff_pct = abs(actual_price - expected_price) / expected_price * 100

        if diff_pct > self.TOLERANCE_PCT:
            return VerifyResult(ok=False, actual=actual_price, diff_pct=diff_pct)

        return VerifyResult(ok=True, actual=actual_price, diff_pct=diff_pct)
```

### 4.5 주문 실행

```python
class OrderExecutor:
    """조건 충족 → 가격 검증 → BrokerAdapter 주문."""

    def __init__(self, kiwoom_client, signal_manager, price_verifier, log_db):
        ...

    async def execute(self, rule: dict, market_data: dict) -> ExecutionResult:
        """
        1. 중복 체크 (SignalManager)
        2. 한도 체크 (LimitChecker)
        3. 가격 검증 (PriceVerifier)
        4. 주문 실행 (BrokerAdapter)
        5. 결과 로그 (logs.db)
        6. WS 알림 (프론트엔드)
        """
        ...
```

---

## 5. 데이터 흐름

### 5.1 규칙 동기화

```
방법 A (브라우저 경유):
  [프론트엔드] 규칙 저장 → POST /api/rules/sync (localhost)
  → [로컬 서버] RuleCache.save(rules) → strategies.json

방법 B (WS push, 브라우저 불필요):
  [클라우드 서버] 규칙 변경 → WS push → [로컬 서버]
  → GET /api/v1/rules (클라우드 서버에서 직접 fetch)
  → RuleCache.save(rules) → strategies.json

[엔진] RuleCache.load() → 메모리 → 평가 시 사용
```

### 5.2 AI 컨텍스트 (로컬 서버 직접 fetch)

```
[로컬 서버] GET /api/v1/context (클라우드 서버에서 직접, JWT 인증)
    ↓ 스케줄 폴링 또는 WS 알림 시
[로컬 서버] ContextCache.update(context) → 인메모리
    ↓
[엔진] ContextCache.get() → 평가 시 사용

※ 프론트엔드 경유 불필요. 로컬 서버가 자립적으로 fetch.
```

---

## 6. 수용 기준

### 6.1 스케줄러

- [x] 장 시간(09:00~15:30)에만 1분 주기로 evaluate_all 호출
- [x] 장외 시간에는 실행하지 않음
- [x] `POST /api/strategy/start` → 엔진 시작
- [x] `POST /api/strategy/stop` → 엔진 중지

### 6.2 조건 평가

- [x] RSI <= 30 AND price <= 50000 → True 반환 (데이터 충족 시)
- [x] OR 조건 정상 동작
- [x] 조건 파싱 오류 → 해당 규칙만 비활성화 + 로그

### 6.3 중복 방지

- [x] 같은 규칙이 하루에 2회 이상 실행되지 않음
- [x] 자정 기준 리셋 → 다음날 재실행 가능

### 6.4 가격 검증

- [x] WS 가격과 REST 가격 괴리 < 1% → 주문 실행
- [x] 괴리 > 1% → 주문 거부 + 로그 기록

### 6.5 주문 실행

- [x] 모의투자 시장가 매수 → 체결 성공 → logs.db 기록
- [x] 체결 알림 → localhost WS로 프론트엔드에 전송

### 6.6 한도

- [x] 일일 예산(budget_ratio) 초과 시 주문 스킵
- [x] 최대 포지션 수 초과 시 주문 스킵

### 6.7 안전장치

**Kill Switch 2단계:**
- [x] STOP_NEW — 신규 주문 차단, 기존 미체결 유지
- [x] CANCEL_OPEN — 신규 차단 + BrokerAdapter로 미체결 전량 취소
- [x] 트레이/프론트에서 단계 선택 가능 (기본: STOP_NEW)
- [x] Kill Switch 해제 → 수동만 허용 (자동 재개 금지)
- [x] Kill Switch 이벤트 logs.db 기록 (활성화/해제/단계)

**최대 손실 제한:**
- [x] 기준: 당일 실현손익만 (평가손익 미포함, v1)
- [x] 데이터: 로컬 체결 로그(logs.db) 기반 당일 실현손익 합산
- [ ] 발동 시: CANCEL_OPEN 자동 실행 + 트레이/프론트 알림
- [x] 해제: 수동만 ("락" — 사용자가 직접 풀기 전까지 Trading Enabled=OFF 유지)
- [x] 해제 절차: 트레이 메뉴 "손실 락 해제" 또는 프론트 대시보드(`POST /api/strategy/unlock`) — 두 경로 외 자동 해제 없음
- [x] 해제 시 logs.db에 해제 이벤트 기록 (시각, 해제 경로, 당시 실현손익)

**주문 속도 제한:**
- [x] 분당 주문 수 > 한도(기본 10건/분) → 초과분 차단 + 경고 로그

### 6.8 분봉 구성

- [x] WS 시세로 1분 OHLCV 구성 (키움 서버 시간 기준 분 경계)
- [x] 장 시작 직후 (09:00~09:02) SYNCING 상태 → 평가 보류
- [ ] WS 끊김 복구 시 누락 분봉 REST로 보충

---

## 7. 범위

### 포함

- `local_server/engine/` 전체
- 스케줄러 (APScheduler)
- 조건 평가 (evaluator)
- 신호 관리 (중복 방지)
- 가격 검증
- 주문 실행 (Unit 1 BrokerAdapter 사용)
- 로그 기록 (Unit 2 logs.db 사용)
- WS 알림 발송
- 안전장치 (Kill Switch, 최대 손실 제한, 주문 속도 제한)

### 미포함

- BrokerAdapter 인터페이스 + 구현체 (Unit 1)
- 로컬 서버 기반 구조 (Unit 2)
- 프론트엔드 UI (Unit 5)
- 백테스팅 (v2)
- Custom LLM 기반 신호 (v2)

---

## 8. 기존 spec과의 관계

| 기존 | 상태 |
|------|------|
| `spec/execution-engine/` | **대체됨** — 클라우드 WS 전송 구조 → 로컬 직접 실행 |

---

## 9. 미결 사항

- [ ] 가격 검증 괴리 임계값 (1%? 0.5%?)
- [ ] 규칙 평가 시 실시간 시세 vs 캐시된 시세 우선순위
- [ ] `custom_formula` 조건 타입의 안전한 파서 (eval 금지)
- [ ] 장 시작 전/후 시간외 거래 지원 여부
- [ ] 다중 규칙 동시 충족 시 주문 우선순위
- [ ] 최대 손실 제한 임계값 기본값 (5%? 사용자 정의?)
- [ ] 주문 속도 제한 기본값 (10건/분?)
- [x] ~~Kill Switch 해제 시 자동 재개 vs 수동 재개~~ → 수동 해제만 허용
- [x] ~~최대 손실: 실현손익 vs 평가손익~~ → v1은 실현손익 기준
- [x] ~~DEGRADED 상태 엔진 정책~~ → Strategy Active=ON, Trading Enabled=OFF (STOP_NEW)
- [x] ~~규칙 데이터 모델 분리~~ → `spec/rule-model/spec.md`로 분리 (매수/매도 분리, 조건 타입 확장, 트리거 정책)
- [ ] 장 시작 SYNCING 구간 길이 (09:00~09:02? 더 길게?)
- [ ] WS 끊김 시 분봉 복구 REST 호출 대상 (차트 API? 현재가?)

---

## 참고

- `spec/execution-engine/spec.md` (이전 버전)
- `docs/architecture.md` §3.1 (주문 흐름), §4.4 (로컬 서버)
- `docs/development-plan-v2.md` Unit 3

---

**마지막 갱신**: 2026-03-09
