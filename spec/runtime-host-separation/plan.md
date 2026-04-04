# Runtime / Host 분리 구현 계획 (Phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** engine/ 내부의 host 직접 import 11곳을 전부 Port/Adapter 패턴으로 교체하여, engine이 host 구현을 모르게 만든다.

**Architecture:** `engine/ports.py`에 4개 Protocol(LogPort, BarDataPort, BarStorePort, ReferenceDataPort)을 정의하고, `local_server/adapters.py`에 어댑터 4개를 구현한다. `routers/trading.py`에서 어댑터를 조립하여 StrategyEngine에 주입한다. BrokerAdapter는 `sv_core`에 이미 있으므로 그대로 재사용한다.

**Tech Stack:** Python 3.13, typing.Protocol, FastAPI

**Spec:** `spec/runtime-host-separation/spec.md`

---

## 파일 구조

| 구분 | 파일 | 역할 |
|------|------|------|
| 신규 (runtime) | `local_server/engine/ports.py` | 4개 Protocol + LOG_TYPE 상수 |
| 신규 (host) | `local_server/adapters.py` | 4개 Adapter |
| 수정 (runtime) | `local_server/engine/executor.py` | LogPort 주입 |
| 수정 (runtime) | `local_server/engine/engine.py` | LogPort + ReferenceDataPort 주입, 서브모듈에 port 전달 |
| 수정 (runtime) | `local_server/engine/indicator_provider.py` | BarDataPort 주입 |
| 수정 (runtime) | `local_server/engine/bar_builder.py` | BarStorePort 주입 |
| 수정 (runtime) | `local_server/engine/alert_monitor.py` | LogPort 주입 + config 생성자 파라미터 |
| 수정 (runtime) | `local_server/engine/limit_checker.py` | TYPE_CHECKING import를 LogPort로 변경 |
| 수정 (host) | `local_server/routers/trading.py` | 어댑터 조립 + 엔진 생성자 호출 변경 |
| 수정 (host) | `local_server/main.py` | AlertMonitor 생성에 port 주입 |
| 수정 (test) | `local_server/tests/test_engine.py` | StrategyEngine 생성자 변경 반영 |
| 수정 (test) | `local_server/tests/test_engine_v2.py` | StrategyEngine 생성자 변경 반영 |

---

### Task 1: ports.py — Port 인터페이스 + LOG_TYPE 상수 정의

**Files:**
- Create: `local_server/engine/ports.py`

- [ ] **Step 1: ports.py 작성**

```python
"""engine이 host에게 요구하는 인터페이스 계약 (Ports & Adapters 패턴).

engine/ 내부 모듈은 이 파일의 Protocol과 상수만 참조한다.
host(local_server 나머지)가 구체 구현(Adapter)을 조립하여 주입한다.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol

# ── LOG_TYPE 상수 ──
# engine이 쓰는 로그 타입. host의 log_db.py에도 동일 값이 있으나,
# engine은 이 파일에서만 import한다.
# Phase 2에서 sv_runtime/ 이동 시 단일 원천 위치를 재검토.

LOG_TYPE_FILL = "FILL"
LOG_TYPE_ORDER = "ORDER"
LOG_TYPE_ERROR = "ERROR"
LOG_TYPE_STRATEGY = "STRATEGY"
LOG_TYPE_ALERT = "ALERT"


# ── Port Protocols ──


class LogPort(Protocol):
    """실행 로그 기록 포트."""

    async def write(
        self,
        log_type: str,
        message: str,
        *,
        symbol: str | None = None,
        meta: dict[str, Any] | None = None,
        intent_id: str | None = None,
    ) -> None: ...

    def today_realized_pnl(self) -> float: ...

    def today_executed_amount(self) -> Decimal: ...


class BarDataPort(Protocol):
    """분봉 데이터 조회 포트."""

    async def fetch_minute_bars(
        self, symbol: str, tf: str, limit: int,
    ) -> list[dict]: ...


class BarStorePort(Protocol):
    """분봉 저장 포트."""

    def save_bars(self, symbol: str, bars: list[dict]) -> None: ...


class ReferenceDataPort(Protocol):
    """종목 메타(시장 구분) 조회 포트."""

    def get_market_map(self) -> dict[str, str]: ...
```

- [ ] **Step 2: import 확인**

```bash
python -c "from local_server.engine.ports import LogPort, BarDataPort, BarStorePort, ReferenceDataPort, LOG_TYPE_ORDER; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add local_server/engine/ports.py
git commit -m "feat(engine): Port 인터페이스 + LOG_TYPE 상수 정의 (runtime/host 분리 준비)"
```

---

### Task 2: adapters.py — Host 어댑터 구현

**Files:**
- Create: `local_server/adapters.py`

- [ ] **Step 1: adapters.py 작성**

