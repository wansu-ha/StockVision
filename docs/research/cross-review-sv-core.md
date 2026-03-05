# sv_core 패키지 교차 정합성 리뷰

검토일: 2026-03-05

## 1. 검토 대상 파일

| 유닛 | 역할 | 경로 |
|------|------|------|
| Unit 1 (정본) | 키움 REST API 구현체 워크트리 | `.claude/worktrees/agent-a574e260/sv_core/broker/base.py` |
| Unit 1 (정본) | 데이터 모델 | `.claude/worktrees/agent-a574e260/sv_core/broker/models.py` |
| Unit 2 (stub) | 로컬 서버 코어 워크트리 | `.claude/worktrees/agent-a643a319/sv_core/broker/base.py` |
| Unit 4 (stub) | 클라우드 서버 (main 브랜치) | `sv_core/broker/base.py` |
| Unit 4 (추가) | 클라우드 서버 모델 stub | `sv_core/models/quote.py` |

---

## 2. BrokerAdapter ABC 메서드 시그니처 비교표

### 2-1. 라이프사이클 / 인증

| 메서드 | Unit 1 정본 | Unit 2 stub | Unit 4 stub |
|--------|------------|------------|------------|
| `connect() -> None` | `async def connect(self) -> None` | **없음** | **없음** |
| `disconnect() -> None` | `async def disconnect(self) -> None` | **없음** | **없음** |
| `is_connected: bool` | `@property @abstractmethod is_connected(self) -> bool` | **없음** | **없음** |
| `authenticate() -> None` | **없음** | `async def authenticate(self) -> None` | `async def authenticate(self) -> None` |
| `is_authenticated() -> bool` | **없음** | `async def is_authenticated(self) -> bool` | `async def is_authenticated(self) -> bool` |

### 2-2. 잔고 / 포지션

| 메서드 | Unit 1 정본 | Unit 2 stub | Unit 4 stub |
|--------|------------|------------|------------|
| `get_balance() -> BalanceResult` | `async def get_balance(self) -> BalanceResult` | `async def get_balance(self, account_no: str) -> dict[str, Any]` | `async def get_balance(self, account_no: str) -> dict` |
| `get_positions()` | **없음 (BalanceResult.positions로 통합)** | `async def get_positions(self, account_no: str) -> list[dict[str, Any]]` | `async def get_positions(self, account_no: str) -> list[dict]` |

### 2-3. 시세 조회

| 메서드 | Unit 1 정본 | Unit 2 stub | Unit 4 stub |
|--------|------------|------------|------------|
| `get_quote(symbol) -> QuoteEvent` | `async def get_quote(self, symbol: str) -> QuoteEvent` | `async def get_current_price(self, symbol: str) -> int` | `async def get_current_price(self, symbol: str) -> int` |
| `subscribe_quotes(symbols, callback)` | `async def subscribe_quotes(self, symbols: list[str], callback: Callable[[QuoteEvent], None]) -> None` | `async def subscribe(self, symbols: list[str], data_type: str) -> None` | `async def subscribe(self, symbols: list[str], data_type: str) -> None` |
| `unsubscribe_quotes(symbols)` | `async def unsubscribe_quotes(self, symbols: list[str]) -> None` | `async def unsubscribe(self, symbols: list[str], data_type: str) -> None` | `async def unsubscribe(self, symbols: list[str], data_type: str) -> None` |
| `listen() -> AsyncIterator` | **없음** | `async def listen(self) -> AsyncIterator[dict[str, Any]]` | `async def listen(self) -> AsyncIterator` |

### 2-4. 주문

