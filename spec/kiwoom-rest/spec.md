# 증권사 REST API 연동 명세서 (broker-adapter)

> 작성일: 2026-03-04 | 상태: **구현 완료** | Unit 1 (Phase 3-A)
>
> **이전 spec**: `spec/kiwoom-integration/` (COM/pykiwoom 기반) → 폐기.
>
> **결정 (2026-03-07)**: **한국투자증권(KIS) Open API+** 채택.
> BrokerAdapter ABC로 증권사 교체 가능하게 설계, 첫 구현체는 KIS.
> 코드: `local_server/broker/kis/`, 공통: `sv_core/broker/`

---

## 1. 목표

`BrokerAdapter` 인터페이스의 **한국투자증권(KIS) 구현체**(KisAdapter)를 구현한다.
로컬 서버와 클라우드 서버가 이 Adapter를 통해 KIS Open API+ REST/WS에 접근한다.

**해결하는 문제:**
- COM/HTS/32bit Python 의존성 제거
- 64bit Python + asyncio 환경에서 직접 REST/WS 호출
- OAuth 토큰 자동 관리
- 증권사 교체 가능한 구조 (BrokerAdapter ABC 준수)

---

## 2. 요구사항

### 2.1 기능적 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| F1 | App Key/Secret으로 OAuth Bearer Token을 발급한다 | P0 |
| F2 | 토큰 만료 전 자동 갱신한다 | P0 |
| F3 | 시장가/지정가 매수·매도 주문을 실행한다 | P0 |
| F4 | 현재가를 조회한다 (주문 전 가격 검증용) | P0 |
| F5 | 잔고/보유 종목을 조회한다 | P0 |
| F6 | WebSocket으로 실시간 시세를 수신한다 | P0 |
| F7 | WebSocket으로 체결 통보를 수신한다 | P0 |
| F8 | API 호출 제한(초당 20건)을 큐로 관리한다 | P1 |
| F9 | 모의투자/실거래 모드를 전환한다 (베이스 URL 변경) | P1 |
| F10 | 미체결 주문 조회 및 정정/취소를 지원한다 | P2 |

### 2.2 비기능적 요구사항

| 항목 | 목표 |
|------|------|
| 토큰 발급 시간 | < 2초 |
| REST API 호출 지연 | < 500ms (네트워크 제외) |
| WS 시세 수신 지연 | < 100ms |
| 메모리 사용 | < 50MB (클라이언트 모듈 단독) |
| 동시 WS 구독 | 최대 200종목 |

---

## 3. 아키텍처

### 3.1 KIS Open API+ 개요

```
KIS Open API+
├── 포털: https://apiportal.koreainvestment.com
├── REST: https://openapi.koreainvestment.com:9443
│
├── 인증:
│   POST /oauth2/token
│   Body: { grant_type: "client_credentials", appkey, appsecret }
│   → Bearer Token 발급 (24시간 유효)
│
├── 주문:
│   POST /uapi/domestic-stock/v1/trading/order-cash
│   Headers: { tr_id: "TTTC0801U" }  (매수 지정가)
│   → 시장가/지정가 매수·매도
│
├── 조회:
│   GET /uapi/domestic-stock/v1/quotations/inquire-price
│   Headers: { tr_id: "FHKST01010100" }
│   → 현재가 조회
│   GET /uapi/domestic-stock/v1/trading/inquire-balance
│   Headers: { tr_id: "TTTC8434R" }
│   → 잔고/보유종목 조회
│
└── WebSocket: wss://openapi.koreainvestment.com:9443/websocket/tryitout/H0STCNT0
    → 실시간 체결가 (pipe-separated 텍스트 프레임)
```

### 3.2 인증 흐름

```
[로컬 서버] → POST /oauth2/token
  Body: { grant_type: "client_credentials", appkey, appsecret }
  Response: { access_token, token_type, expires_in }
                ↓
[로컬 서버] → 모든 REST 요청 헤더:
  Authorization: Bearer {access_token}
  appkey: {app_key}
  tr_id: {트랜잭션 ID}
  Content-Type: application/json; charset=utf-8
                ↓
[로컬 서버] → 만료 5분 전 자동 갱신
```

### 3.3 모듈 구조

