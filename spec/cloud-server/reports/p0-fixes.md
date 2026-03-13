# P0 수정 보고서 — Unit 4 (cloud_server) sv_core 정합성 + API 계약 + 보안

작성일: 2026-03-05

## 수정 목록

### C1 — QuoteEvent import 경로 수정

**대상 파일:**
- `cloud_server/collector/kis_collector.py`
- `cloud_server/services/market_repository.py`

**변경 내용:**
```python
# 이전
from sv_core.models.quote import QuoteEvent

# 이후
from sv_core.broker.models import QuoteEvent  # C1: 정본 경로로 수정
```

두 파일 모두 `sv_core.models.quote` (존재하지 않는 경로) → `sv_core.broker.models` (정본 경로) 로 수정.

---

### C2/C3 — QuoteEvent 필드 타입/이름 수정 + timestamp None 가드

**대상 파일:** `cloud_server/services/market_repository.py`

**변경 내용 (save_minute_bar):**
```python
# 이전
ts = event.timestamp.replace(second=0, microsecond=0)

# 이후
# C2/C3: timestamp는 Optional — None이면 현재 시각 사용
raw_ts = event.timestamp if event.timestamp is not None else datetime.utcnow()
ts = raw_ts.replace(second=0, microsecond=0)
```

`QuoteEvent.timestamp`는 `Optional[datetime]`이므로 None 가드 추가.
`price` 필드는 정본 모델에서 이미 `Decimal` 타입이므로 MarketRepository 내 비교/대입 로직은 타입 변경 없이 호환됨.
`bid`/`ask` 필드는 해당 파일에서 직접 참조하지 않으므로 추가 수정 불필요.

---

### C4 — get_balance() 시그니처 수정

**대상 파일:** `cloud_server/core/broker_factory.py` (`_KiwoomStub`)

C5 재작성 시 함께 처리됨. 기존 `get_balance(self, account_no: str) -> dict` →
`get_balance(self) -> BalanceResult` 로 변경 (파라미터 제거, 반환 타입 정본 모델 사용).

---

### C5 — _KiwoomStub 및 broker_factory 재작성

**대상 파일:** `cloud_server/core/broker_factory.py`

**이전 구현 (잘못된 시그니처):**
```python
class _KiwoomStub(BrokerAdapter):
    async def authenticate(self) -> None: ...          # ABC에 없음
    async def is_authenticated(self) -> bool: ...      # ABC에 없음 (property 아님)
    async def get_current_price(self, symbol: str) -> int: ...  # ABC에 없음
    async def get_balance(self, account_no: str) -> dict: ...   # 파라미터 잘못됨
    async def get_positions(self, account_no: str) -> list[dict]: ...  # ABC에 없음
    async def subscribe(self, symbols, data_type): ...  # ABC에 없음
    async def unsubscribe(self, symbols, data_type): ... # ABC에 없음
    async def listen(self): ...                         # ABC에 없음
```

**이후 구현 (정본 ABC 준수):**
```python
class _KiwoomStub(BrokerAdapter):
    async def connect(self) -> None                     # OK
    async def disconnect(self) -> None                  # OK
    @property is_connected(self) -> bool               # OK (property)
    async def get_balance(self) -> BalanceResult        # OK (C4 포함)
    async def get_quote(self, symbol: str) -> QuoteEvent  # OK
    async def subscribe_quotes(self, symbols, callback) -> None  # OK
    async def unsubscribe_quotes(self, symbols) -> None  # OK
    async def place_order(self, client_order_id, symbol, side, order_type, qty, limit_price) -> OrderResult  # OK
    async def cancel_order(self, order_id) -> OrderResult  # OK
    async def get_open_orders(self) -> list[OrderResult]  # OK
```

**연쇄 수정 — KiwoomCollector (kis_collector.py):**
C5의 ABC 변경으로 인해 `KiwoomCollector`의 broker 호출도 업데이트:
- `broker.subscribe(symbols, data_type)` → `broker.subscribe_quotes(symbols, self._on_quote)` (콜백 패턴)
- `broker.unsubscribe(symbols, "quote")` → `broker.unsubscribe_quotes(symbols)`
- `broker.listen()` (async generator) → `asyncio.Queue` 기반 콜백 수신으로 전환

---

### A7 — 토큰 필드명 수정 (jwt → access_token)

**대상 파일:** `cloud_server/api/auth.py`

**login 엔드포인트:**
```python
# 이전
"data": {"jwt": jwt_token, "refresh_token": raw_rt, "expires_in": 3600}

# 이후
"data": {"access_token": jwt_token, "refresh_token": raw_rt, "expires_in": 3600}
```

**refresh 엔드포인트:**
```python
# 이전
"data": {"jwt": new_jwt, "refresh_token": new_raw_rt, "expires_in": 3600}

# 이후
"data": {"access_token": new_jwt, "refresh_token": new_raw_rt, "expires_in": 3600}
```

두 엔드포인트 모두 `{ "success": true, "data": { "access_token": "...", "refresh_token": "..." } }` 패턴으로 통일.

---

### SEC-C2 — SECRET_KEY 기본값 제거

**대상 파일:** `cloud_server/core/config.py`

**변경 내용:**
```python
# 이전
SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# 이후
SECRET_KEY: str = os.environ.get("SECRET_KEY", "")  # 빈 문자열 = 미설정 표시

# get_settings()에 검증 추가
def get_settings() -> Settings:
    s = Settings()
    if not s.SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY 환경 변수가 설정되지 않았습니다. 서버를 시작할 수 없습니다."
        )
    return s
```

`SECRET_KEY` 미설정 시 `get_settings()` 호출 시점(서버 시작 시)에 `RuntimeError` 발생 → 취약한 기본값으로 운영 서버가 기동되는 상황 방지.

---

## 수정 파일 요약

| 파일 | 수정 항목 |
|------|----------|
| `cloud_server/collector/kis_collector.py` | C1, C5 연쇄 (subscribe_quotes 콜백 패턴) |
| `cloud_server/services/market_repository.py` | C1, C2/C3 (timestamp None 가드) |
| `cloud_server/core/broker_factory.py` | C4, C5 (_KiwoomStub 전면 재작성) |
| `cloud_server/api/auth.py` | A7 (jwt → access_token, 2개소) |
| `cloud_server/core/config.py` | SEC-C2 (기본값 제거 + 시작 실패 검증) |
