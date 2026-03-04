# 실행 엔진 기능 명세서 (execution-engine)

> 작성일: 2026-03-04 | 상태: 초안 | 버전: 1.0

---

## 1. 개요

### 목표
StockVision 시스템에서 **사용자가 정의한 자동매매 규칙을 주기적으로 평가하고, 조건이 충족되면 로컬 브릿지(Kiwoom API 연동)에 실행 신호를 전송**하는 시스템을 구축한다.

### 핵심 가치
- **시스템매매 자동화**: 규칙 기반 의사결정 → 감정 배제, 일관성 확보
- **로컬 브릿지 연동**: 키움증권 API 호출을 로컬에서 수행 → 보안성 + 거래소 규정 준수
- **법적 포지션**: 사용자가 미리 정의한 규칙을 시스템이 실행 → 시스템매매(자동화)로 분류

### 범위
- **로컬 서버 측**: 규칙 평가 엔진, 키움 API 직접 호출, 실행 로그 저장 (logs.db)
- **미포함**: 클라우드 서버에서의 신호 전송 (구버전 개념 — 현재 아님)

> **아키텍처 노트 (2026-03-04)**: 실행 엔진은 **로컬 서버(localhost:8765)**에서 동작.
> 클라우드 → 로컬 WebSocket 신호 전송 구조가 아니라,
> 로컬 서버가 직접 규칙을 평가하고 키움 COM API를 호출함.

---

## 2. 목표 달성 기준

### 성능 요구사항
| 항목 | 목표 | 비고 |
|------|------|------|
| 규칙 평가 주기 | 1분 | 코스피/코스닥 일중 거래 대응 |
| 신호 전송 지연 | < 100ms | WebSocket 기반 |
| 동시 평가 규칙 수 | 1000개 | 확장성 고려 (최초 100개) |
| 중복 실행 방지 | 100% | 조건 만족 → 1회만 실행 |
| 브릿지 재연결 | 자동 | 연결 끊김 시 지수 백오프(1~30s) |

### 기능적 수용 기준
- [x] 활성 규칙 목록을 DB에서 조회할 수 있다
- [ ] 규칙의 조건(가격, 지표, 신호)을 평가할 수 있다
- [ ] 조건 충족 시 키움 COM API로 주문을 직접 실행할 수 있다
- [ ] 주문 실행 결과(성공/실패)를 logs.db에 기록할 수 있다
- [ ] 중복 실행을 방지할 수 있다 (state machine)
- [ ] 키움 COM 연결 상태를 모니터링할 수 있다
- [ ] 키움 API 호출 제한(초당 5건)을 준수할 수 있다
- [ ] 하루 거래 한도, 종목별 한도를 체크할 수 있다

---

## 3. 아키텍처 및 플로우

### 3.1 전체 시스템 플로우

```
[Cloud (stockvision.app)]
    └─ 컨텍스트 API: 시장 변수 제공 (RSI, 변동성, 섹터 강도 등)

[로컬 서버 (localhost:8765)] ← 실행 엔진이 여기서 동작
    ├─ 1. Context Fetch (장 마감 후 1회)
    │    └─ cloud /api/context 호출 → 로컬 캐시 저장
    │
    ├─ 2. Execution Engine (주기적 평가, 1분마다)
    │    ├─ Timer: 매 1분마다 실행
    │    ├─ Load Rules: cloud_config.json에서 활성 규칙 로딩
    │    ├─ Evaluate: 규칙 조건 vs 컨텍스트 캐시 평가
    │    ├─ Filter: 중복/한도 체크
    │    └─ Signal 생성
    │
    └─ 3. 키움 COM API 직접 호출
         └─ 주문 실행 → 체결 결과 → logs.db 저장 → WS로 React에 push

[React 앱 (cloud 호스팅)]
    └─ WS 수신: 체결 결과, 잔고 업데이트, 알림 표시
```

### 3.2 핵심 데이터 흐름