```python
"""Host → Runtime 어댑터.

engine/ports.py의 Protocol을 구현하는 얇은 래퍼.
host가 가진 구체 서비스(LogDB, CloudClient 등)를 port 인터페이스에 맞게 감싼다.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


class LogDbAdapter:
    """LogPort 구현 — LogDB를 감싸는 래퍼."""

    def __init__(self, log_db: Any) -> None:
        self._db = log_db

    async def write(
        self,
        log_type: str,
        message: str,
        *,
        symbol: str | None = None,
        meta: dict[str, Any] | None = None,
        intent_id: str | None = None,
    ) -> None:
        await self._db.async_write(
            log_type, message,
            symbol=symbol, meta=meta, intent_id=intent_id,
        )

    def today_realized_pnl(self) -> float:
        return self._db.today_realized_pnl()

    def today_executed_amount(self) -> Decimal:
        return self._db.today_executed_amount()


class CloudBarDataAdapter:
    """BarDataPort 구현 — CloudClient를 감싸는 래퍼.

    CloudClient가 None(미연결)이면 빈 리스트 반환.
    """

    def __init__(self, cloud_client: Any | None) -> None:
        self._client = cloud_client

    async def fetch_minute_bars(
        self, symbol: str, tf: str, limit: int,
    ) -> list[dict]:
        if self._client is None:
            return []
        try:
            path = f"/api/v1/stocks/{symbol}/bars?resolution={tf}&limit={limit}"
            resp = await self._client._get(path)
            return resp.get("data", []) if isinstance(resp, dict) else []
        except Exception:
            logger.warning("분봉 조회 실패 [%s %s]", symbol, tf)
            return []


class MinuteBarStoreAdapter:
    """BarStorePort 구현 — MinuteBarStore를 감싸는 래퍼."""

    def __init__(self, store: Any | None) -> None:
        self._store = store

    def save_bars(self, symbol: str, bars: list[dict]) -> None:
        if self._store is not None:
            self._store.save_bars(symbol, bars)


class StockMasterAdapter:
    """ReferenceDataPort 구현 — StockMasterCache를 감싸는 래퍼."""

    def __init__(self, cache: Any) -> None:
        self._cache = cache

    def get_market_map(self) -> dict[str, str]:
        return {
            s["symbol"]: s.get("market", "")
            for s in self._cache.get_all()
        }
```

- [ ] **Step 2: import 확인**

Run: `python -c "from local_server.adapters import LogDbAdapter, CloudBarDataAdapter, MinuteBarStoreAdapter, StockMasterAdapter; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add local_server/adapters.py
git commit -m "feat(host): Port 어댑터 구현 (LogDb, CloudBarData, MinuteBarStore, StockMaster)"
```

---

### Task 3: executor.py — LogPort 주입

**Files:**
- Modify: `local_server/engine/executor.py`

executor.py의 host 의존은 1곳: `execute()` 메서드 내부의 `from local_server.storage.log_db import get_log_db, LOG_TYPE_ORDER, LOG_TYPE_FILL, LOG_TYPE_ERROR` (line 86). `db = get_log_db()`로 받아서 메서드 전체에서 `db.async_write()` 호출.

- [ ] **Step 1: 생성자에 LogPort 파라미터 추가**

`executor.py`의 `__init__` 시그니처를 변경한다:

```python
# 현재
class OrderExecutor:
    def __init__(
        self,
        broker: BrokerAdapter,
        signal_manager: SignalManager,
        price_verifier: PriceVerifier,
        limit_checker: LimitChecker,
        safeguard: Safeguard,
    ) -> None:
        self._broker = broker
        self._signal = signal_manager
        self._price = price_verifier
        self._limit = limit_checker
        self._safeguard = safeguard
```

```python
# 변경 후
class OrderExecutor:
    def __init__(
        self,
        broker: BrokerAdapter,
        signal_manager: SignalManager,
        price_verifier: PriceVerifier,
        limit_checker: LimitChecker,
        safeguard: Safeguard,
        log: LogPort,
    ) -> None:
        self._broker = broker
        self._signal = signal_manager
        self._price = price_verifier
        self._limit = limit_checker
        self._safeguard = safeguard
        self._log = log
```

import 추가 (파일 상단 TYPE_CHECKING 블록 안):

```python
if TYPE_CHECKING:
    from sv_core.broker.base import BrokerAdapter
    from sv_core.broker.models import BalanceResult
    from local_server.engine.limit_checker import LimitChecker
    from local_server.engine.ports import LogPort
    from local_server.engine.price_verifier import PriceVerifier
    from local_server.engine.safeguard import Safeguard
    from local_server.engine.signal_manager import SignalManager
```

- [ ] **Step 2: execute() 내부의 host import 제거**

`execute()` 메서드에서 다음 2줄을 삭제:

