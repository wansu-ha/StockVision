# 키움 REST API 연동 명세서 (kiwoom-rest)

> 작성일: 2026-03-04 | 상태: 초안 | Unit 1 (Phase 3-A)
>
> **이전 spec**: `spec/kiwoom-integration/` (COM/pykiwoom 기반) → 폐기.
> 키움증권이 2025년 REST API를 공개하여 COM/HTS/32bit 제약 전부 해소됨.

---

## 1. 목표

`BrokerAdapter` 인터페이스의 **키움증권 구현체**(KiwoomAdapter)를 구현한다.
로컬 서버와 클라우드 서버가 이 Adapter를 통해 키움 REST/WS API에 접근한다.

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
| F8 | API 호출 제한(초당 5건)을 큐로 관리한다 | P1 |
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

### 3.1 키움 REST API 개요

```
키움 REST API
├── 포털: https://openapi.kiwoom.com
├── REST (실거래): https://openapi.kiwoom.com
├── REST (모의투자): https://mockapi.kiwoom.com
├── 데이터 API: https://api.kiwoom.com
│
├── 인증:
│   POST /v1/auth/login  (api-id: au10001)
│   → Bearer Token 발급
│
├── 주문:
│   POST /v1/order  (api-id: kt10000)
│   → 시장가/지정가 매수·매도
│
├── 조회:
│   GET /v1/account/balance
│   → 잔고/보유종목 조회
│   GET /api/dostk/chart  (api.kiwoom.com, api-id: ka10080)
│   → 시세/차트 데이터
│   GET (api-id: ka10001)
│   → 기본 종목 정보
│
└── WebSocket: wss://api.kiwoom.com:10000/api/dostk/websocket
    → 실시간 시세, 체결 통보 (JSON 텍스트 프레임)
```

> **참고**: `api-id` 헤더가 한국투자증권의 `tr_id`에 해당하는 TR 코드 역할을 한다.

### 3.2 인증 흐름

```
[로컬 서버] → POST /v1/auth/login
  Headers: { api-id: "au10001", Content-Type: "application/json" }
  Body: { app_key, secret_key }
  Response: { access_token, ... }
                ↓
[로컬 서버] → 모든 REST 요청 헤더:
  Authorization: Bearer {access_token}
  api-id: {tr코드}
  Content-Type: application/json
                ↓
[로컬 서버] → 만료 전 자동 갱신
```

### 3.3 모듈 구조

```
local_server/broker/
├── __init__.py
├── base.py            # BrokerAdapter ABC + 공통 모델 (OrderResult, BalanceResult, ...)
├── factory.py         # create_broker(config) → BrokerAdapter 인스턴스
└── kiwoom/
    ├── __init__.py
    ├── adapter.py     # KiwoomAdapter — BrokerAdapter 구현체 (진입점)
    ├── auth.py        # OAuth 토큰 발급/갱신/캐시
    ├── order.py       # 주문 실행 (시장가/지정가/정정/취소)
    ├── quote.py       # 현재가, 잔고, 보유종목 조회
    ├── websocket.py   # WS 시세 수신 + 체결 통보
    ├── rate_limiter.py # 초당 5건 큐 관리 (Token Bucket, 단일 관문)
    ├── state_machine.py # 연결 상태 머신 (DISCONNECTED→...→READY→DEGRADED)
    └── error_classifier.py # 오류 분류 (RETRYABLE / NON_RETRYABLE / FATAL)
```

**핵심 변경**: 기존 `local_server/kiwoom/` → `local_server/broker/kiwoom/`으로 이동.
공통 인터페이스(`base.py`)와 팩토리(`factory.py`)를 상위에 배치.

### 3.4 KiwoomAdapter 6대 책임

키움 API 특유의 불안정성(rate limit, 세션 종료, reconnect)을 시스템 레벨에서 흡수하기 위해
KiwoomAdapter는 아래 6가지 책임을 반드시 구현한다.

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

### 4.1 토큰 발급

```python
class KiwoomAuth:
    def __init__(self, app_key: str, secret_key: str, is_mock: bool = True):
        self._base_url = (
            "https://mockapi.kiwoom.com"      # 모의투자
            if is_mock else
            "https://openapi.kiwoom.com"       # 실거래
        )
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    async def get_token(self) -> str:
        """유효한 토큰 반환. 만료 임박 시 자동 갱신."""
        if self._is_token_valid():
            return self._token
        return await self._refresh_token()

    async def _refresh_token(self) -> str:
        """POST /v1/auth/login (api-id: au10001) → Bearer Token 발급"""
        ...
```

### 4.2 주문 실행

