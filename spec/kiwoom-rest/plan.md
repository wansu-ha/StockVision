# 키움 REST API 연동 구현 계획서 (kiwoom-rest)

> 작성일: 2026-03-05 | 상태: 구현 완료 | Unit 1 (Phase 3-A)
>
> **기반**: `spec/kiwoom-rest/spec.md` (2026-03-04)
>
> **검토 (2026-03-07)**: 이전 AI가 한국투자증권 Open API+를 키움증권으로 착각하여 구현.
> **코드 전면 재구현 필요** — `local_server/broker/kiwoom/` 전체가 잘못된 증권사 API 기반.
> 증권사 방향 결정 후 spec/plan/code 모두 재작성해야 함.

---

## 0. 현황

### 출발점

**이전 상태** (`spec/kiwoom-integration/` — 폐기):
- COM 기반 키움 HTS API (32bit Python, pyKiwoom 의존)
- 동기 호출, asyncio 미지원
- Windows 종속성, 배포 복잡도 높음

**변경 사유**:
- 키움증권이 2025년 REST API 공개 → COM/HTS 제약 완전 해소
- 64bit Python 3.13 + asyncio 표준 라이브러리로 직접 호출 가능
- 증권사 교체 가능한 Adapter 패턴 설계

### 기존 코드 상태

**현재**: 프로젝트 초기 단계
- `backend/` — Phase 2 기반 (가상 거래, yfinance 데이터)
- `local_server/` 디렉토리 미존재 → 신규 생성 필요
- `broker/` 패키지 미존재 → 신규 생성 필요

**신규 생성할 모듈**:
```
local_server/
├── __init__.py
├── main.py                      # FastAPI 서버 진입점 (나중 단계)
└── broker/
    ├── __init__.py
    ├── base.py                  # BrokerAdapter ABC + 공통 모델
    ├── factory.py               # 팩토리
    └── kiwoom/
        ├── __init__.py
        ├── adapter.py           # KiwoomAdapter
        ├── auth.py              # OAuth 토큰 관리
        ├── order.py             # 주문 실행
        ├── quote.py             # 현재가/잔고 조회
        ├── websocket.py         # WS 시세 수신
        ├── rate_limiter.py      # Rate Limiter (Token Bucket)
        ├── state_machine.py     # 상태 머신
        ├── error_classifier.py  # 오류 분류
        └── models.py            # 데이터 클래스 (kiwoom 특화)

sv_core/  (공유 패키지 — 클라우드 서버에서도 사용)
├── __init__.py
└── broker/
    ├── base.py                  # BrokerAdapter ABC + 공통 모델
    └── models.py                # 공통 데이터 클래스
```

**의존성 추가** (requirements.txt):
```
httpx                       # REST API 비동기 호출 (local-server-core와 통일)
websockets                  # WebSocket 클라이언트
python-dateutil            # 토큰 만료 시간 파싱
```

---

## 1. 구현 단계 (13 Steps)

### Step 1 — 공유 패키지 구조 + BrokerAdapter ABC

**목표**: `sv_core` 패키지 생성 및 BrokerAdapter 인터페이스 정의

**파일 생성**:
- `sv_core/__init__.py`
- `sv_core/broker/__init__.py`
- `sv_core/broker/base.py` — BrokerAdapter ABC + 공통 데이터 클래스
- `sv_core/broker/models.py` — OrderResult, BalanceResult, Position, QuoteEvent

**주요 구현**:

1. **BrokerAdapter ABC**:
   ```python
   class BrokerAdapter(ABC):
       @abstractmethod
       async def authenticate(self) -> None: ...
       @abstractmethod
       async def is_authenticated(self) -> bool: ...
       @abstractmethod
       async def send_order(...) -> OrderResult: ...
       @abstractmethod
       async def cancel_order(order_no: str) -> OrderResult: ...
       @abstractmethod
       async def get_current_price(symbol: str) -> int: ...
       @abstractmethod
       async def get_balance(account_no: str) -> BalanceResult: ...
       @abstractmethod
       async def get_positions(account_no: str) -> list[Position]: ...
       @abstractmethod
       async def subscribe(symbols: list[str], data_type: str) -> None: ...
       @abstractmethod
       async def unsubscribe(symbols: list[str], data_type: str) -> None: ...
       @abstractmethod
       async def listen(self) -> AsyncIterator[QuoteEvent]: ...
   ```

2. **공통 데이터 클래스**:
   - `@dataclass OrderResult` — success, order_no, message, raw_response
   - `@dataclass BalanceResult` — deposit, total_eval, positions
   - `@dataclass Position` — symbol, name, qty, avg_price, current_price, pnl, pnl_rate
   - `@dataclass QuoteEvent` — event_type, symbol, price, volume, timestamp, raw_data

3. **BrokerAdapter는 sync 메서드 미포함** (async only)

**검증**:
- [ ] `sv_core/broker/base.py` ABC import 가능
- [ ] 모든 abstract 메서드 명시
- [ ] dataclass 직렬화 가능 (json.dumps 호환)

---

### Step 2 — KiwoomAuth (OAuth 토큰 관리)

**목표**: 키움 REST API 인증 (Bearer Token 발급 및 자동 갱신)

**파일 생성**:
- `local_server/__init__.py`
- `local_server/broker/__init__.py`
- `local_server/broker/kiwoom/__init__.py`
- `local_server/broker/kiwoom/auth.py`

**주요 구현**:

```python
class KiwoomAuth:
    def __init__(self, app_key: str, secret_key: str, is_mock: bool = True):
        self._app_key = app_key
        self._secret_key = secret_key
        self._base_url = "https://mockapi.kiwoom.com" if is_mock else "https://openapi.kiwoom.com"
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    async def get_token(self) -> str:
        """유효한 토큰 반환. 만료 임박(1시간 미만) 시 자동 갱신."""
        if self._is_token_valid():
            return self._token
        await self._refresh_token()
        return self._token

    async def _refresh_token(self) -> None:
        """POST /v1/auth/login (api-id: au10001) → Bearer Token 발급"""
        # httpx.AsyncClient로 POST 요청
        # Body: { "appkey": app_key, "secretkey": secret_key }
        # Response: { "access_token": "...", "expires_in": ... }
        # 토큰 저장 및 만료 시간 계산

    def _is_token_valid(self) -> bool:
        """현재 토큰이 유효하고 만료까지 1시간 이상 남았는지 확인"""
        if self._token is None or self._token_expires_at is None:
            return False
        return datetime.now(timezone.utc) < self._token_expires_at - timedelta(hours=1)
```

**외부 의존성**:
- httpx (비동기 HTTP)
- datetime, timezone

**검증**:
- [ ] `KiwoomAuth(app_key, secret, is_mock=True).get_token()` → Bearer Token 반환 (실제 호출)
- [ ] 토큰 만료 1시간 전 자동 갱신 (목 테스트)
- [ ] 모의투자/실거래 URL 전환 확인

---

### Step 3 — KiwoomQuote (현재가/잔고 조회)

**목표**: 종목 현재가 및 계좌 잔고/보유종목 조회

**파일 생성**:
- `local_server/broker/kiwoom/quote.py`

**주요 구현**:

```python
class KiwoomQuote:
    def __init__(self, auth: KiwoomAuth, rate_limiter: "RateLimiter"):
        self._auth = auth
        self._rate_limiter = rate_limiter

    async def get_current_price(self, symbol: str) -> int:
        """
        기본 종목 정보 조회 (api-id: ka10001 또는 ka10080)
        → 현재가 정수 반환
        주문 전 가격 검증용
        """
        # rate_limiter 거쳐서 API 호출
        # symbol 형식: "005930" (KRX) 또는 "005930_NX" (NXT)
        # 응답 파싱 → 현재가 추출

    async def get_balance(self, account_no: str) -> BalanceResult:
        """
        GET /v1/account/balance (api-id: 미정)
        → 예수금, 총평가금액, 보유종목 목록 반환
        BalanceResult(deposit, total_eval, positions=[])로 변환
        """
        # rate_limiter 거쳐서 API 호출
        # 응답: { "account_info": {...}, "holding_list": [...] }
        # Position 리스트로 변환

    async def get_positions(self, account_no: str) -> list[Position]:
        """get_balance의 positions 추출"""
        balance = await self.get_balance(account_no)
        return balance.positions
```

**외부 의존성**:
- KiwoomAuth (Step 2)
- RateLimiter (Step 5)
- BalanceResult, Position (Step 1)

**검증**:
- [ ] `get_current_price("005930")` → 현재가 정수 반환
- [ ] `get_balance(account_no)` → BalanceResult 반환 (예수금 > 0)
- [ ] 보유종목 있을 경우 Position 리스트 정상 구성

---

### Step 4 — KiwoomOrder (주문 실행)

**목표**: 시장가/지정가 매수/매도 주문 실행

**파일 생성/수정**:
- `local_server/broker/kiwoom/order.py`
- `local_server/broker/kiwoom/models.py` — kiwoom 특화 모델 (OrderError 등)

**주요 구현**:

```python
class KiwoomOrder:
    def __init__(self, auth: KiwoomAuth, rate_limiter: "RateLimiter"):
        self._auth = auth
        self._rate_limiter = rate_limiter

    async def send_order(
        self,
        account_no: str,
        symbol: str,
        side: Literal["BUY", "SELL"],
        qty: int,
        price: int = 0,          # 0 = 시장가
        order_type: str = "0",    # 0=지정가, 3=시장가
    ) -> OrderResult:
        """
        POST /v1/order (api-id: kt10000)
        params:
          dmst_stex_tp: "0" (KRX) / "1" (NXT) / "2" (SOR)
          stk_cd: 종목코드
          ord_qty: 주문수량
          ord_uv: 주문단가 (시장가면 0)
          trde_tp: 주문유형 (0=지정가, 3=시장가)
          cano: 계좌번호_앞자리
          acnt_prdt_cd: 계좌번호_뒷자리
          crfl_dvsn: 실거래 신용구분 (미정, 기본값 0)

        Response: { "ord_no": "...", "return_code": "0", "return_msg": "..." }
        OrderResult로 변환
        """
        # rate_limiter 거쳐서 API 호출
        # 응답 파싱 → OrderResult(success, order_no, message, raw_response)
        # 실패 시 return_code != "0" → success=False

    async def cancel_order(self, order_no: str) -> OrderResult:
        """
        주문 취소 (api-id 미정, 문서 확인 필요)
        미구현 → Step 10+ 또는 Unit 3 연동 시
        """
        raise NotImplementedError("P2 기능")
```

**외부 의존성**:
- KiwoomAuth (Step 2)
- RateLimiter (Step 5)
- OrderResult (Step 1)

**검증**:
- [ ] 모의투자 시장가 매수 10주 → OrderResult.success=True, order_no 반환
- [ ] 지정가 매도 → OrderResult 반환
- [ ] 잔고 부족 → success=False, 에러 메시지 포함