```python
        from local_server.storage.log_db import get_log_db, LOG_TYPE_ORDER, LOG_TYPE_FILL, LOG_TYPE_ERROR
        # ...
        db = get_log_db()
```

대신 파일 상단에 sv_core에서 상수를 import:

```python
from local_server.engine.ports import LOG_TYPE_ORDER, LOG_TYPE_FILL, LOG_TYPE_ERROR
```

메서드 내부의 모든 `db.async_write(...)` 호출을 `self._log.write(...)` 로 교체.

교체 대상 (execute() 메서드 내의 모든 `await db.async_write(...)` 호출):

```python
# 각각의 db.async_write 호출을 self._log.write로 변경
# 예: 매도 보호 거부 (line ~107)
await self._log.write(LOG_TYPE_ERROR, "미보유 종목 매도 거부", symbol=symbol,
                      meta={"rule_id": rule_id, "side": side}, intent_id=intent_id)

# 중복 체크 (line ~118)
await self._log.write(LOG_TYPE_ERROR, msg, symbol=symbol,
                      meta={"rule_id": rule_id, "side": side, "check": "duplicate"}, intent_id=intent_id)

# 예산 체크 (line ~133)
await self._log.write(LOG_TYPE_ERROR, budget_check.reason, symbol=symbol,
                      meta={"rule_id": rule_id, "side": side, "check": "budget"}, intent_id=intent_id)

# 포지션 수 체크 (line ~143)
await self._log.write(LOG_TYPE_ERROR, pos_check.reason, symbol=symbol,
                      meta={"rule_id": rule_id, "side": side, "check": "max_positions"}, intent_id=intent_id)

# 안전장치 체크 (line ~153)
await self._log.write(LOG_TYPE_ERROR, msg, symbol=symbol,
                      meta={"rule_id": rule_id, "side": side, "check": "safeguard"}, intent_id=intent_id)

# 속도 제한 (line ~163)
await self._log.write(LOG_TYPE_ERROR, msg, symbol=symbol,
                      meta={"rule_id": rule_id, "side": side, "check": "speed"}, intent_id=intent_id)

# 가격 검증 실패 (line ~180)
await self._log.write(LOG_TYPE_ERROR, msg, symbol=symbol,
                      meta={...}, intent_id=intent_id)

# 주문 준비 (line ~191)
await self._log.write(LOG_TYPE_ORDER, f"주문 준비 ({side} {qty}주, {order_type_str})",
                      symbol=symbol, meta={...}, intent_id=intent_id)

# 주문 제출 완료 (line ~220)
await self._log.write(LOG_TYPE_ORDER, f"주문 제출 완료 (order_id={result.order_id})",
                      symbol=symbol, meta={...}, intent_id=intent_id)

# 체결 로그 (line ~233)
await self._log.write(LOG_TYPE_FILL, f"주문 제출 완료 ({ws_price}원, {qty}주)",
                      symbol=symbol, meta={...}, intent_id=intent_id)

# 실행 실패 (line ~257)
await self._log.write(LOG_TYPE_ERROR, f"주문 실행 실패: {e}",
                      symbol=symbol, meta={...}, intent_id=intent_id)
```

- [ ] **Step 3: host import 잔존 확인**

Run: `python -c "content=open('local_server/engine/executor.py').read(); hits=[l for l in content.splitlines() if 'local_server.storage' in l or 'local_server.cloud' in l or 'local_server.config' in l]; print(f'{len(hits)} host imports'); [print(f'  {l.strip()}') for l in hits]"`
Expected: `0 host imports`

- [ ] **Step 4: 커밋**

```bash
git add local_server/engine/executor.py
git commit -m "refactor(executor): host import 제거, LogPort 주입"
```

---

### Task 4: indicator_provider.py — BarDataPort 주입

**Files:**
- Modify: `local_server/engine/indicator_provider.py`

host 의존 1곳: `refresh_minute()` 내부의 `from local_server.cloud.heartbeat import get_cloud_client` (line 76).

- [ ] **Step 1: 생성자에 BarDataPort 파라미터 추가**

현재 `IndicatorProvider.__init__`은 파라미터 없음. 변경:

```python
# 현재
class IndicatorProvider:
    def __init__(self) -> None:
        self._daily_cache: dict[str, dict] = {}
        self._minute_cache: dict[str, dict[str, dict]] = {}
```

```python
# 변경 후
from local_server.engine.ports import BarDataPort

class IndicatorProvider:
    def __init__(self, bar_data: BarDataPort | None = None) -> None:
        self._daily_cache: dict[str, dict] = {}
        self._minute_cache: dict[str, dict[str, dict]] = {}
        self._bar_data = bar_data
```

`| None = None`으로 해서 기존 코드가 깨지지 않도록 한다 (하위 호환).

