# Runtime / Host 분리 명세서

> 작성일: 2026-03-30 | 상태: 초안
> 관련 문서:
> - `docs/product/assistant-copilot-engine-structure.md`
> - `docs/product/system-trader-definition.md`
> - `docs/product/remote-permission-model.md`
> - `docs/architecture.md`
> - `spec/system-trader/spec.md`

---

## 1. 목표

`local_server` 내부에서 **매매 엔진(runtime)**과 **인프라(host)**의 역할을 분리한다.

현재 `engine/` 모듈들이 `storage.log_db`, `cloud.heartbeat`, `storage.stock_master_cache`, `storage.minute_bar`, `config` 등 host 서비스를 직접 import하고 있다. 이 직접 의존을 Port 인터페이스로 교체하여 engine이 host 구현을 모르게 만든다.

### 1.1 이 분리가 달성하는 것

1. **테스트 격리** — mock port만으로 engine 단위 테스트 가능 (broker/DB/cloud 불필요)
2. **향후 물리 분리 준비** — Phase 2에서 `sv_runtime/` 톱레벨 패키지로 이동할 때 전제 조건 충족
3. **개념 명확화** — "System Trader + Execution Layer"와 "Host 인프라"의 경계가 코드에 반영

### 1.2 이 분리가 하지 않는 것

- 새 서버/프로세스를 만들지 않는다
- 폴더를 이동하지 않는다 (`engine/`은 `local_server/` 안에 그대로)
- 기능을 추가하거나 변경하지 않는다

---

## 2. 배경

### 2.1 Runtime과 Host의 정의

| 구분 | 정체성 | 비유 |
|------|--------|------|
| **Runtime** | 시세 수신 → 전략 평가 → 후보 수집 → 포트폴리오 판단 → 주문 실행의 판단+실행 파이프라인 | 앱 (게임 엔진) |
| **Host** | 프로세스 부팅, 브로커 연결, 클라우드 통신, 저장소, API 노출, 업데이트, 트레이 | 컴퓨터 본체 |

Runtime은 **host가 import해서 쓰는 라이브러리**다. `main()`도 없고 서버도 안 띄운다. Host가 port 구현을 주입하고 `engine.start()`를 호출한다.

### 2.2 현재 구조

```
local_server/
├── main.py, config.py           # host: 부팅, 설정
├── broker/                       # host: 브로커 수명관리
├── cloud/                        # host: 하트비트, WS 릴레이, 커맨드
├── storage/                      # host: LogDB, 캐시, credential
├── routers/                      # host: HTTP API
├── tray/, updater/, core/, utils/# host: 운영
└── engine/                       # ← runtime (host를 직접 import하는 곳 있음)
```

### 2.3 이미 순수한 Engine 모듈 (변경 불필요)

아래 모듈들은 host에 의존하지 않는다:

- `system_trader.py` — 포트폴리오 판단 (순수 로직)
- `safeguard.py` — 킬스위치/손실락 (순수 상태기계)
- `evaluator.py` — DSL 평가 (sv_core.parsing만 사용)
- `signal_manager.py` — 신호 상태 추적 (인메모리)
- `position_state.py` — 종목별 포지션 (데이터 클래스)
- `context_cache.py` — AI 컨텍스트 캐시 (인메모리)
- `condition_tracker.py` — 조건 추적 (인메모리)
- `result_store.py` — 실행 결과 캐시 (인메모리)
- `scheduler.py` — 1분 루프 (APScheduler)
- `trader_models.py` — CandidateSignal 등 데이터 모델
- `price_verifier.py` — BrokerAdapter만 사용 (sv_core에 있으므로 허용)

#### host lifecycle 보조물 (engine/ 안에 있지만 host 관제 성격)

- `health_watchdog.py` — main.py에서 생성·소유하며, 엔진 외부에서 독립적으로 동작하는 관제 도구. host에 직접 의존하지는 않지만(BrokerAdapter + AlertMonitor만 사용), runtime 코어가 아니라 host lifecycle 보조물로 분류한다. Phase 2에서 `sv_runtime/`으로 이동할 때 host 쪽에 남길지 판단.