```
cloud_config.json (로컬 파일: 활성 규칙)
  ├─ rule_id, symbol
  ├─ buy_conditions (JSON)
  ├─ sell_conditions (JSON)
  ├─ max_position_count, budget_ratio
  ├─ is_active, last_executed_at

↓ (매 1분)

Execution Engine (로컬 서버 내부)
  ├─ Load: cloud_config.json에서 is_active=true 규칙
  ├─ For each rule:
  │    ├─ Get: 로컬 캐시된 컨텍스트 (cloud에서 fetch한 시장 변수)
  │    ├─ Evaluate: buy_conditions vs context_cache
  │    ├─ Check: already_executed today?
  │    ├─ Check: portfolio limit
  │    ├─ Check: daily_budget_used < budget_ratio * balance
  │    └─ If all pass → Create Signal
  │
  └─ Signal → kiwoom.order.send_order() 직접 호출

↓

ExecutionLog (logs.db — 로컬 SQLite)
  ├─ rule_id, timestamp, status (PENDING/EXECUTED/FAILED)
  ├─ signal_json, error_message
  └─ kiwoom_result (COM API 응답)
```

### 3.3 상태 머신

**Rule Execution State** (하루 단위):

```
[INACTIVE]
    ↓ (is_active=true 이고 condition 충족)
[READY_TO_TRIGGER] ← 조건 만족, 아직 실행 안 함
    ↓
[SIGNAL_SENT] ← WebSocket으로 신호 전송됨
    ↓
[EXECUTED] ← 로컬 브릿지로부터 거래 완료 응답
    ↓ (자정 기준 리셋)
[READY_TO_TRIGGER] (다음 날)

또는

[SIGNAL_SENT]
    ↓ (연결 끊김, 재시도 최대 3회)
[FAILED]
    ↓
[ALERT] (관리자 알림)
```

---

## 4. 전략 조건 평가 로직

### 4.1 조건 타입 (buy_conditions, sell_conditions)

조건은 JSON 형식으로 다음을 포함:

```json
{
  "operator": "AND" | "OR",
  "conditions": [
    {
      "type": "price",
      "field": "current_price",
      "operator": ">=" | "<=" | ">" | "<",
      "value": 10000
    },
    {
      "type": "indicator",
      "field": "rsi_14",
      "operator": ">=" | "<=",
      "value": 70
    },
    {
      "type": "signal",
      "field": "latest_signal",
      "value": "BUY" | "SELL" | "HOLD"
    },
    {
      "type": "volume",
      "field": "volume_sma_ratio",
      "operator": ">=",
      "value": 1.5
    },
    {
      "type": "custom_formula",
      "expression": "rsi_14 > 70 AND macd_histogram < 0"
    }
  ]
}
```

### 4.2 평가 알고리즘

**Pseudocode:**

```python
def evaluate_conditions(rule: AutoTradingRule, current_data: StockSnapshot) -> bool:
    """
    규칙의 조건을 현재 데이터로 평가.

    Args:
        rule: 자동매매 규칙
        current_data: 종목의 최신 시세, 지표, 신호

    Returns:
        bool: 조건 충족 여부
    """
    conditions = rule.buy_conditions if rule.direction == "BUY" else rule.sell_conditions

    if conditions["operator"] == "AND":
        return all(evaluate_single_condition(c, current_data) for c in conditions["conditions"])
    else:  # OR
        return any(evaluate_single_condition(c, current_data) for c in conditions["conditions"])

def evaluate_single_condition(condition: dict, current_data: dict) -> bool:
    """단일 조건 평가."""
    cond_type = condition["type"]

    if cond_type == "price":
        return compare_values(current_data["current_price"], condition)
    elif cond_type == "indicator":
        field = condition["field"]
        return compare_values(current_data[field], condition)
    elif cond_type == "signal":
        return current_data["latest_signal"] == condition["value"]
    elif cond_type == "volume":
        return compare_values(current_data["volume_ratio"], condition)
    elif cond_type == "custom_formula":
        return evaluate_expression(condition["expression"], current_data)

    return False

def compare_values(value: float, condition: dict) -> bool:
    """값 비교."""
    op = condition["operator"]
    target = condition["value"]

    if op == ">=":
        return value >= target
    elif op == "<=":
        return value <= target
    elif op == ">":
        return value > target
    elif op == "<":
        return value < target

    return False
```