| 메서드 | Unit 1 정본 | Unit 2 stub | Unit 4 stub |
|--------|------------|------------|------------|
| `place_order(client_order_id, symbol, side, order_type, qty, limit_price) -> OrderResult` | `async def place_order(self, client_order_id: str, symbol: str, side: OrderSide, order_type: OrderType, qty: int, limit_price: Optional[Decimal] = None) -> OrderResult` | `async def send_order(self, **kwargs: Any) -> dict[str, Any]` | **없음** |
| `cancel_order(order_id) -> OrderResult` | `async def cancel_order(self, order_id: str) -> OrderResult` | `async def cancel_order(self, order_no: str) -> dict[str, Any]` | **없음** |
| `get_open_orders() -> list[OrderResult]` | `async def get_open_orders(self) -> list[OrderResult]` | **없음** | **없음** |

---

## 3. 데이터 모델 비교

### 3-1. QuoteEvent

| 필드 | Unit 1 정본 (`sv_core.broker.models`) | Unit 4 stub (`sv_core.models.quote`) |
|------|---------------------------------------|--------------------------------------|
| `symbol: str` | `str` | `str` |
| `price` | `Decimal` | `int` (원 단위) |
| `volume: int` | `int` | `int` |
| `timestamp` | `Optional[datetime]` | `datetime` (필수) |
| `bid_price` | `Optional[Decimal]` (필드명: `bid_price`) | `int \| None` (필드명: `bid`) |
| `ask_price` | `Optional[Decimal]` (필드명: `ask_price`) | `int \| None` (필드명: `ask`) |
| `raw: dict` | `dict` (default_factory=dict) | **없음** |

### 3-2. Unit 2 stub에 없는 모델

Unit 2 stub (`agent-a643a319/sv_core/`)에는 `models.py` 파일 자체가 없다.
`OrderResult`, `BalanceResult`, `Position`, `OrderSide`, `OrderType`, `OrderStatus`, `ErrorCategory` 모두 미정의.

### 3-3. Unit 4 stub의 모델 위치

Unit 4는 `sv_core/models/quote.py`에 `QuoteEvent`만 정의한다.
Unit 1 정본은 `sv_core/broker/models.py`에 모든 모델을 정의한다.
**모듈 경로 자체가 다르다.**

---

## 4. import 경로 불일치

### 4-1. cloud_server에서 사용 중인 import

```python
# cloud_server/collector/kiwoom_collector.py
from sv_core.broker.base import BrokerAdapter        # 경로 OK (정본과 일치)
from sv_core.models.quote import QuoteEvent          # Critical: 정본에는 sv_core.models 없음

# cloud_server/services/market_repository.py
from sv_core.models.quote import QuoteEvent          # Critical: 위와 동일

# cloud_server/core/broker_factory.py
from sv_core.broker.base import BrokerAdapter        # 경로 OK
from sv_core.broker.kiwoom import KiwoomAdapter      # 정본 구현 후 유효할 경로 (OK)
```

정본(Unit 1)은 `QuoteEvent`를 `sv_core.broker.models`에 정의한다.
Unit 4 cloud_server는 `sv_core.models.quote`에서 import한다.
**이 두 경로는 완전히 다르다. 정본 병합 시 cloud_server가 즉시 ImportError로 실패한다.**

### 4-2. Unit 2 local_server에서의 sv_core 사용

`local_server/` 코드는 Python 파일에서 `sv_core`를 직접 import하지 않는다.
`local_server/routers/trading.py`의 `place_order`는 `# TODO: Unit 1 BrokerAdapter.send_order() 연동` 주석만 있고 실제 import 없음.
`local_server/pyinstaller.spec`에서 패키지 번들링용 경로 참조만 존재.
**Unit 2 local_server는 현재 sv_core를 직접 import하지 않으므로 런타임 충돌 없음. 단, TODO 연동 시 정본 인터페이스를 따라야 한다.**

---

## 5. 불일치 항목 목록

### Critical (정본 병합 시 즉시 실패)