---

### Step 5 — RateLimiter (Token Bucket)

**목표**: 키움 API 초당 5건 제한을 Token Bucket으로 관리

**파일 생성**:
- `local_server/broker/kiwoom/rate_limiter.py`

**주요 구현**:

```python
class RateLimiter:
    """
    Token Bucket 알고리즘.
    - 초당 5건 제한 (키움 공식 제한)
    - 모든 REST API 호출이 이 객체를 경유 (단일 관문, R1)
    """

    def __init__(self, rate: int = 5, per_seconds: float = 1.0):
        self._rate = rate
        self._per = per_seconds
        self._tokens = rate
        self._refill_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """
        호출 권한 획득.
        - 토큰 충분 → 즉시 반환
        - 토큰 부족 → 대기 후 반환
        """
        async with self._lock:
            await self._refill()
            while self._tokens < tokens:
                # 토큰 부족 → 재충전 시간 계산 후 대기
                sleep_time = (tokens - self._tokens) * self._per / self._rate
                await asyncio.sleep(sleep_time)
                await self._refill()
            self._tokens -= tokens

    async def _refill(self) -> None:
        """토큰 보충 (시간 경과 기반)"""
        now = time.monotonic()
        elapsed = now - self._refill_at
        refill = elapsed / self._per * self._rate
        self._tokens = min(self._rate, self._tokens + refill)
        self._refill_at = now

    async def execute(self, coro) -> Any:
        """rate limit 적용하여 코루틴 실행 (편의 메서드)"""
        await self.acquire()
        return await coro
```

**외부 의존성**:
- asyncio, time (표준 라이브러리)

**검증**:
- [ ] 5개 호출을 < 1초에 완료 가능
- [ ] 6번째 호출은 최소 1초 대기 후 실행
- [ ] 동시 호출 시 순서대로 큐잉 확인 (asyncio.Lock)

---

### Step 6 — KiwoomWebSocket (WS 시세 수신)

**목표**: WebSocket 연결 및 실시간 시세/체결 수신

**파일 생성**:
- `local_server/broker/kiwoom/websocket.py`

**주요 구현**:

```python
class KiwoomWebSocket:
    WS_URL = "wss://api.kiwoom.com:10000/api/dostk/websocket"

    def __init__(self, auth: KiwoomAuth):
        self._auth = auth
        self._ws = None
        self._connected = False
        self._subscribed: dict[str, list[str]] = {}  # { symbol: [data_type, ...] }

    async def connect(self) -> None:
        """
        WebSocket 연결 + LOGIN 패킷 전송.
        시간 제약 없음 (1시간 무활동 시 자동 종료).
        """
        # websockets.connect(WS_URL)
        # LOGIN 패킷: { "trnm": "LOGIN", "token": await self._auth.get_token() }
        # 연결 성공 여부 확인

    async def subscribe(self, symbols: list[str], data_type: str = "0B") -> None:
        """
        실시간 시세 구독.
        { "trnm": "REG", "grp_no": "1",
          "data": [{"item": symbols, "type": [data_type]}] }

        0B: 실시간 체결가
        (기타 type 코드는 키움 문서 확인)
        """
        # _subscribed에 등록
        # WS 연결 상태 확인 후 패킷 전송

    async def unsubscribe(self, symbols: list[str], data_type: str) -> None:
        """
        구독 해제.
        { "trnm": "REMOVE", ... }
        """
        # _subscribed에서 제거
        # WS 연결 상태 확인 후 패킷 전송

    async def _handle_ping(self) -> None:
        """서버 PING에 대한 PONG 응답"""
        # Ping 수신 시 { "trnm": "PONG" } 전송

    async def listen(self) -> AsyncIterator[QuoteEvent]:
        """
        이벤트 스트림.
        WS 메시지 수신 → JSON 파싱 → QuoteEvent yield

        메시지 타입:
        - 시세: { "trnm": "PRICE", "data": {...} }
        - 체결: { "trnm": "EXEC", "data": {...} }
        - Ping: { "trnm": "PING" }
        """
        # listen 중 WS 끊김 감지 → exception raise (재연결 로직은 Step 8)

    async def close(self) -> None:
        """연결 종료"""
```

**외부 의존성**:
- websockets (비동기 WS)
- KiwoomAuth (Step 2)
- QuoteEvent (Step 1)

**검증**:
- [ ] WS 연결 성공 후 LOGIN 패킷 수신 확인 (응답 메시지)
- [ ] 종목 구독 후 시세 데이터 수신 (mock 또는 실제)
- [ ] PING/PONG 핸드셰이크 정상 작동
- [ ] listen() generator로 QuoteEvent yield

---

### Step 7 — StateMachine (연결 상태 관리)

**목표**: 연결 상태 추적 및 전환 로깅

**파일 생성**:
- `local_server/broker/kiwoom/state_machine.py`

**주요 구현**:

```python
from enum import Enum

class BrokerState(Enum):
    """
    DISCONNECTED → CONNECTING → AUTHED → SYNCING → READY → DEGRADED

    상태 정의:
    - DISCONNECTED: 초기 상태, 연결 없음
    - CONNECTING: WS 연결 중
    - AUTHED: WS 로그인 완료, 아직 구독 미완료
    - SYNCING: 리컨실리에이션 중 (R4)
    - READY: 정상 작동, 모든 구독 활성, WS 수신 중
    - DEGRADED: 치명적 오류, 신규 주문 차단 (STOP_NEW), 평가 계속
    """
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHED = "authed"
    SYNCING = "syncing"
    READY = "ready"
    DEGRADED = "degraded"

class StateMachine:
    def __init__(self, logger):
        self._state = BrokerState.DISCONNECTED
        self._logger = logger

    @property
    def state(self) -> BrokerState:
        return self._state

    async def transition(self, target: BrokerState) -> None:
        """
        상태 전환 및 로깅.
        FATAL 오류 시 DEGRADED로 강제 전환.
        """
        if target == self._state:
            return  # 상태 변화 없음

        self._logger.info(f"State transition: {self._state.value} → {target.value}")
        self._state = target

    def can_send_order(self) -> bool:
        """신규 주문 가능 여부 (DEGRADED 제외)"""
        return self._state != BrokerState.DEGRADED
```

**외부 의존성**:
- enum (표준 라이브러리)
- 로거 (Step 11에서 주입)

**검증**:
- [ ] 상태 전환 시 로그 기록
- [ ] DEGRADED 상태에서 can_send_order() → False
- [ ] 다른 상태에서 can_send_order() → True

---

### Step 8 — Reconnect + Resubscribe (R3)

**목표**: WS 끊김 시 자동 재연결 및 기존 구독 목록 재등록

**파일 생성/수정**:
- `local_server/broker/kiwoom/websocket.py` — 재작성
- `local_server/broker/kiwoom/connector.py` (신규) — 재연결 로직 분리

**주요 구현**:

```python
class KiwoomConnector:
    """
    WS 연결 + 재연결 로직 (R3).
    지수 백오프: 1s → 5s → 30s (최대 3회)
    """

    def __init__(self, ws: KiwoomWebSocket, state_machine: StateMachine, logger):
        self._ws = ws
        self._state_machine = state_machine
        self._logger = logger
        self._backoff_times = [1, 5, 30]  # 초

    async def connect_with_retry(self) -> None:
        """재연결 시도 (최대 3회)"""
        for attempt, delay in enumerate(self._backoff_times):
            try:
                await self._state_machine.transition(BrokerState.CONNECTING)
                await self._ws.connect()
                await self._state_machine.transition(BrokerState.AUTHED)

                # 기존 구독 목록 재등록 (R3)
                await self._resubscribe_all()
                await self._state_machine.transition(BrokerState.READY)
                return  # 성공
            except Exception as e:
                self._logger.warning(f"Connection attempt {attempt+1} failed: {e}")
                if attempt < len(self._backoff_times) - 1:
                    await asyncio.sleep(delay)

        # 3회 실패 → DEGRADED (R6)
        await self._state_machine.transition(BrokerState.DEGRADED)
        self._logger.error("Connection failed after 3 attempts → DEGRADED")

    async def _resubscribe_all(self) -> None:
        """저장된 구독 목록 재구독"""
        for symbol, data_types in self._ws._subscribed.items():
            for data_type in data_types:
                await self._ws.subscribe([symbol], data_type)
```

**외부 의존성**:
- KiwoomWebSocket (Step 6)
- StateMachine (Step 7)
- asyncio (표준 라이브러리)

**검증**:
- [ ] WS 연결 끊김 감지 후 자동 재연결 시작
- [ ] 첫 시도 실패 후 1초 대기, 재시도
- [ ] 기존 구독 목록(예: ["005930", "000660"]) 자동 재등록
- [ ] 3회 재시도 실패 후 DEGRADED로 전환

---

### Step 9 — Reconciliation (R4)

**목표**: WS 누락 보정을 위해 미체결/잔고/당일체결 REST 조회

**파일 생성**:
- `local_server/broker/kiwoom/reconciler.py`

**주요 구현**:

```python
class Reconciler:
    """
    리컨실리에이션 (R4).
    트리거:
    1. 재접속 직후 (Step 8)
    2. 주문 후 10초 내 접수/체결 미수신
    3. 주기 300초
    """

    def __init__(self, quote: KiwoomQuote, logger):
        self._quote = quote
        self._logger = logger
        self._last_order_time: dict[str, datetime] = {}  # { order_no: time }

    async def reconcile_after_reconnect(self, account_no: str) -> None:
        """
        재접속 직후 리컨실리에이션.
        - 미체결 주문 조회 (list_pending_orders)
        - 잔고 조회 (get_balance)
        - 당일 체결 조회 (list_executed_orders)

        WS로 이미 수신한 이벤트와 비교 → 누락된 것 보정
        """
        self._logger.info("Reconciliation: after reconnect")
        # 상세 구현은 order 관리 모듈(Step 4) 확장 시

    async def monitor_pending_order(self, order_no: str, account_no: str, timeout_sec: int = 10) -> None:
        """
        주문 후 N초 내 접수/체결 미수신 시 REST로 조회.
        """
        self._last_order_time[order_no] = datetime.now()
        await asyncio.sleep(timeout_sec)

        if order_no in self._last_order_time:
            # 아직 event 미수신 → REST 조회로 확인
            self._logger.warning(f"No event for order {order_no} after {timeout_sec}s, checking...")
            # 상세 구현은 order 관리 모듈 확장 시

    async def reconcile_periodic(self, account_no: str, interval_sec: int = 300) -> None:
        """
        주기적 리컨실리에이션 (300초마다).
        배경 태스크로 실행.
        """
        while True:
            await asyncio.sleep(interval_sec)
            self._logger.debug("Periodic reconciliation triggered")
            # 잔고 조회 → WS 이벤트와 비교
```