### 4.3 조건 평가 데이터 소스

평가에 필요한 데이터:

| 데이터 | 출처 | 갱신 주기 | 비고 |
|--------|------|---------|------|
| current_price | StockPrice (실시간) | 실시간 또는 1분 | 키움 API에서 수집 |
| rsi_14, macd, ema_20 | TechnicalIndicator | 1분 | 매분 재계산 |
| latest_signal | Signal | 5분 또는 1분 | 기술적 지표 기반 신호 생성 |
| volume, volume_sma_ratio | StockPrice | 1분 | 현재 거래량 / 20일 평균 |
| prediction_score | Prediction | 1회/일 (장 마감 후) | RF 모델 예측 |

---

## 5. 브릿지 신호 프로토콜

### 5.1 WebSocket 연결

**Server Setup (FastAPI):**

```python
from fastapi import WebSocketDisconnect
from fastapi.websockets import WebSocket

class ExecutionEngine:
    def __init__(self):
        self.bridge_clients: dict[str, WebSocket] = {}  # bridge_id → ws
        self.reconnect_attempts = {}

    async def register_bridge(self, bridge_id: str, websocket: WebSocket):
        """로컬 브릿지 연결 등록."""
        await websocket.accept()
        self.bridge_clients[bridge_id] = websocket
        self.reconnect_attempts[bridge_id] = 0

        # 로그: 브릿지 연결 성공
        logger.info(f"Bridge connected: {bridge_id}")

    async def unregister_bridge(self, bridge_id: str):
        """브릿지 연결 해제."""
        if bridge_id in self.bridge_clients:
            del self.bridge_clients[bridge_id]
            logger.warning(f"Bridge disconnected: {bridge_id}")
```

### 5.2 신호 형식 (JSON)

**신호 전송 (Server → Bridge):**

```json
{
  "signal_id": "sig_20260304_001",
  "timestamp": "2026-03-04T10:30:00Z",
  "rule_id": 42,
  "account_id": 1,
  "symbol": "005930",  // 삼성전자 코드
  "side": "BUY",
  "quantity": 10,
  "order_type": "MARKET",
  "limit_price": null,
  "reason": {
    "buy_conditions": [
      { "type": "rsi_14 >= 70", "value": 75.2 },
      { "type": "signal == BUY", "value": "BUY" }
    ]
  },
  "broker_hint": {
    "max_position_count": 5,
    "portfolio_count_today": 3,
    "daily_budget_used": 3000000,
    "available_budget": 7000000
  }
}
```

**응답 (Bridge → Server):**

```json
{
  "signal_id": "sig_20260304_001",
  "status": "EXECUTED" | "FAILED" | "PARTIAL",
  "kiwoom_order_id": "10000123",
  "filled_quantity": 10,
  "filled_price": 59800,
  "timestamp": "2026-03-04T10:30:15Z",
  "error_message": null,
  "metadata": {
    "api_call_time_ms": 245,
    "remaining_daily_limit": 998  // 키움 API 일일 호출 수 남은 건수
  }
}
```

### 5.3 전송 매커니즘

```python
async def send_signal_to_bridge(self, signal: ExecutionSignal, bridge_id: str = "primary"):
    """
    신호를 로컬 브릿지에 전송 (WebSocket).

    1. 연결 확인
    2. 신호 JSON 직렬화
    3. WebSocket send
    4. Timeout 설정 (10초)
    5. 응답 대기 (또는 비동기 콜백)
    6. ExecutionLog 기록
    """
    if bridge_id not in self.bridge_clients:
        # 재연결 시도
        await self.reconnect_bridge(bridge_id)
        if bridge_id not in self.bridge_clients:
            raise BridgeNotConnectedError(bridge_id)

    ws = self.bridge_clients[bridge_id]
    signal_json = signal.to_json()

    try:
        await ws.send_json(signal_json)
        await self._log_signal(signal, status="SENT")
    except Exception as e:
        logger.error(f"Failed to send signal: {e}")
        await self._log_signal(signal, status="FAILED", error=str(e))
        raise

async def reconnect_bridge(self, bridge_id: str, max_attempts: int = 3):
    """
    브릿지 재연결 (지수 백오프).

    - Attempt 1: 1초 대기
    - Attempt 2: 5초 대기
    - Attempt 3: 30초 대기
    - Attempt 4+: 포기, 알림 발송
    """
    attempt = self.reconnect_attempts.get(bridge_id, 0)
    if attempt >= max_attempts:
        logger.critical(f"Bridge {bridge_id} failed after {max_attempts} attempts. Alert admin.")
        # Slack/Telegram 알림
        return False

    wait_seconds = [1, 5, 30][attempt]
    logger.info(f"Reconnecting bridge {bridge_id} (attempt {attempt+1}, wait {wait_seconds}s)")

    await asyncio.sleep(wait_seconds)
    self.reconnect_attempts[bridge_id] = attempt + 1

    # 실제 재연결은 클라이언트가 다시 /ws 엔드포인트로 연결할 때 자동으로 등록됨
```