- [ ] **Step 2: refresh_minute()에서 host import 제거**

`refresh_minute()` 메서드에서 다음 블록:

```python
        from local_server.cloud.heartbeat import get_cloud_client
        client = get_cloud_client()
        if client is None:
            logger.debug("CloudClient 없음 — 분봉 지표 갱신 생략 [%s %s]", symbol, tf)
            return

        try:
            path = f"/api/v1/stocks/{symbol}/bars?resolution={tf}&limit={_MINUTE_LOOKBACK}"
            resp = await client._get(path)
            data: list[dict] = resp.get("data", []) if isinstance(resp, dict) else []
        except Exception:
            logger.warning("분봉 조회 실패 [%s %s]", symbol, tf)
            return
```

을 다음으로 교체:

```python
        if self._bar_data is None:
            logger.debug("BarDataPort 없음 — 분봉 지표 갱신 생략 [%s %s]", symbol, tf)
            return

        try:
            data = await self._bar_data.fetch_minute_bars(symbol, tf, _MINUTE_LOOKBACK)
        except Exception:
            logger.warning("분봉 조회 실패 [%s %s]", symbol, tf)
            return
```

- [ ] **Step 3: host import 잔존 확인**

Run: `python -c "content=open('local_server/engine/indicator_provider.py').read(); hits=[l for l in content.splitlines() if 'local_server.cloud' in l]; print(f'{len(hits)} host imports')"`
Expected: `0 host imports`

- [ ] **Step 4: 커밋**

```bash
git add local_server/engine/indicator_provider.py
git commit -m "refactor(indicator_provider): host import 제거, BarDataPort 주입"
```

---

### Task 5: bar_builder.py — BarStorePort 주입

**Files:**
- Modify: `local_server/engine/bar_builder.py`

host 의존 1곳: `_get_bar_store()` 함수의 `from local_server.storage.minute_bar import get_minute_bar_store` (line 25).

- [ ] **Step 1: 모듈 레벨 _get_bar_store() 제거 + 생성자에 BarStorePort 추가**

파일 상단의 `_bar_store` 글로벌 변수와 `_get_bar_store()` 함수를 삭제:

```python
# 삭제 대상 (lines 16-29)
# 분봉 저장소 (지연 임포트로 순환 참조 방지)
_bar_store = None


def _get_bar_store():
    """MinuteBarStore 싱글턴 반환 (지연 초기화)."""
    global _bar_store
    if _bar_store is None:
        try:
            from local_server.storage.minute_bar import get_minute_bar_store
            _bar_store = get_minute_bar_store()
        except Exception as e:
            logger.warning("MinuteBarStore 초기화 실패 (분봉 저장 비활성화): %s", e)
    return _bar_store
```

BarBuilder 생성자 변경:

```python
# 현재
class BarBuilder:
    def __init__(self) -> None:
        self._current: dict[str, dict] = {}
        self._completed: dict[str, Bar] = {}
        self._latest: dict[str, dict] = {}
```

```python
# 변경 후
from local_server.engine.ports import BarStorePort

class BarBuilder:
    def __init__(self, bar_store: BarStorePort | None = None) -> None:
        self._current: dict[str, dict] = {}
        self._completed: dict[str, Bar] = {}
        self._latest: dict[str, dict] = {}
        self._bar_store = bar_store
```

- [ ] **Step 2: on_quote()에서 _get_bar_store() 호출을 self._bar_store로 교체**

`on_quote()` 메서드의 분봉 저장 블록:

```python
            # MinuteBarStore에 완성 분봉 저장
            store = _get_bar_store()
            if store is not None:
                try:
                    store.save_bars(symbol, [{
```

을 다음으로 교체:

```python
            # 완성 분봉 저장
            if self._bar_store is not None:
                try:
                    self._bar_store.save_bars(symbol, [{
```

- [ ] **Step 3: host import 잔존 확인**

Run: `python -c "content=open('local_server/engine/bar_builder.py').read(); hits=[l for l in content.splitlines() if 'local_server.storage' in l]; print(f'{len(hits)} host imports')"`
Expected: `0 host imports`

- [ ] **Step 4: 커밋**

```bash
git add local_server/engine/bar_builder.py
git commit -m "refactor(bar_builder): host import 제거, BarStorePort 주입"
```

---

### Task 6: alert_monitor.py — LogPort 주입 + config 생성자 파라미터

**Files:**
- Modify: `local_server/engine/alert_monitor.py`

host 의존 2곳:
- `fire()` 내부의 `from local_server.storage.log_db import get_log_db, LOG_TYPE_ALERT` (line 139)
- `_check_daily_loss_proximity()` 내부의 `from local_server.config import get_config` (line 230)

- [ ] **Step 1: 생성자에 LogPort + max_loss_pct 추가**