**외부 의존성**:
- KiwoomQuote (Step 3)
- asyncio, datetime (표준 라이브러리)

**검증**:
- [ ] 재연결 후 `reconcile_after_reconnect()` 호출 (Step 8 통합)
- [ ] 주문 후 10초 내 이벤트 없으면 REST 조회 (mock)
- [ ] 주기 300초마다 잔고 확인

---

### Step 10 — Idempotency (R5) + ErrorClassifier (R6)

**목표**:
- R5: 동일 signal_id 중복 주문 방지
- R6: 키움 에러코드를 RETRYABLE/NON_RETRYABLE/FATAL로 분류

**파일 생성**:
- `local_server/broker/kiwoom/idempotency.py`
- `local_server/broker/kiwoom/error_classifier.py`

**주요 구현**:

```python
# idempotency.py
class SignalIdDeduplicator:
    """
    signal_id 중복 방지 (R5).
    주문 이력(signal_id → order_no)을 메모리/파일에 유지.
    """

    def __init__(self, cache_file: Path):
        self._cache_file = cache_file
        self._orders: dict[str, str] = {}  # { signal_id: order_no }
        self._load_cache()

    def register_order(self, signal_id: str, order_no: str) -> None:
        """신규 주문 등록"""
        if signal_id in self._orders:
            raise ValueError(f"Duplicate signal_id: {signal_id}")
        self._orders[signal_id] = order_no
        self._save_cache()

    def get_order_no(self, signal_id: str) -> str | None:
        """기존 주문번호 조회 (재시도 시)"""
        return self._orders.get(signal_id)

    def _load_cache(self) -> None:
        """파일에서 캐시 로드"""
        if self._cache_file.exists():
            with open(self._cache_file) as f:
                self._orders = json.load(f)

    def _save_cache(self) -> None:
        """파일에 캐시 저장"""
        with open(self._cache_file, 'w') as f:
            json.dump(self._orders, f)


# error_classifier.py
class ErrorClassifier:
    """
    오류 분류 (R6).
    키움 에러코드 → RETRYABLE / NON_RETRYABLE / FATAL
    """

    class ErrorLevel(Enum):
        RETRYABLE = "retryable"          # 재시도 권장
        NON_RETRYABLE = "non_retryable"  # 재시도 무의미
        FATAL = "fatal"                   # 시스템 중단

    # 최소 표준 에러 매핑 (키움 문서 확인 후 확장)
    ERROR_CODES = {
        # RETRYABLE
        "EQ001": ErrorLevel.RETRYABLE,  # 일시 서버 오류
        "EQ002": ErrorLevel.RETRYABLE,  # 타임아웃
        "EQ029": ErrorLevel.RETRYABLE,  # Rate limit 초과

        # NON_RETRYABLE
        "EQ003": ErrorLevel.NON_RETRYABLE,  # 파라미터 오류
        "EQ004": ErrorLevel.NON_RETRYABLE,  # 종목 코드 없음
        "EQ010": ErrorLevel.NON_RETRYABLE,  # 주문 가능 시간 아님

        # FATAL
        "EQ007": ErrorLevel.FATAL,      # 인증 실패
        "EQ008": ErrorLevel.FATAL,      # 토큰 만료
        "EQ030": ErrorLevel.FATAL,      # 계좌 동기화 불가
    }

    @classmethod
    def classify(cls, error_code: str) -> ErrorLevel:
        """에러코드 분류"""
        level = cls.ERROR_CODES.get(error_code)
        if level is None:
            # 미분류 → NON_RETRYABLE (보수적)
            return cls.ErrorLevel.NON_RETRYABLE
        return level
```

**외부 의존성**:
- enum, json, pathlib (표준 라이브러리)

**검증**:
- [ ] 동일 signal_id 두 번째 호출 시 ValueError 발생
- [ ] signal_id → order_no 매핑 파일 저장/로드
- [ ] ErrorClassifier.classify("EQ001") → RETRYABLE
- [ ] ErrorClassifier.classify("EQ003") → NON_RETRYABLE
- [ ] ErrorClassifier.classify("EQ007") → FATAL

---

### Step 11 — KiwoomAdapter 통합 (진입점)

**목표**: 모든 모듈을 통합하여 BrokerAdapter를 구현

**파일 생성**:
- `local_server/broker/kiwoom/adapter.py`

**주요 구현**:

```python
class KiwoomAdapter(BrokerAdapter):
    """
    BrokerAdapter의 키움 구현체.
    6가지 책임(R1~R6)을 모두 통합.
    """

    def __init__(
        self,
        app_key: str,
        secret_key: str,
        is_mock: bool = True,
        logger = None,
    ):
        self._auth = KiwoomAuth(app_key, secret_key, is_mock)
        self._rate_limiter = RateLimiter(rate=5, per_seconds=1.0)  # R1
        self._quote = KiwoomQuote(self._auth, self._rate_limiter)
        self._order = KiwoomOrder(self._auth, self._rate_limiter)
        self._ws = KiwoomWebSocket(self._auth)
        self._state_machine = StateMachine(logger)  # R2
        self._connector = KiwoomConnector(self._ws, self._state_machine, logger)  # R3
        self._reconciler = Reconciler(self._quote, logger)  # R4
        self._deduplicator = SignalIdDeduplicator(Path("dedup_cache.json"))  # R5
        self._error_classifier = ErrorClassifier()  # R6
        self._logger = logger or logging.getLogger(__name__)

    async def authenticate(self) -> None:
        """OAuth 토큰 발급 및 WS 연결"""
        token = await self._auth.get_token()
        await self._connector.connect_with_retry()

    async def is_authenticated(self) -> bool:
        """토큰 유효 + WS 연결 확인"""
        return (
            self._auth._token is not None
            and self._state_machine.state in [BrokerState.READY, BrokerState.SYNCING]
        )

    async def send_order(
        self,
        account_no: str,
        symbol: str,
        side: Literal["BUY", "SELL"],
        qty: int,
        price: int = 0,
        order_type: str = "0",
        signal_id: str | None = None,  # R5 추가
    ) -> OrderResult:
        """
        주문 실행 with idempotency (R5) + error classification (R6)
        """
        # R5: signal_id 중복 확인
        if signal_id:
            existing_order_no = self._deduplicator.get_order_no(signal_id)
            if existing_order_no:
                self._logger.info(f"Order already placed for signal_id {signal_id}: {existing_order_no}")
                return OrderResult(success=True, order_no=existing_order_no, message="Duplicate prevented", raw_response={})

        # 주문 가능 상태 확인
        if not self._state_machine.can_send_order():
            return OrderResult(success=False, order_no=None, message="System degraded", raw_response={})

        # 주문 실행 (rate_limiter 내부 적용)
        result = await self._order.send_order(account_no, symbol, side, qty, price, order_type)

        # R6: 오류 분류
        if not result.success:
            error_code = result.raw_response.get("return_code", "UNKNOWN")
            error_level = self._error_classifier.classify(error_code)

            if error_level == ErrorClassifier.ErrorLevel.FATAL:
                await self._state_machine.transition(BrokerState.DEGRADED)

        # R5: 성공 시 signal_id 등록
        if result.success and signal_id:
            self._deduplicator.register_order(signal_id, result.order_no)

        # R4: 주문 후 10초 내 이벤트 대기 (배경 태스크)
        if result.success:
            asyncio.create_task(
                self._reconciler.monitor_pending_order(result.order_no, account_no, timeout_sec=10)
            )

        return result

    async def cancel_order(self, order_no: str) -> OrderResult:
        """P2 기능, 미구현"""
        raise NotImplementedError("P2")

    async def get_current_price(self, symbol: str) -> int:
        """현재가 조회 (rate_limiter 적용)"""
        return await self._rate_limiter.execute(
            self._quote.get_current_price(symbol)
        )

    async def get_balance(self, account_no: str) -> BalanceResult:
        """잔고 조회 (rate_limiter 적용)"""
        return await self._rate_limiter.execute(
            self._quote.get_balance(account_no)
        )

    async def get_positions(self, account_no: str) -> list[Position]:
        """보유종목 조회"""
        balance = await self.get_balance(account_no)
        return balance.positions

    async def subscribe(self, symbols: list[str], data_type: str) -> None:
        """시세 구독 (WS)"""
        await self._ws.subscribe(symbols, data_type)

    async def unsubscribe(self, symbols: list[str], data_type: str) -> None:
        """시세 구독 해제"""
        await self._ws.unsubscribe(symbols, data_type)

    async def listen(self) -> AsyncIterator[QuoteEvent]:
        """실시간 이벤트 스트림"""
        try:
            async for event in self._ws.listen():
                yield event
        except Exception as e:
            self._logger.error(f"Listen error: {e}")
            await self._connector.connect_with_retry()

    async def start_background_reconciliation(self, account_no: str) -> None:
        """배경 리컨실리에이션 시작 (R4)"""
        asyncio.create_task(self._reconciler.reconcile_periodic(account_no, interval_sec=300))
```

**외부 의존성**:
- 모든 Step 2-10 모듈
- logging (표준 라이브러리)
- asyncio.create_task (배경 태스크)

**검증**:
- [ ] `KiwoomAdapter(app_key, secret).authenticate()` → WS 연결 성공
- [ ] `is_authenticated()` → True (WS 연결 상태)
- [ ] `send_order()` → OrderResult 반환, rate_limiter 적용 확인
- [ ] `listen()` → 이벤트 스트림 yield
- [ ] 모든 abstract 메서드 구현

---

### Step 12 — MockAdapter (테스트용)

**목표**: 단위 테스트 및 통합 테스트용 Mock 구현체

**파일 생성**:
- `local_server/broker/mock_adapter.py`

**주요 구현**:

```python
class MockAdapter(BrokerAdapter):
    """
    테스트용 Mock Adapter.
    실제 API 호출 없이 예정된 응답 반환.
    """

    def __init__(self):
        self._authenticated = False
        self._balance = BalanceResult(
            deposit=10000000,
            total_eval=10000000,
            positions=[]
        )

    async def authenticate(self) -> None:
        self._authenticated = True

    async def is_authenticated(self) -> bool:
        return self._authenticated

    async def send_order(...) -> OrderResult:
        """항상 성공하는 모의 주문"""
        order_no = f"MOCK{datetime.now().timestamp()}"
        return OrderResult(
            success=True,
            order_no=order_no,
            message="Mock order succeeded",
            raw_response={}
        )

    async def cancel_order(self, order_no: str) -> OrderResult:
        return OrderResult(success=True, order_no=order_no, message="Mock cancel", raw_response={})

    async def get_current_price(self, symbol: str) -> int:
        """고정 가격 반환"""
        return 100000  # Mock 가격

    async def get_balance(self, account_no: str) -> BalanceResult:
        return self._balance

    async def get_positions(self, account_no: str) -> list[Position]:
        return self._balance.positions

    async def subscribe(self, symbols: list[str], data_type: str) -> None:
        pass

    async def unsubscribe(self, symbols: list[str], data_type: str) -> None:
        pass

    async def listen(self) -> AsyncIterator[QuoteEvent]:
        """
        주기적으로 Mock 이벤트 yield.
        테스트 시 예정된 시세 데이터 반환.
        """
        while True:
            yield QuoteEvent(
                event_type="quote",
                symbol="005930",
                price=100000,
                volume=1000,
                timestamp=datetime.now(timezone.utc),
                raw_data={}
            )
            await asyncio.sleep(1)
```