---

## 6. 안전장치 (중복 방지, 한도, 에러 처리)

### 6.1 중복 실행 방지

**문제:**
같은 조건이 여러 평가 사이클에서 계속 충족되면, 같은 신호가 반복 전송될 수 있음.

**솔루션 1: Last Execution Window**

```python
def should_execute(rule: AutoTradingRule, symbol: str) -> bool:
    """
    규칙을 실행할지 판단 (중복 방지).

    Logic:
    1. rule.last_executed_at 조회
    2. 오늘(자정 기준)이면? 이미 실행함 → False
    3. 어제(자정 이전)이면? 새로운 날 → True
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if rule.last_executed_at is None:
        return True

    return rule.last_executed_at < today_start
```

**솔루션 2: State Machine + Hysteresis**

```python
class ExecutionState(Enum):
    IDLE = "IDLE"  # 조건 미충족
    ARMED = "ARMED"  # 조건 충족, 신호 미전송
    TRIGGERED = "TRIGGERED"  # 신호 전송됨

def evaluate_with_state(rule: AutoTradingRule) -> ExecutionState:
    """
    State machine: 충족 → 1회 신호 → 리셋.

    1. condition 미충족 → IDLE
    2. condition 충족 + state=IDLE → ARMED
    3. state=ARMED → send signal → TRIGGERED
    4. (자정 경과 또는 수동 리셋) → IDLE
    """
    if not evaluate_conditions(rule):
        return ExecutionState.IDLE

    if rule.execution_state == ExecutionState.IDLE:
        rule.execution_state = ExecutionState.ARMED
        return ExecutionState.ARMED
    elif rule.execution_state == ExecutionState.ARMED:
        rule.execution_state = ExecutionState.TRIGGERED
        return ExecutionState.TRIGGERED
    else:
        return ExecutionState.TRIGGERED
```

### 6.2 키움 API 호출 제한 준수

**요구사항:**
초당 5건 이하의 키움 API 호출.

**전략:**
- 신호 큐잉 (Signal Queue)
- Rate Limiter (Token Bucket Algorithm)
- 브릿지 측에서도 처리, 서버 측에서도 검증

```python
class RateLimiter:
    def __init__(self, rate: int = 5, window: int = 1):
        """
        rate: 초당 최대 요청 수
        window: 시간 윈도우 (초)
        """
        self.rate = rate
        self.window = window
        self.tokens = deque()  # (timestamp, count)

    def allow(self) -> bool:
        """요청 허용 여부 판단."""
        now = time.time()

        # 오래된 토큰 제거 (window 초과)
        while self.tokens and self.tokens[0][0] < now - self.window:
            self.tokens.popleft()

        # 토큰 충분?
        total_requests = sum(count for _, count in self.tokens)
        if total_requests < self.rate:
            self.tokens.append((now, 1))
            return True

        return False

signal_queue: asyncio.Queue[ExecutionSignal] = asyncio.Queue()
rate_limiter = RateLimiter(rate=5, window=1)

async def signal_dispatcher():
    """신호 큐를 처리하는 태스크."""
    while True:
        signal = await signal_queue.get()

        if rate_limiter.allow():
            await send_signal_to_bridge(signal)
        else:
            # 다시 큐에 넣고 대기
            await asyncio.sleep(0.2)
            await signal_queue.put(signal)
```