| # | 항목 | 위치 | 상세 |
|---|------|------|------|
| C1 | `QuoteEvent` import 경로 불일치 | `cloud_server/collector/kiwoom_collector.py:11`, `cloud_server/services/market_repository.py:13` | `sv_core.models.quote.QuoteEvent` 사용 중. 정본은 `sv_core.broker.models.QuoteEvent`. 정본 병합 시 `ImportError` 발생. |
| C2 | `QuoteEvent.price` 타입 불일치 | `sv_core/models/quote.py` vs `sv_core/broker/models.py` | Unit 4 stub: `int` (원 단위). 정본: `Decimal`. `market_repository.py`는 `event.price`를 숫자 비교(`>`, `<`)에 사용 — Decimal은 비교 가능하나 DB 컬럼 타입 호환 확인 필요. |
| C3 | `QuoteEvent` 필드명 불일치 (`bid`/`ask` vs `bid_price`/`ask_price`) | `sv_core/models/quote.py` vs `sv_core/broker/models.py` | stub: `bid`, `ask`. 정본: `bid_price`, `ask_price`. 접근 코드에서 `AttributeError` 발생 가능. |
| C4 | `BrokerAdapter.get_balance()` 시그니처 불일치 | Unit 2/4 stub vs Unit 1 정본 | stub: `get_balance(account_no: str) -> dict`. 정본: `get_balance() -> BalanceResult`. `account_no` 파라미터 없음, 반환 타입 다름. `broker_factory.py`의 `_KiwoomStub.get_balance(account_no)` 정본 ABC와 충돌. |
| C5 | `_KiwoomStub`이 정본 ABC 구현 불가 | `cloud_server/core/broker_factory.py:40-72` | stub의 ABC는 `authenticate`, `is_authenticated`, `get_balance(account_no)` 등을 요구. 정본 ABC는 `connect`, `disconnect`, `is_connected`, `place_order`, `get_open_orders` 등을 요구. 정본으로 교체 시 `_KiwoomStub`가 미구현 abstractmethod로 인해 인스턴스 생성 불가. |

### Medium (기능 누락 또는 설계 차이)

| # | 항목 | 위치 | 상세 |
|---|------|------|------|
| M1 | `get_positions()` 독립 메서드 vs `BalanceResult.positions` 통합 | Unit 2/4 stub vs 정본 | stub은 `get_positions(account_no)`를 별도 메서드로 정의. 정본은 `get_balance() -> BalanceResult`에 `positions` 필드로 통합. 로직 분기점이 다름. |
| M2 | 인증 메서드명 불일치 (`authenticate` vs `connect`) | Unit 2/4 vs Unit 1 | stub: `authenticate() + is_authenticated()`. 정본: `connect() + is_connected` (property). 의미론적으로 다름 — 정본은 연결/인증을 단일 `connect()`로 처리. |
| M3 | `subscribe_quotes` 시그니처 차이 | Unit 2/4 vs Unit 1 | stub: `subscribe(symbols, data_type: str)`. 정본: `subscribe_quotes(symbols, callback: Callable[[QuoteEvent], None])`. 콜백 패턴 vs `listen()` 스트리밍 패턴 — 아키텍처 설계 차이. |
| M4 | `get_quote()` vs `get_current_price()` | Unit 2/4 vs Unit 1 | stub: `get_current_price() -> int`. 정본: `get_quote() -> QuoteEvent`. 반환 타입과 정보량이 다름 (정본이 더 풍부). |
| M5 | `listen()` 메서드 부재 (정본) | Unit 1 정본 | `cloud_server`의 `KiwoomCollector.listen()`은 `broker.listen()`을 호출. 정본 ABC에는 `listen()`이 없음. 정본 인터페이스가 콜백 패턴이므로 `kiwoom_collector.py` 전체 로직 수정 필요. |
| M6 | `send_order(**kwargs)` vs `place_order(...)` 구조화 파라미터 | Unit 2 vs Unit 1 | `local_server/routers/trading.py`의 TODO 연동 시 `place_order` 시그니처에 맞게 수정 필요. `client_order_id`, `OrderSide`, `OrderType` Enum, `Decimal` limit_price 모두 필요. |
| M7 | `QuoteEvent.timestamp` 필수성 차이 | Unit 4 stub vs Unit 1 정본 | stub: `timestamp: datetime` (필수). 정본: `timestamp: Optional[datetime] = None`. `market_repository.py`는 `event.timestamp.replace(...)` 직접 호출 — 정본에서 `None`이면 `AttributeError`. |