**외부 의존성**:
- BrokerAdapter (Step 1)
- BalanceResult, Position, QuoteEvent (Step 1)
- asyncio, datetime (표준 라이브러리)

**검증**:
- [ ] MockAdapter 초기화 가능
- [ ] `authenticate()` → `is_authenticated()` → True
- [ ] `send_order()` → OrderResult.success=True
- [ ] `listen()` → 주기적으로 QuoteEvent yield

---

### Step 13 — Factory + 통합 테스트

**목표**: BrokerAdapter 생성 팩토리 및 전체 통합 테스트

**파일 생성/수정**:
- `local_server/broker/factory.py`
- `tests/test_kiwoom_integration.py` (신규)

**주요 구현**:

```python
# factory.py
def create_broker(
    broker_type: str = "kiwoom",
    config: dict | None = None,
) -> BrokerAdapter:
    """
    설정에 따라 BrokerAdapter 인스턴스 생성.

    config = {
        "app_key": "...",
        "secret_key": "...",
        "is_mock": true/false,
    }
    """
    if broker_type == "kiwoom":
        return KiwoomAdapter(
            app_key=config.get("app_key"),
            secret_key=config.get("secret_key"),
            is_mock=config.get("is_mock", True),
        )
    elif broker_type == "mock":
        return MockAdapter()
    else:
        raise ValueError(f"Unknown broker type: {broker_type}")


# tests/test_kiwoom_integration.py
@pytest.mark.asyncio
async def test_kiwoom_adapter_full_flow():
    """
    전체 흐름 테스트 (Mock 사용).
    1. 인증
    2. 현재가 조회
    3. 주문 실행
    4. 잔고 조회
    """
    adapter = create_broker("mock")

    # 인증
    await adapter.authenticate()
    assert await adapter.is_authenticated()

    # 현재가 조회
    price = await adapter.get_current_price("005930")
    assert price > 0

    # 주문 실행
    result = await adapter.send_order(
        account_no="123456",
        symbol="005930",
        side="BUY",
        qty=10,
        price=100000,
    )
    assert result.success

    # 잔고 조회
    balance = await adapter.get_balance("123456")
    assert balance.deposit > 0

@pytest.mark.asyncio
async def test_kiwoom_rate_limiter():
    """초당 5건 제한 테스트"""
    limiter = RateLimiter(rate=5, per_seconds=1.0)

    start = time.time()
    for _ in range(6):
        await limiter.acquire()
    elapsed = time.time() - start

    # 6번째는 약 1초 이상 대기 필요
    assert elapsed >= 1.0

@pytest.mark.asyncio
async def test_error_classifier():
    """오류 분류 테스트"""
    assert ErrorClassifier.classify("EQ001") == ErrorClassifier.ErrorLevel.RETRYABLE
    assert ErrorClassifier.classify("EQ003") == ErrorClassifier.ErrorLevel.NON_RETRYABLE
    assert ErrorClassifier.classify("EQ007") == ErrorClassifier.ErrorLevel.FATAL
```

**외부 의존성**:
- pytest, pytest-asyncio (테스트)
- 모든 Step 2-12 모듈

**검증**:
- [ ] `create_broker("kiwoom", config)` → KiwoomAdapter 반환
- [ ] `create_broker("mock")` → MockAdapter 반환
- [ ] 통합 테스트 모두 통과 (Mock 기반)
- [ ] Rate Limiter 테스트: 5개 호출 < 1초, 6개 호출 >= 1초

---

## 2. 파일 목록

| 파일 | 변경 | 설명 |
|------|------|------|
| `sv_core/__init__.py` | 신규 | 공유 패키지 진입점 |
| `sv_core/broker/__init__.py` | 신규 | — |
| `sv_core/broker/base.py` | 신규 | BrokerAdapter ABC + 공통 모델 |
| `sv_core/broker/models.py` | 신규 | OrderResult, BalanceResult, Position, QuoteEvent |
| `local_server/__init__.py` | 신규 | — |
| `local_server/broker/__init__.py` | 신규 | — |
| `local_server/broker/factory.py` | 신규 | BrokerAdapter 팩토리 |
| `local_server/broker/mock_adapter.py` | 신규 | Mock 구현체 |
| `local_server/broker/kiwoom/__init__.py` | 신규 | — |
| `local_server/broker/kiwoom/adapter.py` | 신규 | KiwoomAdapter (진입점) |
| `local_server/broker/kiwoom/auth.py` | 신규 | OAuth 토큰 관리 |
| `local_server/broker/kiwoom/quote.py` | 신규 | 현재가/잔고 조회 |
| `local_server/broker/kiwoom/order.py` | 신규 | 주문 실행 |
| `local_server/broker/kiwoom/websocket.py` | 신규 | WS 시세 수신 |
| `local_server/broker/kiwoom/connector.py` | 신규 | 재연결 로직 (R3) |
| `local_server/broker/kiwoom/rate_limiter.py` | 신규 | Token Bucket (R1) |
| `local_server/broker/kiwoom/state_machine.py` | 신규 | 상태 머신 (R2) |
| `local_server/broker/kiwoom/reconciler.py` | 신규 | 리컨실리에이션 (R4) |
| `local_server/broker/kiwoom/idempotency.py` | 신규 | 중복 방지 (R5) |
| `local_server/broker/kiwoom/error_classifier.py` | 신규 | 오류 분류 (R6) |
| `local_server/broker/kiwoom/models.py` | 신규 | 키움 특화 모델 |
| `tests/test_kiwoom_integration.py` | 신규 | 통합 테스트 |
| `requirements.txt` | 수정 | httpx, websockets 추가 |