### 6.3 일일 거래 한도

**종류:**
1. **하루 거래 한도** (전체 거래량)
2. **종목별 한도** (특정 종목 최대 보유)
3. **포지션 수 한도** (최대 보유 종목 수)

```python
def check_trading_limits(rule: AutoTradingRule, account: VirtualAccount) -> bool:
    """거래 한도 체크."""

    # 1. Daily Budget: 오늘 사용한 예산 < 예산 한도
    today = date.today()
    today_trades = db.query(VirtualTrade).filter(
        VirtualTrade.account_id == account.id,
        VirtualTrade.trade_date >= today
    ).all()
    today_used = sum(t.total_amount for t in today_trades)
    daily_limit = account.balance * rule.budget_ratio

    if today_used >= daily_limit:
        logger.warning(f"Daily budget exceeded for account {account.id}")
        return False

    # 2. Max Position Count
    positions = db.query(VirtualPosition).filter(
        VirtualPosition.account_id == account.id
    ).all()

    if len(positions) >= rule.max_position_count:
        logger.warning(f"Max position count reached for rule {rule.id}")
        return False

    # 3. 종목별 한도 (중복 매수 방지)
    same_symbol_position = next(
        (p for p in positions if p.stock_id == rule.stock_id),
        None
    )
    if same_symbol_position:
        logger.info(f"Already holding {rule.symbol}, skip buy signal")
        return False

    return True
```

### 6.4 에러 처리 및 복구

**에러 분류:**

| 에러 | 원인 | 대응 |
|------|------|------|
| BridgeNotConnectedError | 로컬 브릿지 미연결 | 재연결 시도 (지수 백오프) |
| SignalTimeoutError | 10초 내 응답 없음 | 재전송 또는 수동 확인 |
| KiwoomAPIError | 키움 API 실패 (한도 초과 등) | 로그 기록, 관리자 알림 |
| InvalidRuleError | 규칙 데이터 오류 (조건 파싱 실패) | 규칙 비활성화, 알림 |
| InsufficientFundsError | 잔고 부족 | 신호 스킵, 로그 |

```python
async def execute_rule_safe(rule: AutoTradingRule):
    """안전한 규칙 실행 (에러 처리)."""
    try:
        # 조건 평가
        if not evaluate_conditions(rule):
            return

        # 중복 체크
        if not should_execute(rule):
            logger.debug(f"Rule {rule.id} already executed today")
            return

        # 한도 체크
        account = db.query(VirtualAccount).get(rule.account_id)
        if not check_trading_limits(rule, account):
            logger.warning(f"Trading limit exceeded for rule {rule.id}")
            return

        # 신호 생성
        signal = create_execution_signal(rule)

        # 전송
        await send_signal_to_bridge(signal, bridge_id="primary")

        # 규칙 상태 업데이트
        rule.last_executed_at = datetime.utcnow()
        rule.execution_state = ExecutionState.TRIGGERED
        db.commit()

    except BridgeNotConnectedError as e:
        logger.error(f"Bridge not connected: {e}")
        await alert_admin(f"Bridge connection failed", severity="HIGH")
    except KiwoomAPIError as e:
        logger.error(f"Kiwoom API error: {e}")
        await _log_signal(signal, status="FAILED", error=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in rule {rule.id}: {e}")
        await alert_admin(f"Execution engine error: {e}", severity="CRITICAL")
```

---

## 7. 기술 요구사항

### 7.1 데이터베이스 스키마 (신규/확장)

**신규 테이블:**