### Low (문서/구조 불일치)

| # | 항목 | 위치 | 상세 |
|---|------|------|------|
| L1 | `sv_core.models` 디렉토리 존재 여부 | Unit 4 main 브랜치 | Unit 4: `sv_core/models/quote.py` 존재. Unit 1 정본: `sv_core/models/` 디렉토리 없음 (모델은 `sv_core/broker/models.py`). 병합 시 디렉토리 구조 정리 필요. |
| L2 | `cancel_order` 파라미터명 | Unit 2 vs Unit 1 | Unit 2: `order_no: str`. 정본: `order_id: str`. 파라미터명만 다르고 기능 동일. |
| L3 | `QuoteEvent.raw` 필드 부재 | Unit 4 stub | 정본은 `raw: dict` 보유. stub은 없음. 원본 API 응답 보존용 필드이므로 디버깅 시 차이 발생 가능. |
| L4 | `broker/__init__.py` re-export | Unit 2 stub | Unit 2의 `sv_core/broker/__init__.py`는 빈 주석만 있음. 정본은 모든 public 심볼을 re-export. 사용자가 `from sv_core.broker import QuoteEvent`처럼 단축 import 사용 시 Unit 2 stub에서는 실패. |

---

## 6. 수정 필요 사항 (구체적 제안)

정본(Unit 1) 병합 기준으로 Unit 4 `cloud_server/`와 `sv_core/` stub을 수정해야 한다.
Unit 2 `local_server/`는 현재 직접 import가 없어 즉각적 충돌은 없으나 TODO 연동 시 동일 지침 적용.

### 수정 1 (C1 해결) — cloud_server의 QuoteEvent import 경로 교체

```python
# 수정 전 (cloud_server/collector/kiwoom_collector.py:11)
from sv_core.models.quote import QuoteEvent

# 수정 후
from sv_core.broker.models import QuoteEvent
```

```python
# 수정 전 (cloud_server/services/market_repository.py:13)
from sv_core.models.quote import QuoteEvent

# 수정 후
from sv_core.broker.models import QuoteEvent
```

### 수정 2 (C2, C3, L3 해결) — sv_core/models/quote.py stub 삭제 또는 정본 경로로 대체

Unit 1 병합 후 `sv_core/models/` 디렉토리 전체를 삭제하고 정본의 `sv_core/broker/models.py`를 사용한다.
병합 전까지 임시 호환을 유지하려면 `sv_core/models/quote.py`를 아래로 교체:

```python
# sv_core/models/quote.py — 임시 호환 shim (Unit 1 병합 후 삭제)
from sv_core.broker.models import QuoteEvent  # noqa: F401
```

### 수정 3 (C4, C5 해결) — cloud_server/_KiwoomStub을 정본 ABC에 맞게 재작성

Unit 1 병합 시 `cloud_server/core/broker_factory.py`의 `_KiwoomStub`을 정본 ABC 메서드에 맞게 전면 수정:

```python
class _KiwoomStub(BrokerAdapter):
    """정본 Unit 1 병합 전 임시 stub"""

    async def connect(self) -> None:
        logger.info("[KiwoomStub] connect()")

    async def disconnect(self) -> None:
        logger.info("[KiwoomStub] disconnect()")

    @property
    def is_connected(self) -> bool:
        return False

    async def get_balance(self) -> BalanceResult:
        from sv_core.broker.models import BalanceResult
        from decimal import Decimal
        return BalanceResult(cash=Decimal(0), total_eval=Decimal(0))

    async def get_quote(self, symbol: str) -> QuoteEvent:
        from sv_core.broker.models import QuoteEvent
        from decimal import Decimal
        from datetime import datetime
        return QuoteEvent(symbol=symbol, price=Decimal(0), volume=0, timestamp=datetime.now())

    async def subscribe_quotes(self, symbols, callback):
        pass

    async def unsubscribe_quotes(self, symbols):
        pass

    async def place_order(self, client_order_id, symbol, side, order_type, qty, limit_price=None):
        from sv_core.broker.models import OrderResult, OrderStatus
        return OrderResult(
            order_id="stub", client_order_id=client_order_id,
            symbol=symbol, side=side, order_type=order_type,
            qty=qty, limit_price=limit_price, status=OrderStatus.REJECTED,
        )

    async def cancel_order(self, order_id: str) -> OrderResult:
        raise NotImplementedError("[KiwoomStub] cancel_order")

    async def get_open_orders(self) -> list:
        return []
```