```python
# 현재
class AlertMonitor:
    _cooldown = timedelta(minutes=30)

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        cfg = config or {}
        self._cfg = cfg
        self._fired: dict[str, tuple[datetime, float | None]] = {}
        self._broadcast: Optional[Callable[[dict], Awaitable[None]]] = None
        logger.info("AlertMonitor initialized")
```

```python
# 변경 후
from local_server.engine.ports import LogPort
from local_server.engine.ports import LOG_TYPE_ALERT

class AlertMonitor:
    _cooldown = timedelta(minutes=30)

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        log: LogPort | None = None,
        max_loss_pct: Decimal | None = None,
    ) -> None:
        cfg = config or {}
        self._cfg = cfg
        self._fired: dict[str, tuple[datetime, float | None]] = {}
        self._broadcast: Optional[Callable[[dict], Awaitable[None]]] = None
        self._log = log
        self._max_loss_pct = max_loss_pct or Decimal("5.0")
        logger.info("AlertMonitor initialized")
```

Decimal import 추가 (파일 상단):

```python
from decimal import Decimal
```

- [ ] **Step 2: fire()에서 log_db import 제거**

`fire()` 메서드의 LogDB 기록 블록:

```python
        # LogDB 기록
        try:
            from local_server.storage.log_db import get_log_db, LOG_TYPE_ALERT
            await get_log_db().async_write(
                LOG_TYPE_ALERT,
                message,
                symbol=symbol,
                meta={
                    "alert_id": alert_id,
                    "alert_type": alert_type,
                    "severity": severity,
                    "current_value": current_value,
                    **(meta or {}),
                },
            )
        except Exception as e:
            logger.error("AlertMonitor LogDB 기록 실패: %s", e)
```

을 다음으로 교체:

```python
        # LogDB 기록
        if self._log:
            try:
                await self._log.write(
                    LOG_TYPE_ALERT,
                    message,
                    symbol=symbol,
                    meta={
                        "alert_id": alert_id,
                        "alert_type": alert_type,
                        "severity": severity,
                        "current_value": current_value,
                        **(meta or {}),
                    },
                )
            except Exception as e:
                logger.error("AlertMonitor LogDB 기록 실패: %s", e)
```

- [ ] **Step 3: _check_daily_loss_proximity()에서 config import 제거**

메서드 내부의:

```python
        from local_server.config import get_config
        from decimal import Decimal
        max_loss_pct = Decimal(str(get_config().get("max_loss_pct", "5.0")))
```

을 다음으로 교체:

```python
        max_loss_pct = self._max_loss_pct
```

(`from decimal import Decimal`은 이미 파일 상단으로 옮겼으므로 제거.)

- [ ] **Step 4: host import 잔존 확인**

Run: `python -c "content=open('local_server/engine/alert_monitor.py').read(); hits=[l for l in content.splitlines() if 'local_server.storage' in l or 'local_server.config' in l]; print(f'{len(hits)} host imports')"`
Expected: `0 host imports`

- [ ] **Step 5: 커밋**

```bash
git add local_server/engine/alert_monitor.py
git commit -m "refactor(alert_monitor): host import 제거, LogPort + max_loss_pct 주입"
```

---

### Task 7: engine.py — LogPort + ReferenceDataPort 주입 + 서브모듈에 port 전달

**Files:**
- Modify: `local_server/engine/engine.py`

host 의존 4곳:
- `start()` line 103: `from local_server.storage.log_db import get_log_db` → `restore_from_db`
- `evaluate_all()` line 223: `get_log_db().today_realized_pnl()`
- `evaluate_all()` line 286: `get_log_db().async_write(LOG_TYPE_ERROR)`
- `evaluate_all()` line 300: `get_log_db().async_write(LOG_TYPE_STRATEGY)`
- `_resolve_markets()` line 665: `from local_server.storage.stock_master_cache import get_stock_master_cache`

이 태스크는 변경이 가장 크다. engine.py는 모든 서브모듈의 조립 지점이므로 port 전달도 여기서 한다.

- [ ] **Step 1: 생성자 시그니처 변경 + port import**

파일 상단 import 영역에 추가:

```python
from local_server.engine.ports import (
    BarDataPort, BarStorePort, LogPort, ReferenceDataPort,
)
from local_server.engine.ports import LOG_TYPE_ERROR, LOG_TYPE_STRATEGY
```

생성자 변경:

```python
# 현재
def __init__(
    self,
    broker: BrokerAdapter,
    config: dict[str, Any] | None = None,
) -> None:
```

```python
# 변경 후
def __init__(
    self,
    broker: BrokerAdapter,
    log: LogPort,
    bar_data: BarDataPort,
    bar_store: BarStorePort,
    ref_data: ReferenceDataPort,
    config: dict[str, Any] | None = None,
) -> None:
```