```python
class ExecutionLog(Base):
    """실행 엔진 신호 로그."""
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("auto_trading_rules.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("virtual_accounts.id"), nullable=False)
    symbol = Column(String(10), nullable=False)

    signal_id = Column(String(50), unique=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 신호 상태
    status = Column(String(20))  # PENDING, SENT, EXECUTED, FAILED
    signal_json = Column(JSON, nullable=False)  # 전송된 신호

    # 응답 (로컬 브릿지로부터)
    response_json = Column(JSON)  # 거래 결과
    response_timestamp = Column(DateTime)

    # 에러
    error_message = Column(String(500))
    error_code = Column(String(50))

    # 메타데이터
    retry_count = Column(Integer, default=0)
    bridge_id = Column(String(50), default="primary")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_rule_timestamp', 'rule_id', 'timestamp'),
        Index('idx_status_timestamp', 'status', 'timestamp'),
    )

class AutoTradingRule(Base):  # 기존 모델 확장
    # ... 기존 필드 ...

    # 실행 엔진 필드 (신규)
    execution_state = Column(String(20), default="IDLE")  # IDLE, ARMED, TRIGGERED
    last_executed_at = Column(DateTime)
    last_execution_status = Column(String(20))  # SUCCESS, FAILED, SKIPPED

    # 평가 조건 (JSON)
    buy_conditions = Column(JSON)  # { operator: "AND", conditions: [...] }
    sell_conditions = Column(JSON)

    # 한도 설정
    max_position_count = Column(Integer, default=5)
    budget_ratio = Column(Float, default=0.2)  # 계좌 잔고의 몇 % 사용할지

    # 신호 설정
    signal_priority = Column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH
    signal_retry_max = Column(Integer, default=3)
```

### 7.2 API 엔드포인트 (신규)

```
# 실행 엔진 상태 조회
GET /api/v1/execution/status
  → { bridge_connected: bool, rules_count: int, signals_queue_size: int }

# 규칙별 실행 로그 조회
GET /api/v1/execution/logs?rule_id={id}&limit=50
  → [ { signal_id, timestamp, status, signal_json, response_json }, ... ]

# WebSocket: 로컬 브릿지 연결
WS /ws/bridge/primary
  → 로컬 브릿지가 연결 유지하는 WebSocket (신호 수신 + 응답 전송)

# 테스트: 규칙 평가 수동 실행
POST /api/v1/execution/test-rule/{rule_id}
  → { evaluated: bool, conditions_met: bool, reason: string }

# 테스트: 신호 수동 전송
POST /api/v1/execution/send-signal
  Request: { rule_id: int, symbol: string, side: "BUY"|"SELL" }
  Response: { signal_id: string, status: string }
```

### 7.3 환경 변수 및 설정

```bash
# .env
EXECUTION_ENGINE_ENABLED=true
EXECUTION_INTERVAL_SECONDS=60  # 1분
SIGNAL_TIMEOUT_SECONDS=10
BRIDGE_RECONNECT_MAX_ATTEMPTS=3
BRIDGE_RECONNECT_BACKOFF=[1, 5, 30]  # 초

KIWOOM_API_RATE_LIMIT=5  # 초당 5건
KIWOOM_API_DAILY_LIMIT=10000

# Redis (옵션: 신호 큐)
REDIS_URL=redis://localhost:6379
SIGNAL_QUEUE_NAME=execution:signals:queue
```

### 7.4 로깅 및 모니터링

**로깅 레벨:**

```
INFO: 규칙 평가 시작/완료, 신호 전송 성공
WARNING: 중복 실행 방지, 한도 초과, 브릿지 재연결
ERROR: API 에러, 신호 전송 실패, 조건 파싱 에러
CRITICAL: 브릿지 연결 상실, 엔진 중단
```

**메트릭 (Prometheus):**

```
execution_rule_evaluations_total  # 총 규칙 평가 수
execution_signals_sent_total      # 총 신호 전송 수
execution_signals_failed_total    # 실패한 신호
execution_rule_evaluation_duration_seconds  # 평가 소요 시간
execution_bridge_connected        # 브릿지 연결 상태 (1=연결, 0=미연결)
execution_signal_queue_size       # 대기 신호 수
```

---

## 8. 미결 사항 및 향후 계획

### 8.1 미결 사항 (Backlog)

1. **신호 응답 매커니즘**
   - 현재: 비동기 응답 (ExecutionLog에 기록)
   - 개선: WebSocket 핸드셰이크 (request_id 기반 매칭)

2. **조건 표현식 검증**
   - 현재: Python `eval()` (보안 리스크)
   - 개선: AST 파서 또는 간단한 수식 라이브러리