```
sv_core/broker/
├── __init__.py
├── base.py            # BrokerAdapter ABC (증권사 무관)
└── models.py          # OrderResult, BalanceResult, Position, QuoteEvent 등

local_server/broker/
├── __init__.py
├── factory.py         # AdapterFactory → KisAdapter | MockAdapter
├── kis/               # 한국투자증권 구현체
│   ├── adapter.py     # KisAdapter — BrokerAdapter 구현체 (진입점)
│   ├── auth.py        # OAuth 토큰 발급/갱신/캐시
│   ├── order.py       # 주문 실행 (시장가/지정가/정정/취소)
│   ├── quote.py       # 현재가, 잔고, 보유종목 조회
│   ├── ws.py          # WS 실시간 시세 수신
│   ├── rate_limiter.py # 초당 20건 큐 관리 (슬라이딩 윈도우)
│   ├── state_machine.py # 연결 상태 머신
│   ├── reconnect.py   # 지수 백오프 재연결
│   ├── reconciler.py  # 미체결 대사
│   ├── idempotency.py # 주문 멱등성
│   └── error_classifier.py # 오류 분류
└── mock/
    └── adapter.py     # MockAdapter (테스트용)
```

**구조 원칙**: ABC(`sv_core/broker/`)는 증권사 무관. 구현체(`kis/`)만 교체하면 다른 증권사 지원 가능.

### 3.4 KisAdapter 6대 책임

증권사 API 특유의 불안정성(rate limit, 세션 종료, reconnect)을 시스템 레벨에서 흡수하기 위해
KisAdapter는 아래 6가지 책임을 반드시 구현한다.

| # | 책임 | 설명 |
|---|------|------|
| R1 | **중앙 Rate Limiter** | TR/주문 호출이 여러 모듈에서 나가도 한 곳에서 큐잉/슬로틀링. rate_limiter.py가 유일한 게이트. |
| R2 | **연결 상태 머신** | `DISCONNECTED → CONNECTING → AUTHED → SYNCING → READY → DEGRADED`. 상태 전환 시 트레이/로그에 반영. |
| R3 | **재접속 시 재구독** | WS 끊김 → 재연결 성공 시, 기존 구독 목록(종목, type)을 자동 재등록. |
| R4 | **리컨실리에이션** | 미체결/잔고/당일체결을 REST 조회하여 WS 이벤트 누락 보정. Triggers: (a) 재접속 직후, (b) 주문 후 10초 내 접수/체결 미수신, (c) 주기 300초. |
| R5 | **주문 idempotency** | 동일 signal_id 중복 주문 방지. 재시도와 SignalManager 간 충돌 없이 동작. |
| R6 | **오류 분류** | 키움 에러코드를 `RETRYABLE` / `NON_RETRYABLE` / `FATAL`로 분류. 분류 기준은 아래 최소 표준 참조. |

**R6 오류 분류 최소 표준:**

| 등급 | 의미 | 예시 |
|------|------|------|
| **RETRYABLE** | 재시도 가능, 자동 복구 기대 | 일시 네트워크 오류, 타임아웃, rate limit 초과 |
| **NON_RETRYABLE** | 재시도 무의미, 해당 요청만 실패 처리 | 파라미터 오류, 장외 시간 주문, 종목 코드 없음 |
| **FATAL** | 세션/시스템 수준 장애, Trading Enabled=OFF | 인증 실패/갱신 실패, 연속 n회 통신 실패, 계좌 동기화 불가, 주문 결과 불명확 지속 |

- FATAL 발생 시: 상태 머신 → DEGRADED(STOP_NEW), 트레이/로그에 즉시 반영
- RETRYABLE: 지수 백오프(1→2→4초, 최대 3회) 후 실패 시 NON_RETRYABLE로 격상
- 분류 불가 에러코드: NON_RETRYABLE로 기본 처리 + 로그에 미분류 경고

---

## 4. API 상세

### 4.1 토큰 발급 (`kis/auth.py`)

```python
class KisAuth:
    """KIS OAuth 2.0 인증 관리자."""

    def __init__(self, app_key: str, app_secret: str) -> None: ...

    async def get_access_token(self) -> str:
        """유효한 액세스 토큰 반환. 만료 5분 전 자동 갱신 (asyncio.Lock 보호)."""
        ...

    async def _fetch_token(self) -> None:
        """POST /oauth2/token
        Body: { grant_type: "client_credentials", appkey, appsecret }
        Response: { access_token, token_type, expires_in }
        expires_in 기본값: 86400 (24시간)"""
        ...

    async def build_headers(self) -> dict[str, str]:
        """일반 API 요청 헤더: Authorization(Bearer) + appkey + Content-Type."""
        ...

    def invalidate(self) -> None:
        """캐시된 토큰 무효화 (인증 오류 시 호출)."""
        ...
```