---

## 3. 현재 host 직접 의존 전수 목록

engine/ 내부에서 host를 직접 import하는 곳 **11곳, 5개 host 모듈**:

| # | Engine 파일 | Host 모듈 | 호출 | import 방식 |
|---|-------------|-----------|------|-------------|
| 1 | `engine.py:103` | `storage.log_db` | `get_log_db()` → `restore_from_db` | 런타임 |
| 2 | `engine.py:223` | `storage.log_db` | `today_realized_pnl()` | 런타임 |
| 3 | `engine.py:286` | `storage.log_db` | `async_write(LOG_TYPE_ERROR)` | 런타임 |
| 4 | `engine.py:300` | `storage.log_db` | `async_write(LOG_TYPE_STRATEGY)` | 런타임 |
| 5 | `engine.py:665` | `storage.stock_master_cache` | `get_stock_master_cache().get_all()` | 런타임 |
| 6 | `executor.py:86` | `storage.log_db` | `async_write` (ORDER, FILL, ERROR) | 런타임 |
| 7 | `indicator_provider.py:76` | `cloud.heartbeat` | `get_cloud_client()._get()` | 런타임 |
| 8 | `bar_builder.py:25` | `storage.minute_bar` | `get_minute_bar_store()` | 런타임 |
| 9 | `alert_monitor.py:139` | `storage.log_db` | `async_write(LOG_TYPE_ALERT)` | 런타임 |
| 10 | `alert_monitor.py:230` | `config` | `get_config()` | 런타임 |
| 11 | `limit_checker.py:11` | `storage.log_db` | `LogDB` 타입 어노테이션 | TYPE_CHECKING only |

**특이점**: 모든 import가 함수 내부 런타임 lazy import. 모듈 레벨 import는 0개. #11은 TYPE_CHECKING 가드 안이라 런타임 결합 없음.

---

## 4. 설계

### 4.1 2단계 점진적 분리

```
Phase 1 (이번 작업): 의존성 역전
  → engine/ 안에 ports.py 추가
  → engine 내부의 host 직접 import를 port 호출로 교체
  → host(routers/trading.py)가 port 어댑터를 조립해서 주입

Phase 2 (별도 작업): 물리 분리
  → engine/ → sv_runtime/ 톱레벨 이동
  → import 경로 일괄 변경
  → 패키지 경계로 역의존 강제
```

Phase를 나누는 이유:
- Port 설계가 빠뜨린 숨은 의존성을 안전하게 발견할 수 있다. 같은 패키지 안이라 일단 동작하면서 점진적으로 정리 가능.
- 한 번에 하면 port 설계 오류와 import 경로 변경 오류가 동시에 터져서 "port가 잘못인지, 이동이 잘못인지, 숨은 의존이 있는 건지" 구분이 어렵다.
- Phase 1 완료 후 engine 내부에서 `from local_server.*` (engine 제외)가 0개인 것을 확인한 뒤에 이동하면 import 에러가 안 난다.
- 롤백 단위가 작다.

### 4.2 Port 인터페이스

**4개 Port + BrokerAdapter 재사용 + 생성자 파라미터 1개.**

#### BrokerAdapter (기존, sv_core/broker/base.py)

이미 `place_order`, `get_balance`, `get_open_orders`, `cancel_order`, `get_quote`, `subscribe_quotes`를 갖고 있다. 새 port를 만들면 인터페이스 중복. **그대로 사용.**

#### LogPort (신규)

```python
class LogPort(Protocol):
    async def write(self, log_type: str, message: str, **kwargs) -> None: ...
    def today_realized_pnl(self) -> float: ...
    def today_executed_amount(self) -> Decimal: ...
```