```python
class KiwoomOrder:
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
        POST /v1/order  (api-id: kt10000)
        params:
          dmst_stex_tp: 거래소 (KRX / NXT / SOR)
          stk_cd: 종목코드
          ord_qty: 주문수량
          ord_uv: 주문단가 (시장가면 0)
          trde_tp: 주문유형 (0=지정가, 3=시장가)
        Response: { ord_no, return_code, return_msg }
        """
        ...
```

### 4.3 현재가/잔고 조회

```python
class KiwoomQuote:
    async def get_current_price(self, symbol: str) -> int:
        """
        기본 종목 정보 (api-id: ka10001)
        또는 차트 데이터 (api-id: ka10080, api.kiwoom.com)
        → 현재가 반환. 주문 전 가격 검증에 사용.
        """
        ...

    async def get_balance(self, account_no: str) -> BalanceResult:
        """
        GET /v1/account/balance
        → 예수금, 보유종목 목록 반환
        """
        ...
```

### 4.4 WebSocket 시세 수신

```python
class KiwoomWebSocket:
    WS_URL = "wss://api.kiwoom.com:10000/api/dostk/websocket"

    async def connect(self):
        """
        WebSocket 연결 + 인증.
        연결 후 LOGIN 패킷 전송:
          { "trnm": "LOGIN", "token": access_token }
        """
        ...

    async def subscribe(self, symbols: list[str], data_type: str = "0B"):
        """
        실시간 시세 구독.
        { "trnm": "REG", "grp_no": "1",
          "data": [{"item": ["005930","000660"], "type": ["0B"]}] }

        0B: 실시간 체결가
        (기타 type 코드는 공식 문서 확인 필요)
        """
        ...

    async def unsubscribe(self, symbols: list[str], data_type: str):
        """
        구독 해제.
        { "trnm": "REMOVE", ... }
        """
        ...

    async def _handle_ping(self, message: dict):
        """서버 PING에 대한 PONG 응답 (keepalive)"""
        ...

    async def listen(self) -> AsyncIterator[QuoteEvent]:
        """
        이벤트 스트림. JSON 텍스트 프레임을 파싱하여 yield.
        1시간 무활동 시 자동 연결 종료 → 재연결 로직 필요.
        """
        ...
```

### 4.5 Rate Limiter

```python
class RateLimiter:
    """Token Bucket 알고리즘. 초당 5건 제한."""

    def __init__(self, rate: int = 5, per_seconds: float = 1.0):
        self._rate = rate
        self._per = per_seconds
        self._queue: asyncio.Queue = asyncio.Queue()

    async def acquire(self):
        """호출 권한 획득. 제한 초과 시 대기."""
        ...

    async def execute(self, coro):
        """rate limit 적용하여 코루틴 실행."""
        await self.acquire()
        return await coro
```

---

## 5. 데이터 모델

### 5.1 공통 모델 (`broker/base.py`)

모든 BrokerAdapter 구현체가 반환하는 공통 데이터 클래스.
증권사별 원본 응답은 `raw_response`/`raw_data`에 보존.

```python
@dataclass
class OrderResult:
    success: bool
    order_no: str | None       # 주문번호
    message: str               # 성공/실패 메시지
    raw_response: dict         # 증권사 원본 응답

@dataclass
class BalanceResult:
    deposit: int               # 예수금
    total_eval: int            # 총평가금액
    positions: list[Position]  # 보유종목 목록

@dataclass
class Position:
    symbol: str
    name: str
    qty: int
    avg_price: int
    current_price: int
    pnl: int                   # 평가손익
    pnl_rate: float            # 수익률 %

@dataclass
class QuoteEvent:
    event_type: str            # "quote" | "execution" | "order_status"
    symbol: str
    price: int
    volume: int | None
    timestamp: datetime
    raw_data: dict
```

### 5.2 BrokerAdapter ABC (`broker/base.py`)

```python
class BrokerAdapter(ABC):
    """증권사 API 추상 인터페이스. 모든 구현체가 준수."""

    @abstractmethod
    async def authenticate(self) -> None: ...

    @abstractmethod
    async def is_authenticated(self) -> bool: ...

    @abstractmethod
    async def send_order(
        self, account_no: str, symbol: str,
        side: Literal["BUY", "SELL"], qty: int,
        price: int = 0, order_type: str = "market",
    ) -> OrderResult: ...

    @abstractmethod
    async def cancel_order(self, order_no: str) -> OrderResult: ...

    @abstractmethod
    async def get_current_price(self, symbol: str) -> int: ...

    @abstractmethod
    async def get_balance(self, account_no: str) -> BalanceResult: ...

    @abstractmethod
    async def get_positions(self, account_no: str) -> list[Position]: ...

    @abstractmethod
    async def subscribe(self, symbols: list[str], data_type: str) -> None: ...

    @abstractmethod
    async def unsubscribe(self, symbols: list[str], data_type: str) -> None: ...

    @abstractmethod
    async def listen(self) -> AsyncIterator[QuoteEvent]: ...
```