생성자 본문에 `self._log = log`, `self._ref_data = ref_data` 추가.

- [ ] **Step 2: 서브모듈 생성에 port 전달**

생성자 본문의 서브모듈 생성 코드를 수정:

```python
# OrderExecutor — log 추가
self._executor = OrderExecutor(
    broker=broker,
    signal_manager=self._signal_manager,
    price_verifier=self._price_verifier,
    limit_checker=self._limit_checker,
    safeguard=self._safeguard,
    log=log,
)

# IndicatorProvider — bar_data 추가
self._indicator_provider = IndicatorProvider(bar_data=bar_data)

# BarBuilder — bar_store 추가
self._bar_builder = BarBuilder(bar_store=bar_store)

# AlertMonitor — log + max_loss_pct 추가
self._alert_monitor = AlertMonitor(
    config=cfg.get("alerts"),
    log=log,
    max_loss_pct=Decimal(str(cfg.get("max_loss_pct", "5.0"))),
)
```

- [ ] **Step 3: start()에서 log_db import 제거**

```python
# 현재 (line ~103)
from local_server.storage.log_db import get_log_db
self._limit_checker.restore_from_db(get_log_db())
```

```python
# 변경 후
self._limit_checker.restore_from_db(self._log)
```

`limit_checker.restore_from_db`는 `today_executed_amount()`만 호출하므로, LogPort를 넣으면 된다. limit_checker.py의 타입 힌트도 Task 8에서 변경.

- [ ] **Step 4: evaluate_all()에서 log_db import 3곳 제거**

1) `today_realized_pnl()` (line ~223):

```python
# 현재
from local_server.storage.log_db import get_log_db
today_pnl = get_log_db().today_realized_pnl()
```

```python
# 변경 후
today_pnl = self._log.today_realized_pnl()
```

2) 차단 로그 (line ~286):

```python
# 현재
from local_server.storage.log_db import get_log_db, LOG_TYPE_ERROR
await get_log_db().async_write(
    LOG_TYPE_ERROR,
    f"{reason.value}: {candidate.symbol} {candidate.side} 거부",
    symbol=candidate.symbol,
    meta={"rule_id": candidate.rule_id, "side": candidate.side,
          "block_reason": reason.value},
    intent_id=candidate.intent_id,
)
```

```python
# 변경 후
await self._log.write(
    LOG_TYPE_ERROR,
    f"{reason.value}: {candidate.symbol} {candidate.side} 거부",
    symbol=candidate.symbol,
    meta={"rule_id": candidate.rule_id, "side": candidate.side,
          "block_reason": reason.value},
    intent_id=candidate.intent_id,
)
```

3) 선택 로그 (line ~300):

```python
# 현재
from local_server.storage.log_db import get_log_db, LOG_TYPE_STRATEGY
await get_log_db().async_write(
    LOG_TYPE_STRATEGY,
    f"{candidate.reason}: {candidate.symbol} {candidate.side}",
    symbol=candidate.symbol,
    meta={"rule_id": candidate.rule_id, "side": candidate.side,
          "qty": candidate.desired_qty, "price": candidate.latest_price},
    intent_id=candidate.intent_id,
)
```

```python
# 변경 후
await self._log.write(
    LOG_TYPE_STRATEGY,
    f"{candidate.reason}: {candidate.symbol} {candidate.side}",
    symbol=candidate.symbol,
    meta={"rule_id": candidate.rule_id, "side": candidate.side,
          "qty": candidate.desired_qty, "price": candidate.latest_price},
    intent_id=candidate.intent_id,
)
```

- [ ] **Step 5: _resolve_markets()에서 stock_master_cache import 제거**

```python
# 현재 (line ~665)
from local_server.storage.stock_master_cache import get_stock_master_cache
master_map = {
    s["symbol"]: s.get("market", "")
    for s in get_stock_master_cache().get_all()
}
```

```python
# 변경 후 — stock_master_cache import만 교체, 후속 로직(unknown → broker 폴백)은 유지
all_markets = self._ref_data.get_market_map()

market_map: dict[str, str] = {}
unknown: list[str] = []
for sym in symbols:
    market = all_markets.get(sym, "")
    if market in ("KOSPI", "KOSDAQ"):
        market_map[sym] = market
    else:
        unknown.append(sym)
```

이후의 `for sym in unknown: ... self._lookup_market_via_broker(sym)` 루프는 그대로 유지한다 (broker 폴백은 host가 아닌 BrokerAdapter 경유).

- [ ] **Step 6: host import 잔존 확인**

Run: `python -c "content=open('local_server/engine/engine.py').read(); hits=[l for l in content.splitlines() if 'local_server.storage' in l or 'local_server.cloud' in l or 'local_server.config' in l]; print(f'{len(hits)} host imports'); [print(f'  {l.strip()}') for l in hits]"`
Expected: `0 host imports`