- 소비자: `engine.py` (4곳), `executor.py` (6곳), `alert_monitor.py` (1곳)
- host 어댑터: `LogDB`를 감싸는 얇은 래퍼

#### BarDataPort (신규)

```python
class BarDataPort(Protocol):
    async def fetch_minute_bars(self, symbol: str, tf: str, limit: int) -> list[dict]: ...
```

- 소비자: `indicator_provider.py` (1곳)
- host 어댑터: `CloudClient._get()` 를 감싸는 래퍼

#### BarStorePort (신규)

```python
class BarStorePort(Protocol):
    def save_bars(self, symbol: str, bars: list[dict]) -> None: ...
```

- 소비자: `bar_builder.py` (1곳)
- host 어댑터: `MinuteBarStore`를 감싸는 래퍼

#### ReferenceDataPort (신규)

```python
class ReferenceDataPort(Protocol):
    def get_market_map(self) -> dict[str, str]: ...
```

- 소비자: `engine.py` `_resolve_markets` (1곳)
- host 어댑터: `StockMasterCache`를 감싸는 래퍼

#### alert_monitor의 config 의존 (생성자 파라미터)

`get_config().get("max_loss_pct")` 1곳만 있고, 임계값 하나를 읽는 용도. Port를 만들 필요 없이 생성자에서 `max_loss_pct: Decimal`을 직접 받는다.

### 4.3 커버리지 매핑