---

## 6. 수용 기준

### 6.1 인증

- [ ] App Key/Secret으로 Bearer Token 발급 성공
- [ ] 토큰 만료 1시간 전 자동 갱신
- [ ] 모의투자/실거래 베이스 URL 전환

### 6.2 주문

- [ ] 모의투자 시장가 매수 10주 → 주문번호 수신
- [ ] 모의투자 지정가 매도 → 주문번호 수신
- [ ] 잔고 부족 시 에러 메시지 정상 반환
- [ ] 초당 5건 이내 호출 준수

### 6.3 조회

- [ ] 현재가 조회 → 정수 가격 반환
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

- `local_server/broker/base.py` — BrokerAdapter ABC + 공통 모델
- `local_server/broker/factory.py` — 팩토리
- `local_server/broker/kiwoom/` — KiwoomAdapter 구현체 (OAuth, REST, WS, Rate Limiter)

### 미포함

- 다른 증권사 Adapter (v3+ 확장)
- 프론트엔드 UI (Unit 5)
- 전략 엔진 연동 (Unit 3)
- 로컬 서버 기반 구조 (Unit 2)
- 클라우드 서버 시세 수집 (Unit 4 — 이 모듈 재사용)

---

## 8. 키움 REST API 제약

| 항목 | 제약 |
|------|------|
| 인증 | Bearer Token (POST /v1/auth/login) |
| 실거래 URL | `https://openapi.kiwoom.com` |
| 모의투자 URL | `https://mockapi.kiwoom.com` |
| 데이터 API | `https://api.kiwoom.com` |
| WS URL | `wss://api.kiwoom.com:10000/api/dostk/websocket` |
| 조회/주문 제한 | 초당/분당 제한 (정확한 수치는 공식 문서 확인 필요) |
| WS 타임아웃 | 1시간 무활동 시 자동 종료 |
| 모의투자 | 별도 URL, 동일 api-id |
| 거래 시간 | 평일 09:00~15:30 KST |
| HTS 불필요 | REST API는 HTS 설치/로그인 불필요 |
| 종목코드 형식 | KRX: `005930`, NXT: `005930_NX` |

---

## 9. 기존 spec과의 관계

| 기존 | 상태 |
|------|------|
| `spec/kiwoom-integration/` | **폐기** — COM/pykiwoom/32bit 기반, REST API로 대체 |
| `spec/local-bridge/` | Unit 2로 이전, 키움 관련 부분은 본 spec으로 |

---

## 10. 미결 사항

- [x] ~~키움 REST API 정확한 엔드포인트 URL 확인~~ → 3차 소스 기반 확인 완료 (§3.1)
- [x] ~~WebSocket 바이너리 vs 텍스트 프레임 형식 확인~~ → JSON 텍스트 프레임
- [ ] api-id(TR 코드) 전수 목록 확인 (공식 가이드 로그인 필요)
- [ ] 토큰 유효 기간 정확한 확인 (24h? 다른 값?)
- [ ] 조회/주문 제한 정확한 수치 (초당 N건, 분당 M건)
- [ ] WS 실시간 type 코드 전수 확인 (0B 외 호가, 체결 통보 등)
- [ ] 토큰 갱신 실패 시 사용자 알림 방식 (트레이? WS?)
- [ ] IP 화이트리스트 자동 등록 가능 여부
- [ ] 모의투자(mockapi.kiwoom.com)와 실거래의 api-id 동일 여부 확인
- [x] ~~리컨실리에이션 트리거 조합~~ → 재접속 직후 / 주문 후 10초 미수신 / 주기 300초 (§3.4 R4)
- [x] ~~DEGRADED 상태에서의 엔진 정책~~ → STOP_NEW (평가 계속, 주문 차단)
- [x] ~~오류 분류 최소 표준~~ → RETRYABLE/NON_RETRYABLE/FATAL 3등급 + 처리 정책 (§3.4 R6)
- [ ] 오류 분류 매핑표: 키움 에러코드별 구체적 분류 (공식 문서 확인 후 작성)

---

## 참고

- [키움 REST API 공식 포털](https://openapi.kiwoom.com)
- `docs/architecture.md` §4.4 (BrokerAdapter), §4.5 (로컬 서버), §5.2 (키 분리)
- `docs/development-plan-v2.md` Unit 1

---

**마지막 갱신**: 2026-03-05