- [ ] **Step 7: 커밋**

```bash
git add local_server/engine/engine.py
git commit -m "refactor(engine): host import 제거, LogPort + ReferenceDataPort 주입"
```

---

### Task 8: limit_checker.py — TYPE_CHECKING import 변경

**Files:**
- Modify: `local_server/engine/limit_checker.py`

런타임 결합은 없지만, Task 7에서 `restore_from_db`에 `LogPort`를 넘기도록 바꿨으므로 타입 힌트를 맞춰야 한다.

- [ ] **Step 1: TYPE_CHECKING import 변경**

```python
# 현재
if TYPE_CHECKING:
    from local_server.storage.log_db import LogDB
```

```python
# 변경 후
if TYPE_CHECKING:
    from local_server.engine.ports import LogPort
```

- [ ] **Step 2: restore_from_db 타입 힌트 변경**

```python
# 현재
def restore_from_db(self, log_db: LogDB) -> None:
    """당일 체결 금액을 LogDB에서 복원한다 (엔진 재시작 시)."""
    self._today_executed = log_db.today_executed_amount()
```

```python
# 변경 후
def restore_from_db(self, log: LogPort) -> None:
    """당일 체결 금액을 LogPort에서 복원한다 (엔진 재시작 시)."""
    self._today_executed = log.today_executed_amount()
```

- [ ] **Step 3: host import 잔존 확인**

Run: `python -c "content=open('local_server/engine/limit_checker.py').read(); hits=[l for l in content.splitlines() if 'local_server.storage' in l]; print(f'{len(hits)} host imports')"`
Expected: `0 host imports`

- [ ] **Step 4: 커밋**

```bash
git add local_server/engine/limit_checker.py
git commit -m "refactor(limit_checker): TYPE_CHECKING을 LogPort로 변경"
```

---

### Task 9: routers/trading.py — 어댑터 조립 + 엔진 생성자 호출 변경

**Files:**
- Modify: `local_server/routers/trading.py`

현재 `start_strategy()` 엔드포인트에서 `StrategyEngine(broker)` 로 생성하고 있다. port 어댑터를 조립해서 주입하도록 변경.

- [ ] **Step 1: import 추가**

`trading.py` 상단에 추가:

```python
from local_server.adapters import (
    LogDbAdapter, CloudBarDataAdapter, MinuteBarStoreAdapter, StockMasterAdapter,
)
```

- [ ] **Step 2: start_strategy()의 엔진 생성 변경**

```python
# 현재
engine = StrategyEngine(broker)
```

```python
# 변경 후
from local_server.storage.log_db import get_log_db
from local_server.storage.stock_master_cache import get_stock_master_cache
from local_server.storage.minute_bar import get_minute_bar_store
from local_server.cloud.heartbeat import get_cloud_client

engine = StrategyEngine(
    broker=broker,
    log=LogDbAdapter(get_log_db()),
    bar_data=CloudBarDataAdapter(get_cloud_client()),
    bar_store=MinuteBarStoreAdapter(get_minute_bar_store()),
    ref_data=StockMasterAdapter(get_stock_master_cache()),
)
```

(host인 `trading.py`가 host 서비스를 import하는 것은 정상.)

- [ ] **Step 3: 커밋**

```bash
git add local_server/routers/trading.py
git commit -m "refactor(trading): 어댑터 조립하여 StrategyEngine에 port 주입"
```

---

### Task 10: main.py — AlertMonitor 생성에 port 주입

**Files:**
- Modify: `local_server/main.py`

main.py:188에서 HealthWatchdog용 AlertMonitor를 별도로 생성한다. engine.py 안의 AlertMonitor와는 다른 인스턴스이므로, 여기도 LogPort를 주입해야 한다. 안 하면 이 AlertMonitor의 경고가 DB에 기록되지 않는다.

- [ ] **Step 1: AlertMonitor 생성에 log + max_loss_pct 전달**

main.py lifespan 함수의 HealthWatchdog 시작 블록:

```python
# 현재 (line ~188)
from local_server.engine.alert_monitor import AlertMonitor
from local_server.engine.health_watchdog import HealthWatchdog
app.state.alert_monitor = AlertMonitor(config=cfg.get("alerts"))
```

```python
# 변경 후
from local_server.engine.alert_monitor import AlertMonitor
from local_server.engine.health_watchdog import HealthWatchdog
from local_server.adapters import LogDbAdapter
from local_server.storage.log_db import get_log_db
from decimal import Decimal

app.state.alert_monitor = AlertMonitor(
    config=cfg.get("alerts"),
    log=LogDbAdapter(get_log_db()),
    max_loss_pct=Decimal(str(cfg.get("max_loss_pct", "5.0"))),
)
```

- [ ] **Step 2: 커밋**

