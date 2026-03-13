## P0 재리뷰 결과

검증 일시: 2026-03-05

| # | 이슈 | 수정 상태 | 검증 결과 | 잔여 문제 |
|---|------|----------|----------|----------|
| C1 | cloud_server import 경로 | ✅ | `sv_core.broker.models.QuoteEvent` 사용 확인 | 없음 |
| C2/C3 | QuoteEvent 필드 참조 + timestamp None 가드 | ✅ | `price: Decimal`, `bid_price`, `ask_price` 정본 일치. `timestamp is not None` 가드 확인 | 없음 |
| C4 | `get_balance()` account_no 제거 + BalanceResult 반환 | ✅ | stub `get_balance(self)` 파라미터 없음, `BalanceResult` 반환 확인 | 없음 |
| C5 | `_KiwoomStub` 전체 메서드 구현 | ✅ | 모든 9개 메서드 구현 확인 | 없음 |
| C5연쇄 | KiwoomCollector 콜백 패턴 사용 | ✅ | `subscribe_quotes(symbols, self._on_quote)` 콜백 패턴 사용. `listen()`은 큐 소비용 generator (구독과 분리됨) | 없음 |
| stub정합 | Unit 2 stub base.py 메서드명/시그니처 | ⚠️ | 메서드명 일치. 시그니처 일부 불일치 | 아래 상세 참고 |
| A1 | `POST /api/auth/token` — `{ access_token, refresh_token }` 수신 | ✅ | `CloudTokenRequest`에 `access_token`, `refresh_token` 필드 확인 | 없음 |
| A2 | `POST /api/config/kiwoom` 추가 | ✅ | `router.post("/kiwoom", ...)` 확인 | 없음 |
| A3 | `POST /api/strategy/kill` 추가 | ✅ | `router.post("/strategy/kill", ...)` 확인 | 없음 |
| A4 | `POST /api/strategy/unlock` 추가 | ✅ | `router.post("/strategy/unlock", ...)` 확인 | 없음 |
| A7 | cloud auth 응답 토큰 필드 `access_token` | ✅ | `/login` 및 `/refresh` 모두 `"access_token": jwt_token` 사용. 주석에 `# A7: jwt → access_token` 명시됨 | 없음 |
| W1 | WS 타입명 `price_update`/`execution`/`status_change` | ✅ | 상수 `WS_TYPE_PRICE_UPDATE = "price_update"`, `WS_TYPE_EXECUTION = "execution"`, `WS_TYPE_STATUS_CHANGE = "status_change"` 확인. docstring에도 명시 | 없음 |
| SEC-C1 | `build_headers()`에서 appsecret 제거 + 별도 메서드 | ✅ | `build_headers()`는 `Authorization`, `appkey`만 포함. `build_auth_headers()`가 별도로 `appsecret` 포함 | 없음 |
| SEC-C2 | SECRET_KEY 기본값 제거 + RuntimeError | ⚠️ | `get_settings()`에서 RuntimeError 발생 확인. 그러나 모듈 최하단 `settings = get_settings()` 전역 호출이 있음 | 아래 상세 참고 |

---

## 상세 — 잔여 문제

### stub 정합 (Unit 2 `agent-a643a319/sv_core/broker/base.py`)

**파일**: `d:/Projects/StockVision/.claude/worktrees/agent-a643a319/sv_core/broker/base.py`

Unit 2의 stub `BrokerAdapter`는 정본(Unit 1 `agent-a574e260/sv_core/broker/base.py`)과 메서드명은 동일하지만, 다음 차이가 존재한다.

**1. `place_order` side/order_type 타입 불일치**

정본 (Unit 1):
```python
async def place_order(
    self,
    client_order_id: str,
    symbol: str,
    side: OrderSide,       # Enum
    order_type: OrderType, # Enum
    qty: int,
    limit_price: Optional[Decimal] = None,
) -> OrderResult: ...
```

stub (Unit 2, 라인 147-155):
```python
async def place_order(
    self,
    client_order_id: str,
    symbol: str,
    side: str,          # "buy" | "sell"  ← str, Enum 아님
    order_type: str,    # "MARKET" | "LIMIT"  ← str, Enum 아님
    qty: int,
    limit_price: Decimal | None = None,
) -> OrderResult: ...
```

stub이 `OrderSide`/`OrderType` Enum 대신 `str`을 사용한다. stub이 독립적으로 사용되는 동안에는 런타임 오류가 없으나, Unit 1 구현체로 교체 시 타입 불일치가 드러날 수 있다.

**2. `QuoteEvent.timestamp` 타입 불일치**

정본 `models.py` (라인 87): `timestamp: Optional[datetime] = None`

stub `base.py` (라인 38-46):
```python
def __init__(
    self,
    ...
    timestamp: str,   # ← str, Optional[datetime] 아님. None 기본값도 없음
    ...
)
```

timestamp가 `str`로 선언되어 있고 Optional이 아니다. 정본의 `Optional[datetime]`과 불일치. Unit 2 코드에서 `event.timestamp`를 datetime으로 처리하려 할 경우 타입 오류 발생.

**3. stub 모델과 정본 모델이 별개 클래스**

Unit 2 stub은 자체 `QuoteEvent`, `BalanceResult`, `OrderResult`, `Position` 클래스를 `base.py` 내에 인라인으로 정의한다(라인 16-91). Unit 1이 머지된 이후에는 이 stub 모델들을 `sv_core.broker.models`에서 임포트하도록 교체해야 한다.

---

### SEC-C2 (`cloud_server/core/config.py`)

**파일**: `d:/Projects/StockVision/cloud_server/core/config.py`

`get_settings()`는 SECRET_KEY 미설정 시 `RuntimeError`를 올바르게 발생시킨다 (라인 82-85).

그러나 **라인 90**에 다음 전역 호출이 있다:

```python
# 편의 접근
settings = get_settings()
```

이 코드는 모듈 임포트 시점에 즉시 실행된다. SECRET_KEY가 없으면 `import cloud_server.core.config`만 해도 RuntimeError가 발생하여 전체 앱 임포트가 실패한다. 개발 환경(`.env` 없이 테스트하는 경우)에서도 예외 없이 작동하지 않는다.

**권고**: 편의 접근 `settings = get_settings()` 전역 호출을 제거하고, 각 모듈에서 `from cloud_server.core.config import get_settings; settings = get_settings()`로 명시적으로 호출하거나, 앱 시작 시(lifespan/startup 핸들러)에서만 호출하도록 변경하라. 또는 개발 환경(`ENV=development`)에서는 경고만 발행하고 테스트용 기본값을 허용하는 예외 처리를 추가하라.

---

## 요약

- 11건 중 **9건 완전 수정 확인**
- **2건 부분적 잔여 문제**:
  - stub 정합: Unit 2 `place_order` side/order_type Enum 불일치, `QuoteEvent.timestamp` 타입/Optional 불일치 — 통합 시 수정 필요 (현재 독립 개발 중이므로 블로커 아님)
  - SEC-C2: RuntimeError 로직은 올바르나, 모듈 최하단 `settings = get_settings()` 전역 즉시 호출이 개발/테스트 환경에서 문제가 될 수 있음