### 4.2 주문 실행 (`kis/order.py`)

```python
class KisOrder:
    """KIS 주문 실행/취소/미체결 조회."""

    # tr_id 매핑 (실전투자)
    _ORDER_TR_ID = {
        (BUY, MARKET): "TTTC0802U",  (BUY, LIMIT): "TTTC0801U",
        (SELL, MARKET): "TTTC0801U", (SELL, LIMIT): "TTTC0801U",
    }
    TR_CANCEL = "TTTC0803U"
    TR_OPEN_ORDERS = "TTTC8036R"

    async def place_order(
        self, client_order_id: str, symbol: str,
        side: OrderSide, order_type: OrderType,
        qty: int, limit_price: Optional[Decimal] = None,
    ) -> OrderResult:
        """POST /uapi/domestic-stock/v1/trading/order-cash
        헤더: tr_id, 바디: CANO, ACNT_PRDT_CD, PDNO, ORD_DVSN, ORD_QTY, ORD_UNPR
        응답: { output: { ODNO: 주문번호 } }"""
        ...

    async def cancel_order(self, order_id: str, symbol: str, qty: int) -> OrderResult:
        """POST /uapi/domestic-stock/v1/trading/order-rvsecncl
        헤더: tr_id=TTTC0803U, RVSE_CNCL_DVSN_CD=02 (취소)"""
        ...

    async def get_open_orders(self) -> list[OrderResult]:
        """GET /uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl
        헤더: tr_id=TTTC8036R"""
        ...
```

### 4.3 현재가/잔고 조회 (`kis/quote.py`)

```python
class KisQuote:
    """KIS 시세 및 잔고 조회."""

    TR_PRICE_REAL = "FHKST01010100"  # 현재가 조회
    TR_BALANCE_REAL = "TTTC8434R"    # 잔고 조회

    async def get_price(self, symbol: str) -> QuoteEvent:
        """GET /uapi/domestic-stock/v1/quotations/inquire-price
        헤더: tr_id=FHKST01010100
        파라미터: FID_COND_MRKT_DIV_CODE=J, FID_INPUT_ISCD=종목코드
        응답: { output: { stck_prpr, acml_vol, bidp, askp } }"""
        ...

    async def get_balance(self) -> BalanceResult:
        """GET /uapi/domestic-stock/v1/trading/inquire-balance
        헤더: tr_id=TTTC8434R
        파라미터: CANO, ACNT_PRDT_CD, INQR_DVSN=02 (종목별)
        응답: { output1: [보유종목], output2: [계좌합계] }"""
        ...
```

### 4.4 WebSocket 시세 수신 (`kis/ws.py`)

```python
class KisWS:
    """KIS WebSocket 실시간 체결/시세 스트림."""

    WS_URL = "wss://openapi.koreainvestment.com:9443/websocket/tryitout/H0STCNT0"
    TR_SUBSCRIBE = "H0STCNT0"  # 주식 체결가

    async def connect(self) -> None:
        """WebSocket 연결 (ping_interval=30s, ping_timeout=10s).
        연결 후 _recv_loop 태스크 시작."""
        ...

    async def subscribe(self, symbols: list[str]) -> None:
        """종목 구독. JSON 메시지:
        { header: { approval_key, custtype: "P", tr_type: "1" },
          body: { input: { tr_id: "H0STCNT0", tr_key: "005930" } } }"""
        ...

    async def unsubscribe(self, symbols: list[str]) -> None:
        """구독 해제 (tr_type: "2")"""
        ...

    def _handle_realtime_data(self, raw_msg: str) -> None:
        """실시간 데이터 파싱. 형식: "{tr_id}|{종목코드}|{필드수}|{데이터}"
        데이터는 '^'로 구분된 필드:
          [0]=종목코드, [2]=체결시간, [7]=매도호가, [8]=매수호가,
          [10]=현재가, [12]=누적거래량"""
        ...
```

### 4.5 Rate Limiter (`kis/rate_limiter.py`)