### 수정 4 (M5 해결) — cloud_server/collector/kiwoom_collector.py 아키텍처 수정

`KiwoomCollector.listen()`은 `broker.listen()`을 호출하나 정본 ABC에는 `listen()`이 없다.
정본은 `subscribe_quotes(symbols, callback)` 콜백 패턴을 사용한다.
`KiwoomCollector`를 콜백 패턴으로 재설계해야 한다:

```python
# 수정 방향: listen() 스트리밍 대신 callback 패턴
import asyncio

class KiwoomCollector:
    def __init__(self, broker: BrokerAdapter):
        self.broker = broker
        self._queue: asyncio.Queue[QuoteEvent] = asyncio.Queue()

    async def subscribe(self, symbols: list[str]) -> None:
        await self.broker.subscribe_quotes(symbols, self._queue.put_nowait)

    async def listen(self) -> AsyncIterator[QuoteEvent]:
        while True:
            event = await self._queue.get()
            yield event
```

### 수정 5 (M7 해결) — market_repository.py의 timestamp None 가드

```python
# 수정 전 (market_repository.py:52)
ts = event.timestamp.replace(second=0, microsecond=0)

# 수정 후
if event.timestamp is None:
    raise ValueError(f"QuoteEvent.timestamp가 None — symbol={event.symbol}")
ts = event.timestamp.replace(second=0, microsecond=0)
```

### 수정 6 (Unit 2 TODO 연동 시) — local_server/routers/trading.py

Unit 1 병합 후 `# TODO: Unit 1 BrokerAdapter.send_order() 연동` 부분을 정본 인터페이스로 교체:

```python
# place_order 라우터에서
from sv_core.broker.base import BrokerAdapter
from sv_core.broker.models import OrderSide, OrderType
from decimal import Decimal

# broker 인스턴스는 dependency injection 또는 전역 싱글톤으로 획득
result = await broker.place_order(
    client_order_id=str(uuid.uuid4()),
    symbol=body.symbol,
    side=OrderSide(body.side),
    order_type=OrderType(body.order_type),
    qty=body.qty,
    limit_price=Decimal(body.limit_price) if body.limit_price else None,
)
```

---

## 7. 요약

| 우선순위 | 건수 | 내용 |
|---------|------|------|
| Critical | 5건 | 정본 병합 즉시 런타임 실패 (ImportError, ABC 미구현) |
| Medium | 7건 | 아키텍처/설계 불일치 (콜백 vs 스트리밍, 타입 차이) |
| Low | 4건 | 명명/구조 불일치 (기능 영향 낮음) |

**핵심 원인**: Unit 2와 Unit 4가 정본 확정 전에 각자 독립적으로 stub을 설계했고, 인터페이스 설계 방향이 달랐다.
- Unit 2/4 stub: 인증(`authenticate`) + 스트리밍(`listen`) + 원시 dict 반환
- Unit 1 정본: 연결(`connect`) + 콜백(`subscribe_quotes`) + 타입화된 dataclass 반환

**병합 우선순위**: C1(import 경로) → C4/C5(_KiwoomStub 재작성) → M5(KiwoomCollector 콜백 전환) → M7(timestamp None 가드) 순으로 처리.