```bash
git add local_server/main.py
git commit -m "refactor(main): AlertMonitor 생성에 LogPort 주입"
```

---

### Task 11: 테스트 파일 — StrategyEngine 생성자 변경 반영

**Files:**
- Modify: `local_server/tests/test_engine.py`
- Modify: `local_server/tests/test_engine_v2.py`

StrategyEngine 생성자에 필수 파라미터가 추가되었으므로 테스트에서 mock port를 넣어줘야 한다.

- [ ] **Step 1: test_engine.py 수정**

test_engine.py:499의 `StrategyEngine(broker, config={"max_loss_pct": "1.0"})` 를 변경:

```python
# 변경 후 — mock port 주입
from unittest.mock import AsyncMock, MagicMock

mock_log = MagicMock()
mock_log.write = AsyncMock()
mock_log.today_realized_pnl = MagicMock(return_value=0.0)
mock_log.today_executed_amount = MagicMock(return_value=Decimal(0))

engine = StrategyEngine(
    broker,
    log=mock_log,
    bar_data=MagicMock(),
    bar_store=MagicMock(),
    ref_data=MagicMock(),
    config={"max_loss_pct": "1.0"},
)
```

- [ ] **Step 2: test_engine_v2.py 수정**

test_engine_v2.py:446의 `_make_engine()` 헬퍼 변경:

```python
# 변경 후
def _make_engine() -> StrategyEngine:
    """mock broker + mock ports로 StrategyEngine 인스턴스 생성."""
    from unittest.mock import AsyncMock, MagicMock
    from decimal import Decimal

    broker = MagicMock()
    mock_log = MagicMock()
    mock_log.write = AsyncMock()
    mock_log.today_realized_pnl = MagicMock(return_value=0.0)
    mock_log.today_executed_amount = MagicMock(return_value=Decimal(0))

    return StrategyEngine(
        broker=broker,
        log=mock_log,
        bar_data=MagicMock(),
        bar_store=MagicMock(),
        ref_data=MagicMock(),
    )
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m pytest local_server/tests/test_engine.py local_server/tests/test_engine_v2.py -v --tb=short`
Expected: 기존 테스트 PASS (mock port로 host 의존 없이 실행)

- [ ] **Step 4: 커밋**

```bash
git add local_server/tests/test_engine.py local_server/tests/test_engine_v2.py
git commit -m "test: StrategyEngine 생성자 변경에 mock port 주입"
```

---

### Task 12: 전체 검증 — host import 0개 확인 + 서버 기동 테스트

**Files:**
- 변경 없음 (검증만)

- [ ] **Step 1: engine/ 전체에서 host import 잔존 확인**

Run:

```bash
python -c "
import os
host_patterns = ['local_server.storage', 'local_server.cloud', 'local_server.config',
                 'local_server.broker', 'local_server.routers', 'local_server.tray',
                 'local_server.updater', 'local_server.core', 'local_server.utils']
hits = []
for root, dirs, files in os.walk('local_server/engine'):
    for f in files:
        if not f.endswith('.py') or '__pycache__' in root:
            continue
        path = os.path.join(root, f)
        for i, line in enumerate(open(path), 1):
            if any(p in line for p in host_patterns):
                hits.append(f'{path}:{i}: {line.strip()}')
print(f'{len(hits)} host imports found')
for h in hits:
    print(f'  {h}')
"
```

Expected: `0 host imports found`

- [ ] **Step 2: Python import 체크**

Run:

```bash
python -c "
from local_server.engine.ports import LogPort, BarDataPort, BarStorePort, ReferenceDataPort
from local_server.engine.engine import StrategyEngine
from local_server.engine.executor import OrderExecutor
from local_server.engine.indicator_provider import IndicatorProvider
from local_server.engine.bar_builder import BarBuilder
from local_server.engine.alert_monitor import AlertMonitor
from local_server.engine.limit_checker import LimitChecker
from local_server.adapters import LogDbAdapter, CloudBarDataAdapter, MinuteBarStoreAdapter, StockMasterAdapter
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 3: 서버 기동 테스트**

Run:

```bash
python -c "
import uvicorn, asyncio, sys
from local_server.main import app
print('App created OK — import chain verified')
# 실제 서버 기동은 수동으로 확인: python -m uvicorn local_server.main:app --port 4020
"
```

Expected: `App created OK — import chain verified`. import 에러 없음.

- [ ] **Step 4: spec 수용 기준 체크리스트 업데이트**

`spec/runtime-host-separation/spec.md`의 §6 수용 기준 체크박스를 `[x]`로 변경.

- [ ] **Step 5: 최종 커밋**

```bash
git add spec/runtime-host-separation/spec.md
git commit -m "docs: runtime/host 분리 Phase 1 완료, spec 수용기준 체크"
```