```python
class MultiEndpointRateLimiter:
    """슬라이딩 윈도우. 초당 20건 제한 (KIS 기본값)."""

    def __init__(self, calls_per_second: int = 20): ...

    async def acquire(self) -> None:
        """호출 권한 획득. 1초 내 호출 수가 limit 이상이면 대기."""
        ...
```

---

## 5. 데이터 모델

### 5.1 공통 모델 (`sv_core/broker/models.py`)

모든 BrokerAdapter 구현체가 반환하는 공통 데이터 클래스.
가격은 `Decimal`, 원본 응답은 `raw`에 보존.

```python
class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class OrderStatus(str, Enum):
    NEW = "NEW"
    SUBMITTED = "SUBMITTED"
    PARTIAL_FILLED = "PARTIAL_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class ErrorCategory(str, Enum):
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    RATE_LIMIT = "RATE_LIMIT"
    AUTH = "AUTH"
    UNKNOWN = "UNKNOWN"

@dataclass
class OrderResult:
    order_id: str                        # 브로커 주문 ID
    client_order_id: str                 # 클라이언트 주문 ID (멱등성 키)
    symbol: str
    side: OrderSide
    order_type: OrderType
    qty: int
    limit_price: Optional[Decimal]       # 시장가면 None
    status: OrderStatus
    filled_qty: int = 0
    filled_avg_price: Optional[Decimal] = None
    submitted_at: Optional[datetime] = None
    raw: dict = field(default_factory=dict)

@dataclass
class BalanceResult:
    cash: Decimal                        # 현금 잔고
    total_eval: Decimal                  # 총 평가 금액
    positions: list["Position"] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

@dataclass
class Position:
    symbol: str
    qty: int
    avg_price: Decimal
    current_price: Decimal
    eval_amount: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_rate: Decimal         # %

@dataclass
class QuoteEvent:
    symbol: str
    price: Decimal
    volume: int
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    timestamp: Optional[datetime] = None
    raw: dict = field(default_factory=dict)
```

### 5.2 BrokerAdapter ABC (`sv_core/broker/base.py`)

```python
class BrokerAdapter(ABC):
    """증권사 API 추상 인터페이스. 모든 구현체가 준수."""

    # 라이프사이클
    @abstractmethod
    async def connect(self) -> None: ...
    @abstractmethod
    async def disconnect(self) -> None: ...
    @property
    @abstractmethod
    def is_connected(self) -> bool: ...

    # 잔고/시세 조회
    @abstractmethod
    async def get_balance(self) -> BalanceResult: ...
    @abstractmethod
    async def get_quote(self, symbol: str) -> QuoteEvent: ...

    # 실시간 구독
    @abstractmethod
    async def subscribe_quotes(self, symbols: list[str], callback: Callable) -> None: ...
    @abstractmethod
    async def unsubscribe_quotes(self, symbols: list[str]) -> None: ...

    # 주문
    @abstractmethod
    async def place_order(
        self, client_order_id: str, symbol: str,
        side: OrderSide, order_type: OrderType,
        qty: int, limit_price: Optional[Decimal] = None,
    ) -> OrderResult: ...
    @abstractmethod
    async def cancel_order(self, order_id: str) -> OrderResult: ...
    @abstractmethod
    async def get_open_orders(self) -> list[OrderResult]: ...
```

---

## 6. 수용 기준

### 6.1 인증

- [ ] App Key/Secret으로 Bearer Token 발급 성공
- [ ] 토큰 만료 5분 전 자동 갱신
- [ ] 모의투자/실거래 베이스 URL 전환

### 6.2 주문

- [ ] 모의투자 시장가 매수 10주 → 주문번호 수신
- [ ] 모의투자 지정가 매도 → 주문번호 수신
- [ ] 잔고 부족 시 에러 메시지 정상 반환
- [ ] 초당 20건 이내 호출 준수

### 6.3 조회

- [ ] 현재가 조회 → Decimal 가격 반환
- [ ] 잔고 조회 → 예수금 + 보유종목 반환

### 6.4 WebSocket

- [ ] WS 연결 성공 후 종목 구독 → 실시간 체결가 수신
- [ ] 주문 체결 통보 수신
- [ ] 연결 끊김 시 자동 재연결 (3회, 지수 백오프)
- [ ] 재연결 성공 시 기존 구독 목록 자동 재등록 (R3)