---

## 3. 의존성 (다른 Unit과의 관계)

### 이 Unit이 제공하는 것 (다운스트림)

1. **Unit 2 — 로컬 서버 코어** (`spec/local-server-core/`)
   - BrokerAdapter 인터페이스 → 전략 엔진이 사용
   - KiwoomAdapter 구현체 → 로컬 서버의 주문/시세 수신

2. **Unit 4 — 클라우드 서버** (`spec/api-server/`)
   - `sv_core/broker/base.py` 공유 → 클라우드 서버도 KiwoomAdapter 사용 가능 (서비스 키)

### 이 Unit이 의존하는 것 (업스트림)

- **외부**: 키움 REST API, WebSocket (API 명세는 spec 8장 참조)
- **내부**: 없음 (독립적)

### 다른 Unit과의 순서

```
Unit 1 (이 Unit) → Unit 2 (로컬 서버) → Unit 3 (전략 엔진) → 통합
```

Unit 1 완료 후 Unit 2에서 로컬 서버 Framework(FastAPI, 라우터)를 구축하고,
Unit 2가 완료되면 Unit 3에서 전략 엔진이 BrokerAdapter를 활용한다.

---

## 4. 미결 사항 처리

spec의 10장 "미결 사항"을 구현 시 처리 방법:

| 미결 사항 | 처리 방법 |
|---------|---------|
| **api-id 전수 목록** | Step 2-4 구현 시 사용하는 api-id만 명시. 부족하면 키움 공식 가이드 참조하여 추가 |
| **토큰 유효 기간** | auth.py에서 24h 가정. 실제 응답의 `expires_in` 필드로 덮어쓰기 |
| **조회/주문 제한 정확한 수치** | Step 5 RateLimiter에 초당 5건으로 구현. 실제 키움 제한 다를 경우 rate 파라미터 조정 |
| **WS type 코드 전수** | Step 6에서 `0B`(실시간 체결가)만 구현. 필요시 확장 |
| **토큰 갱신 실패 시 사용자 알림** | Unit 2(로컬 서버 UI) 통합 시 트레이/WS로 알림. 현 단계는 로그만 |
| **IP 화이트리스트 자동 등록** | 미지원 (사용자가 키움 웹에서 수동 등록) |
| **mockapi.kiwoom.com와 실거래 api-id 동일 여부** | 코드상 베이스 URL만 다르고 api-id는 동일하게 가정. 실제 다를 경우 Step 2-4에서 조건 추가 |
| **오류 코드 매핑표** | Step 10 error_classifier.py에 최소 표준 6개만 구현. 키움 공식 문서 확인 후 확장 |

---

## 5. 커밋 계획

개발 중 매 Step 완료 시 `spec/kiwoom-rest/reports/` 디렉토리에 진행 상황을 기록하되,
**최종 완료 후 일괄 커밋** (workflow.md 준수):

```
Step 1-3:  기반 구조 (패키지, ABC, 인증)
Step 4-6:  핵심 기능 (주문, 조회, WS)
Step 7-10: 안정성 (상태, 재연결, 오류 처리)
Step 11-13: 통합 (Adapter, Mock, Factory, 테스트)
```

일괄 커밋:
```
git add local_server/ sv_core/ tests/ requirements.txt
git commit -m "feat: Unit 1 — 키움 REST API 연동 (BrokerAdapter + 6대 책임)"
```

---

## 6. 예상 일정

| Step | 난이도 | 예상 시간 |
|------|--------|---------|
| 1 (ABC) | ⭐ | 1h |
| 2 (인증) | ⭐⭐ | 2h |
| 3 (조회) | ⭐⭐ | 1.5h |
| 4 (주문) | ⭐⭐ | 1.5h |
| 5 (Rate Limiter) | ⭐ | 1h |
| 6 (WS) | ⭐⭐⭐ | 3h |
| 7 (StateMachine) | ⭐⭐ | 1.5h |
| 8 (Reconnect) | ⭐⭐⭐ | 2h |
| 9 (Reconciliation) | ⭐⭐⭐ | 2h |
| 10 (Idempotency + ErrorClassifier) | ⭐⭐ | 2h |
| 11 (KiwoomAdapter 통합) | ⭐⭐⭐ | 3h |
| 12 (MockAdapter) | ⭐ | 1h |
| 13 (Factory + 테스트) | ⭐⭐ | 2h |
| **합계** | | **~23.5h** |

---

## 7. 성공 기준

- [ ] 모든 Step 구현 완료
- [ ] 단위 테스트: 각 모듈별 기능 검증
- [ ] 통합 테스트: MockAdapter로 full flow 테스트
- [ ] 코드 리뷰: 6대 책임(R1~R6) 모두 구현 확인
- [ ] 문서: 키움 API 제약, 에러 코드 매핑 보완

---

**마지막 갱신**: 2026-03-05