3. **분산 실행 (Multi-Server)**
   - 현재: 단일 서버 가정
   - 개선: Celery + Redis 기반 분산 태스크 (Lock-based duplicate prevention)

4. **규칙 변경 즉시 반영**
   - 현재: 다음 평가 주기에 반영
   - 개선: In-memory cache + 변경 이벤트 (RELOAD_RULES)

5. **실시간 조건 평가**
   - 현재: 1분 주기
   - 개선: WebSocket 기반 실시간 가격 스트림 + 이벤트 기반 평가

### 8.2 향후 계획 (Phase 3+)

- [ ] AI 기반 신호 생성 (LSTM 모델)
- [ ] 전략 최적화 엔진 (유전 알고리즘)
- [ ] 실시간 포지션 모니터링 (로컬 브릿지 → 서버 업데이트)
- [ ] 고급 리스크 관리 (VaR, Sharpe 최적화)
- [ ] 멀티 브릿지 지원 (분산 거래)

---

## 9. 참고 자료 및 관련 모듈

### 기존 코드 경로

| 모듈 | 경로 | 용도 |
|------|------|------|
| Auto Trading Rule | `backend/app/models/auto_trading.py` | 규칙 데이터 모델 |
| Virtual Trading | `backend/app/models/virtual_trading.py` | 계좌, 포지션, 거래 |
| Stock Data | `backend/app/models/stock.py` | 종목, 가격, 지표 |
| Trading Service | `backend/app/services/virtual_trading_engine.py` | 가상 거래 로직 |
| Technical Indicators | `backend/app/services/technical_indicators.py` | 지표 계산 |
| Trading API | `backend/app/api/trading.py` | 자동매매 규칙 API |

### 관련 문서

- `docs/architecture.md` — 시스템 아키텍처
- `spec/virtual-auto-trading/spec.md` — 가상 자동매매 시스템
- `spec/local-bridge/spec.md` — 로컬 브릿지 (TBD)
- `spec/strategy-builder/spec.md` — 규칙 빌더 UI (TBD)

---

## 10. 수용 테스트 (Acceptance Criteria)

### Phase 1: 기본 평가 엔진

- [ ] 활성 규칙 목록을 DB에서 조회할 수 있다
- [ ] 규칙의 조건(가격, RSI, 신호)을 평가할 수 있다 (단위 테스트)
- [ ] 조건 충족 시 Signal 객체를 생성할 수 있다
- [ ] 신호 로그가 DB(ExecutionLog)에 기록된다

### Phase 2: WebSocket 신호 전송

- [ ] 로컬 브릿지 WebSocket 연결을 수락할 수 있다 (`/ws/bridge/primary`)
- [ ] 신호를 JSON 형식으로 직렬화하여 전송할 수 있다
- [ ] 브릿지로부터 응답을 수신하여 ExecutionLog에 기록할 수 있다
- [ ] 신호 전송 제한 시간(10초) 내 완료된다

### Phase 3: 안전장치

- [ ] 같은 규칙이 하루에 2회 이상 실행되지 않는다
- [ ] 키움 API 호출이 초당 5건을 초과하지 않는다
- [ ] 일일 거래 한도(budget_ratio)를 초과하여 신호를 보내지 않는다
- [ ] 최대 보유 종목 수(max_position_count)를 초과하지 않는다

### Phase 4: 브릿지 연결 관리

- [ ] 브릿지 연결 끊김 시 자동 재연결을 시도한다 (지수 백오프)
- [ ] 브릿지 미연결 시 신호를 큐에 보관했다가 재연결 후 전송한다
- [ ] 최대 재연결 시도 실패 시 관리자에게 알림한다

### Phase 5: E2E 플로우

- [ ] 자동매매 규칙 생성 → 조건 평가 → 신호 전송 → 거래 실행의 전체 플로우가 동작한다
- [ ] 실행 로그를 API로 조회할 수 있다
- [ ] 테스트 신호 수동 전송 (`POST /api/v1/execution/send-signal`) 가능하다

---

**문서 히스토리:**

| 버전 | 날짜 | 내용 |
|------|------|------|
| 1.0 | 2026-03-04 | 초안 작성 |