| Host 의존 (§3) | 해결 방식 |
|-----------------|-----------|
| `log_db` 7곳 (#1~#4, #6, #9) | LogPort |
| `cloud.heartbeat` 1곳 (#7) | BarDataPort |
| `stock_master_cache` 1곳 (#5) | ReferenceDataPort |
| `minute_bar` 1곳 (#8) | BarStorePort |
| `config` 1곳 (#10) | 생성자 파라미터 |
| `log_db` TYPE_CHECKING (#11) | 무시 (런타임 결합 없음) |

**11곳 전부 커버. engine 내부에서 host import 0개 달성.**

### 4.4 StrategyEngine 생성자 변경

현재:

```python
class StrategyEngine:
    def __init__(
        self,
        broker: BrokerAdapter,
        config: dict | None = None,
    ):
```

변경 후:

```python
class StrategyEngine:
    def __init__(
        self,
        broker: BrokerAdapter,
        log: LogPort,
        bar_data: BarDataPort,
        bar_store: BarStorePort,
        ref_data: ReferenceDataPort,
        config: dict | None = None,
    ):
```

engine이 내부 모듈에 port를 전달:

```python
self._executor = OrderExecutor(broker=broker, log=log, ...)
self._indicator_provider = IndicatorProvider(bar_data=bar_data)
self._bar_builder = BarBuilder(bar_store=bar_store)
self._alert_monitor = AlertMonitor(
    log=log,
    max_loss_pct=Decimal(str(cfg.get("max_loss_pct", "5.0"))),
    config=cfg.get("alerts"),
)
```

### 4.5 의존 방향

```
sv_core/           ← 아무것도 모름 (공유 프리미티브)
  ↑
engine/ (runtime)  ← sv_core + ports만 앎, host 모름
  ↑
host (나머지)      ← runtime도 알고, sv_core도 알고, 자기 자신도 앎
```

host는 **조립자**다. 모든 것을 알고 연결해준다. 이게 정상이다.
금지되는 건 **역방향(runtime → host)**만이다.

### 4.6 Host 어댑터와 조립부

#### 어댑터란

Port가 "무엇을 해줘"라는 계약서라면, Adapter는 "내가 해줄게"라는 구현체다. host가 가진 구체 서비스(LogDB, CloudClient 등)를 port 인터페이스에 맞게 감싸는 얇은 래퍼.

예시:

```python
class LogDbAdapter:
    """LogPort 구현 — LogDB를 감싸는 래퍼."""
    def __init__(self, db):
        self._db = db

    async def write(self, log_type, message, **kw):
        await self._db.async_write(log_type, message, **kw)

    def today_realized_pnl(self):
        return self._db.today_realized_pnl()

    def today_executed_amount(self):
        return self._db.today_executed_amount()
```

#### 어댑터 위치

어댑터는 host 코드이므로 engine/ 밖에 위치한다. `local_server/adapters.py`에 모든 어댑터를 모은다. router가 두꺼워지는 것을 방지.

#### 조립부 (routers/trading.py)

```python
from local_server.adapters import (
    LogDbAdapter, CloudBarDataAdapter, MinuteBarStoreAdapter, StockMasterAdapter,
)
from local_server.storage.log_db import get_log_db
from local_server.storage.stock_master_cache import get_stock_master_cache
from local_server.storage.minute_bar import get_minute_bar_store
from local_server.cloud.heartbeat import get_cloud_client

# port 어댑터 생성
log_adapter = LogDbAdapter(get_log_db())
bar_data_adapter = CloudBarDataAdapter(get_cloud_client())
bar_store_adapter = MinuteBarStoreAdapter(get_minute_bar_store())
ref_data_adapter = StockMasterAdapter(get_stock_master_cache())

engine = StrategyEngine(
    broker=broker,
    log=log_adapter,
    bar_data=bar_data_adapter,
    bar_store=bar_store_adapter,
    ref_data=ref_data_adapter,
)
```

### 4.7 역방향 의존 (host → runtime)

| Host 모듈 | Runtime 접근 | 현재 | 변경 |
|-----------|-------------|------|------|
| `routers/trading.py` | StrategyEngine | `app.state.engine` | 유지 (정상적인 방향) |
| `cloud/_command_handler.py` | `engine.safeguard` | 직접 접근 | 유지 (host → runtime 방향은 허용) |
| `main.py` | StrategyEngine | `app.state.engine` | 유지 |

host → runtime 방향의 import는 정상이다. 문제는 runtime → host 방향만이다.

---

## 5. 파일별 영향 범위

### 5.1 신규 파일

| 파일 | 내용 |
|------|------|
| `engine/ports.py` | Protocol 정의 4개 (LogPort, BarDataPort, BarStorePort, ReferenceDataPort) + LOG_TYPE 상수 |

### 5.2 Runtime 수정 (host import 제거)

| 파일 | 변경 | 호출 수 |
|------|------|---------|
| `engine.py` | `get_log_db()` 3곳 → `self._log`, `get_stock_master_cache()` 1곳 → `self._ref` | 4 |
| `executor.py` | `get_log_db()` → `self._log` | 6 |
| `indicator_provider.py` | `get_cloud_client()._get()` → `self._bar_data` | 1 |
| `bar_builder.py` | `get_minute_bar_store()` → `self._bar_store` | 1 |
| `alert_monitor.py` | `get_log_db()` → `self._log`, `get_config()` → 생성자 파라미터 | 2 |

### 5.3 Host 수정 (어댑터 조립)

| 파일 | 변경 |
|------|------|
| `adapters.py` (신규) | LogDbAdapter, CloudBarDataAdapter, MinuteBarStoreAdapter, StockMasterAdapter |
| `routers/trading.py` | 어댑터 조립 + StrategyEngine 생성자 호출 변경 |
| `main.py` | AlertMonitor 생성에 LogPort 주입 |

### 5.4 변경 없는 파일

`system_trader.py`, `safeguard.py`, `evaluator.py`, `signal_manager.py`, `position_state.py`, `context_cache.py`, `condition_tracker.py`, `result_store.py`, `scheduler.py`, `trader_models.py`, `price_verifier.py`, `health_watchdog.py`

---

## 6. 수용 기준

### Phase 1 완료 조건

- [ ] `engine/ports.py`에 4개 Protocol 정의
- [ ] `engine/` 내부에서 `from local_server.storage.*`, `from local_server.cloud.*`, `from local_server.config` import가 0개 (TYPE_CHECKING 제외)
- [ ] `sv_core.*` import, `local_server.engine.*` import는 허용
- [ ] `engine/ports.py`에 LOG_TYPE 상수 정의 (runtime 내부 단일 원천, Phase 2에서 위치 재검토)
- [ ] `local_server/adapters.py`에 어댑터 4개 구현
- [ ] `routers/trading.py`에서 어댑터 조립 후 엔진에 주입
- [ ] `main.py`에서 AlertMonitor 생성에 LogPort 주입
- [ ] 테스트 파일(test_engine.py, test_engine_v2.py) 생성자 변경 반영
- [ ] 기존 기능 동작 확인: 엔진 start/stop, 전략 평가 → 주문 실행, Kill Switch 원격 제어

### Phase 2 완료 조건 (별도 작업)

- [ ] `engine/` → `sv_runtime/` 톱레벨 이동
- [ ] `sv_runtime/`에서 `from local_server.*` import가 0개
- [ ] 모든 `from local_server.engine.*` → `from sv_runtime.*` 일괄 변경
- [ ] 패키지 경계로 역의존 강제 확인

---

## 7. 리스크와 주의점

1. **StrategyEngine 생성자 시그니처 변경**: `trading.py`의 엔진 생성부와 테스트 코드 모두 수정 필요. 빠뜨리면 런타임 에러.

2. **executor.py의 log_db 호출 6곳**: 가장 빈번한 결합점. 한 번에 모두 전환해야 일관성 유지. 일부만 바꾸면 혼재 상태가 됨.

3. **LOG_TYPE 상수 위치**: `LOG_TYPE_ORDER`, `LOG_TYPE_FILL`, `LOG_TYPE_ERROR`, `LOG_TYPE_STRATEGY`, `LOG_TYPE_ALERT` 등이 현재 `storage.log_db`에 정의되어 있다. Phase 1에서는 `engine/ports.py`에 재정의한다. host의 `log_db.py`에 있는 기존 상수는 하위호환을 위해 유지하되, engine은 `ports.py`에서만 import한다. 값이 동일한 문자열 상수이므로 drift 위험은 낮다. Phase 2에서 `sv_runtime/`으로 이동 시 단일 원천(sv_core 또는 별도 공유 모듈)으로 통합할지 재검토한다.

4. **indicator_provider의 yfinance**: 일봉 조회에 `yfinance`를 직접 호출하고 `asyncio.to_thread`로 감싸고 있다. 이번 Phase 1에서는 분봉(BarDataPort)만 끊고, 일봉 yfinance 호출은 유지한다. Phase 2에서 `sv_runtime/`으로 이동 시 yfinance는 runtime의 외부 의존으로 허용하거나 별도 port로 추출한다.

5. **limit_checker의 TYPE_CHECKING import**: `from local_server.storage.log_db import LogDB`가 TYPE_CHECKING 블록 안에 있다. 런타임 결합은 없지만, Phase 2 이동 시 이 타입 힌트를 `LogPort`로 교체해야 한다.

6. **점진적 검증 필수**: port를 하나씩 끊을 때마다 엔진 start → 평가 루프 → 주문 파이프라인이 정상 동작하는지 확인 후 다음으로 진행.

---

## 8. 용어 정리

| 용어 | 의미 |
|------|------|
| **Runtime** | 매매 엔진. 전략 평가 → 포트폴리오 판단 → 주문 실행 파이프라인. host가 import해서 쓰는 라이브러리 |
| **Host** | 프로세스 부팅, 브로커 연결, 저장소, 클라우드, API 노출 등 runtime의 실행 환경 |
| **Port** | runtime이 host에게 요구하는 인터페이스 계약 (Python Protocol) |
| **Adapter** | port를 구현하는 host 쪽 래퍼 (LogDbAdapter 등) |
| **Phase 1** | 의존성 역전 — port 인터페이스로 host 직접 import 제거 |
| **Phase 2** | 물리 분리 — engine/ → sv_runtime/ 톱레벨 이동 |