### 6.5 Adapter 책임

- [ ] 모든 REST 호출이 단일 RateLimiter를 경유 (직접 호출 경로 없음, R1)
- [ ] 상태 머신 전환 시 로그 기록 (DISCONNECTED→...→READY→DEGRADED, R2)
- [ ] 리컨실리에이션: 미체결/잔고/당일체결 조회로 WS 누락 보정 (R4)
- [ ] reconcile 트리거: 재접속 직후, 주문 후 10초 미수신, 주기 300초
- [ ] 동일 signal_id 중복 주문 전송 불가 (R5)
- [ ] 오류 분류별 처리: RETRYABLE→지수 백오프 재시도, NON_RETRYABLE→실패 처리, FATAL→DEGRADED(STOP_NEW) (R6)

---

## 7. 범위

### 포함

- `sv_core/broker/base.py` — BrokerAdapter ABC
- `sv_core/broker/models.py` — 공통 데이터 모델
- `local_server/broker/factory.py` — 팩토리
- `local_server/broker/kis/` — KisAdapter 구현체 (OAuth, REST, WS, Rate Limiter)
- `local_server/broker/mock/` — MockAdapter (테스트용)

### 미포함

- 다른 증권사 Adapter (v3+ 확장)
- 프론트엔드 UI (Unit 5)
- 전략 엔진 연동 (Unit 3)
- 로컬 서버 기반 구조 (Unit 2)
- 클라우드 서버 시세 수집 (Unit 4 — 이 모듈 재사용)

---

## 8. KIS Open API+ 제약

| 항목 | 제약 |
|------|------|
| 인증 | Bearer Token (`POST /oauth2/token`, client_credentials) |
| REST URL | `https://openapi.koreainvestment.com:9443` |
| WS URL | `wss://openapi.koreainvestment.com:9443/websocket/tryitout/{tr_id}` |
| 조회/주문 제한 | 초당 20회 (REST), 일 100,000회 |
| 토큰 유효기간 | 24시간 (expires_in 필드로 확인) |
| WS 데이터 형식 | pipe(`\|`) + caret(`^`) 구분 텍스트 |
| 거래 시간 | 평일 09:00~15:30 KST |
| HTS 불필요 | REST API는 HTS 설치/로그인 불필요 |
| 종목코드 형식 | `005930` (6자리) |
| tr_id 방식 | 헤더 `tr_id`로 트랜잭션 구분 |

---

## 9. 기존 spec과의 관계

| 기존 | 상태 |
|------|------|
| `spec/kiwoom-integration/` | **폐기** — COM/pykiwoom/32bit 기반, REST API로 대체 |
| `spec/local-bridge/` | Unit 2로 이전, 키움 관련 부분은 본 spec으로 |

---

## 10. 미결 사항

- [x] ~~REST API 정확한 엔드포인트 URL 확인~~ → KIS Open API+ 확인 완료 (§3.1)
- [x] ~~WebSocket 바이너리 vs 텍스트 프레임 형식 확인~~ → pipe+caret 구분 텍스트 프레임
- [x] ~~리컨실리에이션 트리거 조합~~ → 재접속 직후 / 주문 후 10초 미수신 / 주기 300초 (§3.4 R4)
- [x] ~~DEGRADED 상태에서의 엔진 정책~~ → STOP_NEW (평가 계속, 주문 차단)
- [x] ~~오류 분류 최소 표준~~ → RETRYABLE/NON_RETRYABLE/FATAL 3등급 + 처리 정책 (§3.4 R6)
- [ ] KIS 모의투자 전용 tr_id 확인 (실전과 다를 수 있음 — 공식 문서 확인 필요)
- [ ] WS 체결 통보 tr_id 확인 (H0STCNI0 등)
- [ ] 토큰 갱신 실패 시 사용자 알림 방식 (트레이? WS?)
- [ ] 오류 분류 매핑표: KIS rt_cd / msg_cd별 구체적 분류 (공식 문서 확인 후 작성)

---

## 참고

- [한국투자증권 KIS Developers](https://apiportal.koreainvestment.com)
- `docs/architecture.md` §4.4 (BrokerAdapter), §4.5 (로컬 서버), §5.2 (키 분리)
- `docs/development-plan-v2.md` Unit 1

---

**마지막 갱신**: 2026-03-07
